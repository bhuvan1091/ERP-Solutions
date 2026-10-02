"""Company settings router: get / update company profile, logo upload, bank details."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional
import base64

from database import get_db
from models import Company, User
from auth import require_permission
from helpers import log_audit


router = APIRouter(prefix="/api/company", tags=["company"])


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    legal_name: Optional[str] = None
    gstin: Optional[str] = None
    fssai_license: Optional[str] = None
    address: Optional[str] = None
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    logo_url: Optional[str] = None
    logo_base64: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_branch: Optional[str] = None
    upi_id: Optional[str] = None
    invoice_notes: Optional[str] = None
    finance_email: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    gstin: Optional[str] = None
    fssai_license: Optional[str] = None
    address: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    logo_base64: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_branch: Optional[str] = None
    upi_id: Optional[str] = None
    invoice_notes: Optional[str] = None
    finance_email: Optional[str] = None


def _get_company(db: Session) -> Company:
    c = db.query(Company).first()
    if not c:
        c = Company(name="GreenPeak Nutrition Pvt Ltd")
        db.add(c); db.commit(); db.refresh(c)
    return c


@router.get("", response_model=CompanyOut)
def get_company(db: Session = Depends(get_db), _: User = Depends(require_permission("dashboard:read"))):
    return _get_company(db)


@router.patch("", response_model=CompanyOut)
def update_company(
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("admin:write")),
):
    c = _get_company(db)
    data = payload.model_dump(exclude_unset=True)

    # Logo size guard: data URL ≤ 500 KB
    if "logo_base64" in data and data["logo_base64"]:
        s = data["logo_base64"]
        if len(s) > 700_000:   # ~500KB after b64 overhead
            raise HTTPException(400, "Logo image too large; please upload under 500KB.")
        if not s.startswith("data:image/"):
            raise HTTPException(400, "logo_base64 must be a data URL (data:image/...;base64,...)")

    for k, v in data.items():
        setattr(c, k, v)
    log_audit(db, current, "UPDATE", "Company", c.id, {"fields": list(data.keys())})
    db.commit()
    db.refresh(c)
    return c
