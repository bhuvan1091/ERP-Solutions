"""Nutrition ERP - FastAPI entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

load_dotenv(Path(__file__).parent / ".env")

from database import engine, Base
import models  # noqa: F401 ensure models are imported for metadata

# Create all tables (dev convenience; prod should use Alembic migrations)
Base.metadata.create_all(bind=engine)

from routers.auth_router import router as auth_router
from routers.users_router import router as users_router, role_router
from routers.products_router import router as products_router, cat_router
from routers.suppliers_router import router as suppliers_router
from routers.customers_router import router as customers_router
from routers.inventory_router import wh_router, inv_router
from routers.purchase_router import router as po_router, grn_router
from routers.sales_router import router as so_router
from routers.advertising_router import router as ads_router
from routers.dashboard_router import router as dash_router, audit_router


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nutrition ERP",
    description="Enterprise ERP for nutrition / nutraceutical companies",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(role_router)
app.include_router(products_router)
app.include_router(cat_router)
app.include_router(suppliers_router)
app.include_router(customers_router)
app.include_router(wh_router)
app.include_router(inv_router)
app.include_router(po_router)
app.include_router(grn_router)
app.include_router(so_router)
app.include_router(ads_router)
app.include_router(dash_router)
app.include_router(audit_router)


@app.get("/api")
def api_root():
    return {
        "name": "Nutrition ERP API",
        "version": "1.0.0",
        "status": "ok",
        "docs": "/api/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.on_event("startup")
def on_startup():
    """Run seed on empty DB so the app has demo data to show."""
    from seed import seed_if_empty
    from database import SessionLocal
    db = SessionLocal()
    try:
        seed_if_empty(db)
    except Exception as e:
        logger.exception("Seed failed: %s", e)
    finally:
        db.close()
