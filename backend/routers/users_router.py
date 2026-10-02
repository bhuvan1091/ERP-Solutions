"""User and role management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import User, Role
from schemas import UserCreate, UserOut, RoleOut
from auth import get_current_user, require_permission, hash_password
from helpers import log_audit


router = APIRouter(prefix="/api/users", tags=["users"])
role_router = APIRouter(prefix="/api/roles", tags=["roles"])


def _user_to_out(user: User, db: Session) -> UserOut:
    role = db.query(Role).filter(Role.id == user.role_id).first()
    return UserOut(
        id=user.id, email=user.email, full_name=user.full_name,
        role_id=user.role_id,
        role_code=role.code if role else None,
        role_name=role.name if role else None,
        phone=user.phone, is_active=user.is_active,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )


@router.get("", response_model=List[UserOut])
def list_users(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:read")),
):
    q = db.query(User)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter((User.email.ilike(s)) | (User.full_name.ilike(s)))
    users = q.order_by(User.created_at.desc()).all()
    return [_user_to_out(u, db) for u in users]


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("admin:write")),
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(400, "Email already in use")
    role = db.query(Role).filter(Role.code == payload.role_code).first()
    if not role:
        raise HTTPException(400, f"Role {payload.role_code} not found")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    log_audit(db, current, "CREATE", "User", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return _user_to_out(user, db)


@role_router.get("", response_model=List[RoleOut])
def list_roles(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    roles = db.query(Role).order_by(Role.name).all()
    return roles
