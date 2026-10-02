"""Advertising / marketing campaigns (Phase 1 stubs with mock data)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import AdPlatformConnection, AdCampaign, SalesOrder, User
from schemas import AdCampaignOut, AdPlatformConnectionOut
from auth import require_permission


router = APIRouter(prefix="/api/advertising", tags=["advertising"])


def _campaign_out(c: AdCampaign) -> AdCampaignOut:
    clicks = c.clicks or 0
    imp = c.impressions or 0
    conv = c.conversions or 0
    spend = Decimal(c.spend_to_date or 0)
    cv = Decimal(c.conversion_value or 0)
    ctr = (clicks / imp * 100) if imp else 0
    cpc = float(spend / clicks) if clicks else 0
    cpa = float(spend / conv) if conv else 0
    roas = float(cv / spend) if spend else 0
    return AdCampaignOut(
        id=c.id, external_id=c.external_id, platform=c.platform,
        account_id=c.account_id, name=c.name, objective=c.objective,
        status=c.status, product_id=c.product_id,
        product_name=c.product.name if c.product else None,
        start_date=c.start_date, end_date=c.end_date,
        daily_budget=c.daily_budget, total_budget=c.total_budget,
        spend_to_date=spend, impressions=imp, clicks=clicks,
        conversions=conv, conversion_value=cv,
        ctr=round(ctr, 2), cpc=round(cpc, 2), cpa=round(cpa, 2), roas=round(roas, 2),
        created_at=c.created_at,
    )


@router.get("/connections", response_model=List[AdPlatformConnectionOut])
def list_connections(db: Session = Depends(get_db),
                     _: User = Depends(require_permission("advertising:read"))):
    return db.query(AdPlatformConnection).order_by(AdPlatformConnection.platform).all()


@router.post("/connections", response_model=AdPlatformConnectionOut)
def create_connection(
    platform: str, account_name: str, account_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("advertising:write")),
):
    conn = AdPlatformConnection(
        platform=platform.upper(),
        account_name=account_name,
        account_id=account_id,
        status="CONNECTED",
        last_sync_at=datetime.now(timezone.utc),
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


@router.get("/campaigns", response_model=List[AdCampaignOut])
def list_campaigns(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("advertising:read")),
):
    q = db.query(AdCampaign)
    if platform:
        q = q.filter(AdCampaign.platform == platform.upper())
    if status:
        q = q.filter(AdCampaign.status == status.upper())
    campaigns = q.order_by(AdCampaign.created_at.desc()).all()
    return [_campaign_out(c) for c in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=AdCampaignOut)
def get_campaign(campaign_id: str, db: Session = Depends(get_db),
                 _: User = Depends(require_permission("advertising:read"))):
    c = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not c:
        raise HTTPException(404, "Campaign not found")
    return _campaign_out(c)


@router.get("/summary")
def summary(db: Session = Depends(get_db),
            _: User = Depends(require_permission("advertising:read"))):
    campaigns = db.query(AdCampaign).all()
    by_platform: dict[str, dict] = {}
    total = {"spend": Decimal(0), "clicks": 0, "conversions": 0, "revenue": Decimal(0)}
    for c in campaigns:
        p = c.platform
        bp = by_platform.setdefault(p, {"platform": p, "campaigns": 0, "spend": Decimal(0),
                                         "clicks": 0, "conversions": 0, "revenue": Decimal(0)})
        bp["campaigns"] += 1
        bp["spend"] += Decimal(c.spend_to_date or 0)
        bp["clicks"] += c.clicks or 0
        bp["conversions"] += c.conversions or 0
        bp["revenue"] += Decimal(c.conversion_value or 0)
        total["spend"] += Decimal(c.spend_to_date or 0)
        total["clicks"] += c.clicks or 0
        total["conversions"] += c.conversions or 0
        total["revenue"] += Decimal(c.conversion_value or 0)

    # ERP-attributed revenue from sales orders tagged with campaign_id
    erp_attributed = {}
    rows = db.query(SalesOrder).filter(SalesOrder.campaign_id.isnot(None)).all()
    for so in rows:
        if so.campaign_id:
            erp_attributed[so.campaign_id] = erp_attributed.get(so.campaign_id, Decimal(0)) + Decimal(so.total or 0)

    return {
        "platforms": [
            {
                **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in bp.items()},
                "roas": round(float(bp["revenue"] / bp["spend"]), 2) if bp["spend"] else 0,
            }
            for bp in by_platform.values()
        ],
        "totals": {
            "spend": str(total["spend"]), "clicks": total["clicks"],
            "conversions": total["conversions"], "revenue": str(total["revenue"]),
            "roas": round(float(total["revenue"] / total["spend"]), 2) if total["spend"] else 0,
        },
        "erp_attributed_revenue": str(sum(erp_attributed.values(), Decimal(0))),
    }
