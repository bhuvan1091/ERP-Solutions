"""Sales orders with FEFO stock allocation and dispatch."""
from datetime import datetime, timezone, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional

from database import get_db
from models import (
    SalesOrder, SalesOrderLine, Customer, Warehouse, Product, User,
    InventoryBatch, StockMovement, SalesOrderStatus, StockMovementType, BatchStatus,
)
from schemas import SOCreate, SOOut, SOLineOut
from auth import require_permission
from helpers import log_audit


router = APIRouter(prefix="/api/sales-orders", tags=["sales"])


def _so_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(SalesOrder).count()
    return f"SO-{year}-{(count + 1):05d}"


def _so_out(so: SalesOrder) -> SOOut:
    lines = []
    for l in so.lines:
        bn = None
        if l.allocated_batch_id:
            b = next((bb for bb in [l.__dict__.get("_allocated_batch")] if bb), None)
            if not b:
                b = None
        lines.append(SOLineOut(
            id=l.id, product_id=l.product_id,
            product_sku=l.product.sku if l.product else None,
            product_name=l.product.name if l.product else None,
            quantity=l.quantity, dispatched_quantity=l.dispatched_quantity,
            unit_price=l.unit_price, tax_rate=l.tax_rate,
            discount=l.discount, line_total=l.line_total,
            allocated_batch_id=l.allocated_batch_id,
            allocated_batch_number=None,
        ))
    return SOOut(
        id=so.id, so_number=so.so_number,
        customer_id=so.customer_id,
        customer_name=so.customer.name if so.customer else None,
        warehouse_id=so.warehouse_id,
        warehouse_name=so.warehouse.name if so.warehouse else None,
        order_date=so.order_date, expected_dispatch_date=so.expected_dispatch_date,
        status=so.status.value if hasattr(so.status, "value") else so.status,
        subtotal=so.subtotal, tax_amount=so.tax_amount,
        discount_amount=so.discount_amount, total=so.total,
        source_channel=so.source_channel, campaign_id=so.campaign_id,
        utm_source=so.utm_source, utm_medium=so.utm_medium, utm_campaign=so.utm_campaign,
        notes=so.notes, created_at=so.created_at, lines=lines,
    )


@router.get("", response_model=List[SOOut])
def list_sos(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sales:read")),
):
    q = db.query(SalesOrder).options(selectinload(SalesOrder.lines).selectinload(SalesOrderLine.product))
    if status:
        q = q.filter(SalesOrder.status == status)
    if customer_id:
        q = q.filter(SalesOrder.customer_id == customer_id)
    sos = q.order_by(SalesOrder.created_at.desc()).all()
    return [_so_out(s) for s in sos]


@router.get("/{so_id}", response_model=SOOut)
def get_so(so_id: str, db: Session = Depends(get_db),
           _: User = Depends(require_permission("sales:read"))):
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    if not so:
        raise HTTPException(404, "Sales order not found")
    return _so_out(so)


