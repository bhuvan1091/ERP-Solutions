"""Purchase Orders + Goods Receipts (GRN) with batch creation."""
from datetime import datetime, timezone, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional

from database import get_db
from models import (
    PurchaseOrder, PurchaseOrderLine, GoodsReceipt, GoodsReceiptLine,
    InventoryBatch, StockMovement, Supplier, Warehouse, Product, User,
    PurchaseOrderStatus, StockMovementType, BatchStatus,
)
from schemas import POCreate, POOut, POLineOut, GRNCreate
from auth import require_permission
from helpers import log_audit


router = APIRouter(prefix="/api/purchase-orders", tags=["purchase"])
grn_router = APIRouter(prefix="/api/goods-receipts", tags=["purchase"])


def _po_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(PurchaseOrder).count()
    return f"PO-{year}-{(count + 1):05d}"


def _grn_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(GoodsReceipt).count()
    return f"GRN-{year}-{(count + 1):05d}"


def _po_out(po: PurchaseOrder) -> POOut:
    lines = [
        POLineOut(
            id=l.id, product_id=l.product_id,
            product_sku=l.product.sku if l.product else None,
            product_name=l.product.name if l.product else None,
            quantity=l.quantity, received_quantity=l.received_quantity,
            unit_price=l.unit_price, tax_rate=l.tax_rate, line_total=l.line_total,
        )
        for l in po.lines
    ]
    return POOut(
        id=po.id, po_number=po.po_number,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.name if po.supplier else None,
        warehouse_id=po.warehouse_id,
        warehouse_name=po.warehouse.name if po.warehouse else None,
        order_date=po.order_date, expected_delivery_date=po.expected_delivery_date,
        status=po.status.value if hasattr(po.status, "value") else po.status,
        subtotal=po.subtotal, tax_amount=po.tax_amount, total=po.total,
        notes=po.notes, created_at=po.created_at, lines=lines,
    )


@router.get("", response_model=List[POOut])
def list_pos(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("purchase:read")),
):
    q = db.query(PurchaseOrder).options(selectinload(PurchaseOrder.lines).selectinload(PurchaseOrderLine.product))
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    pos = q.order_by(PurchaseOrder.created_at.desc()).all()
    return [_po_out(p) for p in pos]


