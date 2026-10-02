"""Auth router: login, refresh, me."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError

from database import get_db
from models import User, Role, AuditLog
from schemas import LoginRequest, TokenResponse, RefreshRequest, UserMe
from auth import (
    verify_password, create_access_token, decode_token, get_current_user,
)
from helpers import log_audit


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    user.last_login_at = datetime.now(timezone.utc)
    log_audit(db, user, "LOGIN", "User", user.id)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, "access"),
        refresh_token=create_access_token(user.id, "refresh"),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == data["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id, "access"),
        refresh_token=create_access_token(user.id, "refresh"),
    )


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == user.role_id).first()
    return UserMe(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role_code=role.code if role else None,
        role_name=role.name if role else None,
        permissions=role.permissions if role else [],
        is_active=user.is_active,
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_audit(db, user, "LOGOUT", "User", user.id)
    db.commit()
    return {"message": "Logged out"}
