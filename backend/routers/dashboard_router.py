"""Dashboard aggregates + audit log viewer."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import (
    Product, Supplier, Customer, Warehouse, InventoryBatch, StockMovement,
    PurchaseOrder, SalesOrder, AdCampaign, AuditLog, User,
    BatchStatus, PurchaseOrderStatus, SalesOrderStatus,
)
from schemas import DashboardResponse, DashboardKPI, AuditLogOut
from auth import require_permission, get_current_user


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
audit_router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db),
              _: User = Depends(require_permission("dashboard:read"))):
    today = date.today()
    thirty_days = today - timedelta(days=30)
    sixty_days_future = today + timedelta(days=60)

    # KPIs
    revenue_30d = db.query(func.coalesce(func.sum(SalesOrder.total), 0)).filter(
        SalesOrder.order_date >= thirty_days,
        SalesOrder.status != SalesOrderStatus.CANCELLED,
    ).scalar() or Decimal(0)
    po_pending = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.status == PurchaseOrderStatus.PENDING_APPROVAL
    ).scalar() or 0
    so_pending = db.query(func.count(SalesOrder.id)).filter(
        SalesOrder.status.in_([SalesOrderStatus.CONFIRMED, SalesOrderStatus.ALLOCATED])
    ).scalar() or 0
    inv_valuation = db.query(func.coalesce(func.sum(
        InventoryBatch.quantity_on_hand * InventoryBatch.cost_per_unit
    ), 0)).filter(InventoryBatch.status == BatchStatus.RELEASED).scalar() or Decimal(0)

    near_exp_count = db.query(func.count(InventoryBatch.id)).filter(
        InventoryBatch.expiry_date <= sixty_days_future,
        InventoryBatch.expiry_date >= today,
        InventoryBatch.quantity_on_hand > 0,
    ).scalar() or 0
    expired_count = db.query(func.count(InventoryBatch.id)).filter(
        InventoryBatch.expiry_date < today,
        InventoryBatch.quantity_on_hand > 0,
    ).scalar() or 0

    ad_spend = db.query(func.coalesce(func.sum(AdCampaign.spend_to_date), 0)).scalar() or Decimal(0)
    ad_revenue = db.query(func.coalesce(func.sum(AdCampaign.conversion_value), 0)).scalar() or Decimal(0)
    roas = round(float(ad_revenue / ad_spend), 2) if ad_spend else 0

    product_count = db.query(func.count(Product.id)).scalar() or 0
    customer_count = db.query(func.count(Customer.id)).scalar() or 0

    kpis = [
        DashboardKPI(label="Revenue (30d)", value=str(revenue_30d), hint="Confirmed sales orders"),
        DashboardKPI(label="Inventory Valuation", value=str(inv_valuation), hint="Released stock at cost"),
        DashboardKPI(label="Pending POs", value=po_pending, hint="Awaiting approval"),
        DashboardKPI(label="Open Sales Orders", value=so_pending, hint="Pending fulfillment"),
        DashboardKPI(label="Near-Expiry Batches", value=near_exp_count, hint="Expires in ≤60 days"),
        DashboardKPI(label="Expired Batches", value=expired_count, hint="With stock on hand"),
        DashboardKPI(label="Ad Spend (All)", value=str(ad_spend), hint="Across all platforms"),
        DashboardKPI(label="Platform ROAS", value=roas, hint="Revenue / spend"),
    ]

    # Revenue trend - last 14 days
    trend = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        total = db.query(func.coalesce(func.sum(SalesOrder.total), 0)).filter(
            SalesOrder.order_date == d,
            SalesOrder.status != SalesOrderStatus.CANCELLED,
        ).scalar() or Decimal(0)
        trend.append({"date": d.isoformat(), "revenue": float(total)})

    # Low stock products
    low_stock_rows = (
        db.query(
            Product.id, Product.sku, Product.name, Product.reorder_level,
            func.coalesce(func.sum(InventoryBatch.quantity_on_hand), 0).label("stock"),
        )
        .outerjoin(InventoryBatch, (InventoryBatch.product_id == Product.id) & (InventoryBatch.status == BatchStatus.RELEASED))
        .filter(Product.reorder_level > 0)
        .group_by(Product.id)
        .having(func.coalesce(func.sum(InventoryBatch.quantity_on_hand), 0) <= Product.reorder_level)
        .limit(10).all()
    )
    low_stock = [
        {"id": r.id, "sku": r.sku, "name": r.name,
         "stock_on_hand": float(r.stock), "reorder_level": float(r.reorder_level)}
        for r in low_stock_rows
    ]

    # Near-expiry batches
    near_rows = db.query(InventoryBatch).filter(
        InventoryBatch.expiry_date <= sixty_days_future,
        InventoryBatch.expiry_date >= today,
        InventoryBatch.quantity_on_hand > 0,
    ).order_by(InventoryBatch.expiry_date.asc()).limit(10).all()
    near_expiry = [
        {"id": b.id, "batch_number": b.batch_number,
         "product_name": b.product.name if b.product else None,
         "warehouse": b.warehouse.name if b.warehouse else None,
         "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
         "days_to_expiry": (b.expiry_date - today).days if b.expiry_date else None,
         "quantity": float(b.quantity_on_hand)}
        for b in near_rows
    ]

    # Pending approvals (POs awaiting approval)
    pending = db.query(PurchaseOrder).filter(
        PurchaseOrder.status == PurchaseOrderStatus.PENDING_APPROVAL
    ).order_by(PurchaseOrder.created_at.desc()).limit(5).all()
    pending_approvals = [
        {"id": p.id, "po_number": p.po_number,
         "supplier_name": p.supplier.name if p.supplier else None,
         "total": float(p.total), "created_at": p.created_at.isoformat()}
        for p in pending
    ]

    # Top products by SO value (last 30 days)
    top_rows = (
        db.query(
            Product.id, Product.name, Product.sku,
            func.coalesce(func.sum(SalesOrder.total), 0).label("revenue"),
        )
        .select_from(SalesOrder)
        .join(SalesOrder.lines)
        .join(Product, Product.id == SalesOrder.lines.property.mapper.class_.product_id)
        .filter(SalesOrder.order_date >= thirty_days)
        .group_by(Product.id).order_by(func.sum(SalesOrder.total).desc())
        .limit(5).all()
    ) if False else []  # keep simple

    # simpler: top by SO line total
    from models import SalesOrderLine
    top_rows_q = (
        db.query(
            Product.id, Product.name, Product.sku,
            func.coalesce(func.sum(SalesOrderLine.line_total), 0).label("revenue"),
        )
        .join(SalesOrderLine, SalesOrderLine.product_id == Product.id)
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.order_id)
        .filter(SalesOrder.order_date >= thirty_days,
                SalesOrder.status != SalesOrderStatus.CANCELLED)
        .group_by(Product.id)
        .order_by(func.sum(SalesOrderLine.line_total).desc())
        .limit(5).all()
    )
    top_products = [
        {"id": r.id, "sku": r.sku, "name": r.name, "revenue": float(r.revenue)}
        for r in top_rows_q
    ]

    # Campaign summary
    cs_rows = (
        db.query(
            AdCampaign.platform,
            func.count(AdCampaign.id).label("count"),
            func.coalesce(func.sum(AdCampaign.spend_to_date), 0).label("spend"),
            func.coalesce(func.sum(AdCampaign.conversion_value), 0).label("revenue"),
        ).group_by(AdCampaign.platform).all()
    )
    campaign_summary = [
        {"platform": r.platform, "campaigns": r.count,
         "spend": float(r.spend), "revenue": float(r.revenue),
         "roas": round(float(r.revenue / r.spend), 2) if r.spend else 0}
        for r in cs_rows
    ]

    # Recent audit activity
    acts = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
    recent_activity = [
        {"id": a.id, "user_email": a.user_email, "action": a.action,
         "entity_type": a.entity_type, "created_at": a.created_at.isoformat()}
        for a in acts
    ]

    return DashboardResponse(
        kpis=kpis, revenue_trend=trend, low_stock=low_stock,
        near_expiry=near_expiry, pending_approvals=pending_approvals,
        top_products=top_products, campaign_summary=campaign_summary,
        recent_activity=recent_activity,
    )


# ====== AUDIT ======
@audit_router.get("", response_model=List[AuditLogOut])
def list_audit_logs(
    limit: int = Query(100, le=500),
    entity_type: str | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:read")),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if action:
        q = q.filter(AuditLog.action == action)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()
