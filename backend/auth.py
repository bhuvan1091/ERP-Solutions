"""JWT authentication, password hashing, RBAC permissions."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User, Role


SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_EXPIRE_MIN = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))
REFRESH_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ======= PERMISSIONS CATALOG =======
PERMISSIONS = {
    # Products
    "product:read", "product:write", "product:delete",
    # Suppliers
    "supplier:read", "supplier:write", "supplier:delete", "supplier:approve",
    # Customers
    "customer:read", "customer:write", "customer:delete",
    # Warehouses
    "warehouse:read", "warehouse:write",
    # Inventory
    "inventory:read", "inventory:write", "inventory:adjust",
    # Purchase
    "purchase:read", "purchase:write", "purchase:approve", "purchase:receive",
    # Sales
    "sales:read", "sales:write", "sales:approve", "sales:dispatch",
    # Finance
    "finance:read", "finance:write",
    # Quality
    "quality:read", "quality:write", "quality:release",
    # Manufacturing
    "manufacturing:read", "manufacturing:write",
    # Marketing / Advertising
    "advertising:read", "advertising:write", "advertising:approve",
    # Dashboard
    "dashboard:read",
    # Admin
    "admin:read", "admin:write",
    # Audit
    "audit:read",
}

ALL_PERMS = sorted(PERMISSIONS)

READ_ONLY_PERMS = [p for p in ALL_PERMS if p.endswith(":read")]

# Role => permission mapping
ROLE_PERMISSIONS = {
    "SUPER_ADMIN": ALL_PERMS,
    "COMPANY_ADMIN": ALL_PERMS,
    "MANAGING_DIRECTOR": ALL_PERMS,
    "FINANCE_MANAGER": READ_ONLY_PERMS + [
        "finance:write", "purchase:approve", "sales:approve",
    ],
    "PROCUREMENT_MANAGER": READ_ONLY_PERMS + [
        "supplier:write", "supplier:approve", "purchase:write",
        "purchase:approve", "purchase:receive", "product:write",
    ],
    "WAREHOUSE_MANAGER": READ_ONLY_PERMS + [
        "inventory:write", "inventory:adjust", "warehouse:write",
        "purchase:receive", "sales:dispatch",
    ],
    "PRODUCTION_MANAGER": READ_ONLY_PERMS + [
        "manufacturing:write", "inventory:write",
    ],
    "QUALITY_MANAGER": READ_ONLY_PERMS + [
        "quality:write", "quality:release",
    ],
    "SALES_MANAGER": READ_ONLY_PERMS + [
        "customer:write", "sales:write", "sales:approve", "sales:dispatch",
    ],
    "SALES_REPRESENTATIVE": [
        "dashboard:read", "customer:read", "customer:write",
        "product:read", "sales:read", "sales:write", "inventory:read",
    ],
    "MARKETING_MANAGER": READ_ONLY_PERMS + [
        "advertising:write", "advertising:approve", "customer:write",
    ],
    "MARKETING_EXECUTIVE": [
        "dashboard:read", "advertising:read", "advertising:write",
        "customer:read", "product:read", "sales:read",
    ],
    "HR_MANAGER": [
        "dashboard:read", "admin:read", "admin:write", "audit:read",
    ],
    "AUDITOR": READ_ONLY_PERMS,
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: str, token_type: str = "access") -> str:
    expire_delta = (
        timedelta(minutes=ACCESS_EXPIRE_MIN) if token_type == "access"
        else timedelta(days=REFRESH_EXPIRE_DAYS)
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + expire_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_permission(*required: str):
    def dep(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if not role:
            raise HTTPException(status_code=403, detail="No role assigned")
        perms = set(role.permissions or [])
        if not perms.intersection(required) and not any(p in perms for p in required):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Required: {list(required)}",
            )
        return user
    return dep
