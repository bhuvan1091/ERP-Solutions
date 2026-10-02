"""Suppliers CRUD."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Supplier, User
from schemas import SupplierCreate, SupplierUpdate, SupplierOut
from auth import require_permission
from helpers import log_audit


router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _gen_code(db: Session) -> str:
    count = db.query(Supplier).count()
    return f"SUP-{(count + 1):04d}"


@router.get("", response_model=List[SupplierOut])
def list_suppliers(
    search: Optional[str] = None,
    is_approved: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supplier:read")),
):
    q = db.query(Supplier)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter((Supplier.name.ilike(s)) | (Supplier.code.ilike(s)) | (Supplier.email.ilike(s)))
    if is_approved is not None:
        q = q.filter(Supplier.is_approved == is_approved)
    return q.order_by(Supplier.name).all()


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: str, db: Session = Depends(get_db),
                 _: User = Depends(require_permission("supplier:read"))):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    return s


@router.post("", response_model=SupplierOut)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("supplier:write"))):
    code = payload.code or _gen_code(db)
    if db.query(Supplier).filter(Supplier.code == code).first():
        raise HTTPException(400, "Supplier code already exists")
    s = Supplier(**payload.model_dump(exclude={"code"}), code=code)
    db.add(s)
    log_audit(db, current, "CREATE", "Supplier", s.id, {"name": s.name})
    db.commit()
    db.refresh(s)
    return s


@router.patch("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: str, payload: SupplierUpdate, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("supplier:write"))):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    for k, v in payload.model_dump(exclude_unset=True, exclude={"code"}).items():
        setattr(s, k, v)
    log_audit(db, current, "UPDATE", "Supplier", s.id)
    db.commit()
    db.refresh(s)
    return s


@router.post("/{supplier_id}/approve", response_model=SupplierOut)
def approve_supplier(supplier_id: str, db: Session = Depends(get_db),
                     current: User = Depends(require_permission("supplier:approve"))):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    s.is_approved = True
    log_audit(db, current, "APPROVE", "Supplier", s.id)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: str, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("supplier:delete"))):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "Supplier not found")
    s.is_active = False
    log_audit(db, current, "DELETE", "Supplier", s.id)
    db.commit()
    return {"message": "Supplier deactivated"}
