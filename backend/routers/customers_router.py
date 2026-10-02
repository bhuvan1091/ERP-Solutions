"""Customers CRUD."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Customer, User
from schemas import CustomerCreate, CustomerUpdate, CustomerOut
from auth import require_permission
from helpers import log_audit


router = APIRouter(prefix="/api/customers", tags=["customers"])


def _gen_code(db: Session) -> str:
    count = db.query(Customer).count()
    return f"CUST-{(count + 1):04d}"


@router.get("", response_model=List[CustomerOut])
def list_customers(
    search: Optional[str] = None,
    customer_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("customer:read")),
):
    q = db.query(Customer)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter((Customer.name.ilike(s)) | (Customer.code.ilike(s)) | (Customer.email.ilike(s)))
    if customer_type:
        q = q.filter(Customer.customer_type == customer_type)
    return q.order_by(Customer.name).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: str, db: Session = Depends(get_db),
                 _: User = Depends(require_permission("customer:read"))):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    return c


@router.post("", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("customer:write"))):
    code = payload.code or _gen_code(db)
    if db.query(Customer).filter(Customer.code == code).first():
        raise HTTPException(400, "Customer code already exists")
    c = Customer(**payload.model_dump(exclude={"code"}), code=code)
    db.add(c)
    log_audit(db, current, "CREATE", "Customer", c.id, {"name": c.name})
    db.commit()
    db.refresh(c)
    return c


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: str, payload: CustomerUpdate, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("customer:write"))):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    for k, v in payload.model_dump(exclude_unset=True, exclude={"code"}).items():
        setattr(c, k, v)
    log_audit(db, current, "UPDATE", "Customer", c.id)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{customer_id}")
def delete_customer(customer_id: str, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("customer:delete"))):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    c.is_active = False
    log_audit(db, current, "DELETE", "Customer", c.id)
    db.commit()
    return {"message": "Customer deactivated"}
