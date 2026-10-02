"""Warehouses + inventory batches + stock movements."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from database import get_db
from models import (
    Warehouse, InventoryBatch, StockMovement, Product, User, BatchStatus,
    StockMovementType,
)
from schemas import (
    WarehouseCreate, WarehouseOut, BatchOut, StockAdjustment, StockMovementOut,
)
from auth import require_permission
from helpers import log_audit


wh_router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])
inv_router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _batch_out(b: InventoryBatch) -> BatchOut:
    days = None
    if b.expiry_date:
        days = (b.expiry_date - date.today()).days
    return BatchOut(
        id=b.id, batch_number=b.batch_number, product_id=b.product_id,
        product_name=b.product.name if b.product else None,
        product_sku=b.product.sku if b.product else None,
        warehouse_id=b.warehouse_id,
        warehouse_name=b.warehouse.name if b.warehouse else None,
        manufacture_date=b.manufacture_date, expiry_date=b.expiry_date,
        quantity_on_hand=b.quantity_on_hand,
        quantity_reserved=b.quantity_reserved,
        quantity_available=(b.quantity_on_hand - b.quantity_reserved),
        cost_per_unit=b.cost_per_unit,
        status=b.status.value if hasattr(b.status, "value") else b.status,
        days_to_expiry=days,
        created_at=b.created_at,
    )


# ---- Warehouses ----
@wh_router.get("", response_model=List[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db),
                    _: User = Depends(require_permission("warehouse:read"))):
    return db.query(Warehouse).order_by(Warehouse.name).all()


@wh_router.post("", response_model=WarehouseOut)
def create_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db),
                     current: User = Depends(require_permission("warehouse:write"))):
    if db.query(Warehouse).filter(Warehouse.code == payload.code).first():
        raise HTTPException(400, "Warehouse code already exists")
    w = Warehouse(**payload.model_dump())
    db.add(w)
    log_audit(db, current, "CREATE", "Warehouse", w.id, {"code": w.code})
    db.commit()
    db.refresh(w)
    return w


# ---- Batches ----
@inv_router.get("/batches", response_model=List[BatchOut])
def list_batches(
    search: Optional[str] = None,
    product_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    status: Optional[str] = None,
    near_expiry_days: Optional[int] = None,
    expired_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:read")),
):
    q = db.query(InventoryBatch).join(Product)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter(or_(InventoryBatch.batch_number.ilike(s), Product.name.ilike(s), Product.sku.ilike(s)))
    if product_id:
        q = q.filter(InventoryBatch.product_id == product_id)
    if warehouse_id:
        q = q.filter(InventoryBatch.warehouse_id == warehouse_id)
    if status:
        q = q.filter(InventoryBatch.status == status)
    today = date.today()
    if near_expiry_days:
        cutoff = today + timedelta(days=near_expiry_days)
        q = q.filter(InventoryBatch.expiry_date <= cutoff, InventoryBatch.expiry_date >= today)
    if expired_only:
        q = q.filter(InventoryBatch.expiry_date < today)
    batches = q.order_by(InventoryBatch.expiry_date.asc().nullslast()).all()
    return [_batch_out(b) for b in batches]


@inv_router.get("/movements", response_model=List[StockMovementOut])
def list_movements(
    product_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory:read")),
):
    q = db.query(StockMovement).join(InventoryBatch)
    if product_id:
        q = q.filter(InventoryBatch.product_id == product_id)
    if warehouse_id:
        q = q.filter(InventoryBatch.warehouse_id == warehouse_id)
    movements = q.order_by(StockMovement.created_at.desc()).limit(limit).all()
    out = []
    for m in movements:
        b = m.batch
        out.append(StockMovementOut(
            id=m.id, batch_id=m.batch_id,
            product_name=b.product.name if b and b.product else None,
            product_sku=b.product.sku if b and b.product else None,
            batch_number=b.batch_number if b else None,
            warehouse_name=b.warehouse.name if b and b.warehouse else None,
            movement_type=m.movement_type.value if hasattr(m.movement_type, "value") else m.movement_type,
            quantity=m.quantity, reference_type=m.reference_type,
            reference_number=m.reference_number, notes=m.notes,
            user_email=None, created_at=m.created_at,
        ))
    return out


@inv_router.post("/adjust")
def adjust_stock(payload: StockAdjustment, db: Session = Depends(get_db),
                 current: User = Depends(require_permission("inventory:adjust"))):
    b = db.query(InventoryBatch).filter(InventoryBatch.id == payload.batch_id).first()
    if not b:
        raise HTTPException(404, "Batch not found")
    new_qty = b.quantity_on_hand + payload.quantity_delta
    if new_qty < 0:
        raise HTTPException(400, "Adjustment would make stock negative")
    b.quantity_on_hand = new_qty
    mv = StockMovement(
        batch_id=b.id, movement_type=StockMovementType.ADJUSTMENT,
        quantity=payload.quantity_delta,
        reference_type="ADJ", notes=payload.notes, user_id=current.id,
    )
    db.add(mv)
    log_audit(db, current, "UPDATE", "InventoryBatch", b.id,
              {"adjust": str(payload.quantity_delta), "notes": payload.notes})
    db.commit()
    return {"message": "Stock adjusted", "new_quantity": str(b.quantity_on_hand)}


@inv_router.post("/batches/{batch_id}/release")
def release_batch(batch_id: str, db: Session = Depends(get_db),
                  current: User = Depends(require_permission("quality:release"))):
    b = db.query(InventoryBatch).filter(InventoryBatch.id == batch_id).first()
    if not b:
        raise HTTPException(404, "Batch not found")
    if b.status != BatchStatus.QUARANTINE and b.status != BatchStatus.HOLD:
        raise HTTPException(400, "Batch not in a releasable state")
    b.status = BatchStatus.RELEASED
    log_audit(db, current, "APPROVE", "InventoryBatch", b.id, {"action": "release"})
    db.commit()
    return {"message": "Batch released"}