@router.post("", response_model=SOOut)
def create_so(payload: SOCreate, db: Session = Depends(get_db),
              current: User = Depends(require_permission("sales:write"))):
    if not payload.lines:
        raise HTTPException(400, "At least one line required")
    customer = db.query(Customer).filter(Customer.id == payload.customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(400, "Invalid customer")
    if not db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first():
        raise HTTPException(400, "Invalid warehouse")

    so = SalesOrder(
        so_number=_so_number(db),
        customer_id=payload.customer_id,
        warehouse_id=payload.warehouse_id,
        expected_dispatch_date=payload.expected_dispatch_date,
        status=SalesOrderStatus.CONFIRMED,
        source_channel=payload.source_channel,
        campaign_id=payload.campaign_id,
        utm_source=payload.utm_source, utm_medium=payload.utm_medium, utm_campaign=payload.utm_campaign,
        notes=payload.notes, created_by=current.id,
    )
    db.add(so)
    db.flush()

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    discount_total = Decimal("0")
    for ln in payload.lines:
        product = db.query(Product).filter(Product.id == ln.product_id).first()
        if not product:
            raise HTTPException(400, f"Invalid product {ln.product_id}")
        unit_price = Decimal(ln.unit_price) if ln.unit_price is not None else Decimal(product.selling_price)
        tax_rate = Decimal(ln.tax_rate) if ln.tax_rate is not None else Decimal(product.tax_rate)
        line_sub = Decimal(ln.quantity) * unit_price - Decimal(ln.discount)
        line_tax = line_sub * tax_rate / Decimal(100)
        line = SalesOrderLine(
            order_id=so.id, product_id=product.id,
            quantity=ln.quantity, unit_price=unit_price,
            tax_rate=tax_rate, discount=ln.discount,
            line_total=line_sub + line_tax,
        )
        db.add(line)
        subtotal += line_sub
        tax_total += line_tax
        discount_total += Decimal(ln.discount)

    so.subtotal = subtotal
    so.tax_amount = tax_total
    so.discount_amount = discount_total
    so.total = subtotal + tax_total
    log_audit(db, current, "CREATE", "SalesOrder", so.id, {"so_number": so.so_number})
    db.commit()
    db.refresh(so)
    return _so_out(so)


@router.post("/{so_id}/allocate", response_model=SOOut)
def allocate_so(so_id: str, db: Session = Depends(get_db),
                current: User = Depends(require_permission("sales:approve"))):
    """FEFO allocation: pick batches with earliest expiry for each line."""
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    if not so:
        raise HTTPException(404, "SO not found")
    if so.status != SalesOrderStatus.CONFIRMED:
        raise HTTPException(400, f"Cannot allocate SO in status {so.status}")

    today = date.today()
    for line in so.lines:
        if line.allocated_batch_id:
            continue
        # find RELEASED, non-expired batches sorted by expiry ascending (FEFO)
        candidates = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == line.product_id,
            InventoryBatch.warehouse_id == so.warehouse_id,
            InventoryBatch.status == BatchStatus.RELEASED,
            (InventoryBatch.expiry_date.is_(None)) | (InventoryBatch.expiry_date >= today),
        ).order_by(InventoryBatch.expiry_date.asc().nullslast()).all()

        remaining = Decimal(line.quantity)
        chosen = None
        for c in candidates:
            avail = Decimal(c.quantity_on_hand) - Decimal(c.quantity_reserved)
            if avail >= remaining:
                chosen = c
                break
        if not chosen:
            raise HTTPException(400,
                f"Insufficient released stock for {line.product.sku if line.product else line.product_id}")
        chosen.quantity_reserved = Decimal(chosen.quantity_reserved) + remaining
        line.allocated_batch_id = chosen.id

    so.status = SalesOrderStatus.ALLOCATED
    log_audit(db, current, "UPDATE", "SalesOrder", so.id, {"action": "allocate"})
    db.commit()
    db.refresh(so)
    return _so_out(so)


@router.post("/{so_id}/dispatch", response_model=SOOut)
def dispatch_so(so_id: str, db: Session = Depends(get_db),
                current: User = Depends(require_permission("sales:dispatch"))):
    """Consume reserved stock and mark dispatched."""
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    if not so:
        raise HTTPException(404, "SO not found")
    if so.status != SalesOrderStatus.ALLOCATED:
        raise HTTPException(400, f"Cannot dispatch SO in status {so.status}")

    for line in so.lines:
        if not line.allocated_batch_id:
            raise HTTPException(400, "All lines must be allocated before dispatch")
        batch = db.query(InventoryBatch).filter(InventoryBatch.id == line.allocated_batch_id).first()
        qty = Decimal(line.quantity)
        batch.quantity_on_hand = Decimal(batch.quantity_on_hand) - qty
        batch.quantity_reserved = Decimal(batch.quantity_reserved) - qty
        line.dispatched_quantity = qty
        mv = StockMovement(
            batch_id=batch.id, movement_type=StockMovementType.ISSUE,
            quantity=-qty, reference_type="SO", reference_id=so.id,
            reference_number=so.so_number, user_id=current.id,
            notes=f"Dispatch for {so.so_number}",
        )
        db.add(mv)

    so.status = SalesOrderStatus.DISPATCHED
    log_audit(db, current, "APPROVE", "SalesOrder", so.id, {"action": "dispatch"})
    db.commit()
    db.refresh(so)
    return _so_out(so)


@router.post("/{so_id}/cancel", response_model=SOOut)
def cancel_so(so_id: str, db: Session = Depends(get_db),
              current: User = Depends(require_permission("sales:approve"))):
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    if not so:
        raise HTTPException(404, "SO not found")
    if so.status in (SalesOrderStatus.DISPATCHED, SalesOrderStatus.INVOICED, SalesOrderStatus.CANCELLED):
        raise HTTPException(400, "Cannot cancel")

    # Release reservations
    for line in so.lines:
        if line.allocated_batch_id:
            batch = db.query(InventoryBatch).filter(InventoryBatch.id == line.allocated_batch_id).first()
            if batch:
                batch.quantity_reserved = Decimal(batch.quantity_reserved) - Decimal(line.quantity)
            line.allocated_batch_id = None

    so.status = SalesOrderStatus.CANCELLED
    log_audit(db, current, "UPDATE", "SalesOrder", so.id, {"status": "CANCELLED"})
    db.commit()
    db.refresh(so)
    return _so_out(so)
