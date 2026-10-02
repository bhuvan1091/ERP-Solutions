"""Helpers used across routers."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import AuditLog, User


def log_audit(db: Session, user: User | None, action: str, entity_type: str,
              entity_id: str | None = None, details: dict | None = None):
    """Append audit log. Caller commits."""
    log = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )
    db.add(log)


def next_sequence_number(db: Session, prefix: str, table_model, column_name: str) -> str:
    """Generate PO-00001, GRN-00001, SO-00001 etc"""
    count = db.query(table_model).count()
    return f"{prefix}-{(count + 1):05d}"