@router.get("/{po_id}", response_model=POOut)
def get_po(po_id: str, db: Session = Depends(get_db),
           _: User = Depends(require_permission("purchase:read"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "Purchase order not found")
    return _po_out(po)


@router.post("", response_model=POOut)
def create_po(payload: POCreate, db: Session = Depends(get_db),
              current: User = Depends(require_permission("purchase:write"))):
    if not payload.lines:
        raise HTTPException(400, "At least one line required")
    if not db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.is_active == True).first():
        raise HTTPException(400, "Invalid supplier")
    if not db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first():
        raise HTTPException(400, "Invalid warehouse")

    po = PurchaseOrder(
        po_number=_po_number(db),
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        expected_delivery_date=payload.expected_delivery_date,
        notes=payload.notes,
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        created_by=current.id,
    )
    db.add(po)
    db.flush()

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for ln in payload.lines:
        if not db.query(Product).filter(Product.id == ln.product_id).first():
            raise HTTPException(400, f"Invalid product {ln.product_id}")
        line_sub = Decimal(ln.quantity) * Decimal(ln.unit_price)
        line_tax = line_sub * Decimal(ln.tax_rate) / Decimal(100)
        line = PurchaseOrderLine(
            order_id=po.id, product_id=ln.product_id, quantity=ln.quantity,
            unit_price=ln.unit_price, tax_rate=ln.tax_rate,
            line_total=line_sub + line_tax,
        )
        db.add(line)
        subtotal += line_sub
        tax_total += line_tax

    po.subtotal = subtotal
    po.tax_amount = tax_total
    po.total = subtotal + tax_total
    log_audit(db, current, "CREATE", "PurchaseOrder", po.id, {"po_number": po.po_number})
    db.commit()
    db.refresh(po)
    return _po_out(po)


@router.post("/{po_id}/approve", response_model=POOut)
def approve_po(po_id: str, db: Session = Depends(get_db),
               current: User = Depends(require_permission("purchase:approve"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise HTTPException(400, f"Cannot approve PO in status {po.status}")
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by = current.id
    po.approved_at = datetime.now(timezone.utc)
    log_audit(db, current, "APPROVE", "PurchaseOrder", po.id)
    db.commit()
    db.refresh(po)
    return _po_out(po)


@router.post("/{po_id}/cancel", response_model=POOut)
def cancel_po(po_id: str, db: Session = Depends(get_db),
              current: User = Depends(require_permission("purchase:approve"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED):
        raise HTTPException(400, "Cannot cancel this PO")
    po.status = PurchaseOrderStatus.CANCELLED
    log_audit(db, current, "UPDATE", "PurchaseOrder", po.id, {"status": "CANCELLED"})
    db.commit()
    db.refresh(po)
    return _po_out(po)


# ====== GRN ======
@grn_router.post("")
def create_grn(payload: GRNCreate, db: Session = Depends(get_db),
               current: User = Depends(require_permission("purchase:receive"))):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == payload.purchase_order_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    if po.status not in (PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIALLY_RECEIVED):
        raise HTTPException(400, f"PO not in receivable state ({po.status})")
    if not payload.lines:
        raise HTTPException(400, "GRN must have at least one line")

    grn = GoodsReceipt(
        grn_number=_grn_number(db),
        purchase_order_id=po.id,
        received_date=payload.received_date or date.today(),
        notes=payload.notes,
        created_by=current.id,
    )
    db.add(grn)
    db.flush()

    for ln in payload.lines:
        po_line = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.id == ln.po_line_id).first()
        if not po_line or po_line.order_id != po.id:
            raise HTTPException(400, f"Invalid PO line {ln.po_line_id}")
        remaining = Decimal(po_line.quantity) - Decimal(po_line.received_quantity)
        if Decimal(ln.quantity) <= 0:
            raise HTTPException(400, "Quantity must be > 0")
        if Decimal(ln.quantity) > remaining:
            raise HTTPException(400,
                f"Line {po_line.product.sku}: receiving {ln.quantity} exceeds remaining {remaining}")

        # create or update batch
        batch = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == po_line.product_id,
            InventoryBatch.warehouse_id == po.warehouse_id,
            InventoryBatch.batch_number == ln.batch_number,
        ).first()
        unit_cost = ln.unit_cost if ln.unit_cost is not None else po_line.unit_price
        if not batch:
            batch = InventoryBatch(
                batch_number=ln.batch_number,
                product_id=po_line.product_id,
                warehouse_id=po.warehouse_id,
                manufacture_date=ln.manufacture_date,
                expiry_date=ln.expiry_date,
                quantity_on_hand=Decimal(ln.quantity),
                cost_per_unit=unit_cost,
                status=BatchStatus.RELEASED,  # auto-release on receipt for Phase 1 (QA module can override)
            )
            db.add(batch)
            db.flush()
        else:
            batch.quantity_on_hand = Decimal(batch.quantity_on_hand) + Decimal(ln.quantity)

        # GRN line
        grn_line = GoodsReceiptLine(
            receipt_id=grn.id, po_line_id=po_line.id, product_id=po_line.product_id,
            batch_number=ln.batch_number, quantity=ln.quantity,
            manufacture_date=ln.manufacture_date, expiry_date=ln.expiry_date,
            unit_cost=unit_cost, batch_id=batch.id,
        )
        db.add(grn_line)

        # Stock movement
        mv = StockMovement(
            batch_id=batch.id, movement_type=StockMovementType.GRN,
            quantity=Decimal(ln.quantity),
            reference_type="GRN", reference_id=grn.id, reference_number=grn.grn_number,
            user_id=current.id, notes=f"Receipt against {po.po_number}",
        )
        db.add(mv)

        # Update PO line
        po_line.received_quantity = Decimal(po_line.received_quantity) + Decimal(ln.quantity)

    # Update PO status
    all_lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.order_id == po.id).all()
    if all(Decimal(l.received_quantity) >= Decimal(l.quantity) for l in all_lines):
        po.status = PurchaseOrderStatus.RECEIVED
    else:
        po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

    log_audit(db, current, "CREATE", "GoodsReceipt", grn.id, {"grn_number": grn.grn_number, "po": po.po_number})
    db.commit()
    db.refresh(grn)
    return {"id": grn.id, "grn_number": grn.grn_number, "po_status": po.status.value}


@grn_router.get("")
def list_grns(db: Session = Depends(get_db),
              _: User = Depends(require_permission("purchase:read"))):
    grns = db.query(GoodsReceipt).order_by(GoodsReceipt.created_at.desc()).limit(100).all()
    out = []
    for g in grns:
        out.append({
            "id": g.id, "grn_number": g.grn_number,
            "purchase_order_id": g.purchase_order_id,
            "po_number": g.purchase_order.po_number if g.purchase_order else None,
            "supplier_name": g.purchase_order.supplier.name if g.purchase_order and g.purchase_order.supplier else None,
            "received_date": g.received_date.isoformat() if g.received_date else None,
            "notes": g.notes,
            "line_count": len(g.lines),
            "created_at": g.created_at.isoformat(),
        })
    return out
