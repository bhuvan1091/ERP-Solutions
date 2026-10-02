"""Products CRUD."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from database import get_db
from models import Product, ProductCategory, User, InventoryBatch, BatchStatus
from schemas import (
    ProductCreate, ProductUpdate, ProductOut,
    ProductCategoryCreate, ProductCategoryOut,
)
from auth import require_permission
from helpers import log_audit


router = APIRouter(prefix="/api/products", tags=["products"])
cat_router = APIRouter(prefix="/api/product-categories", tags=["products"])


def _generate_sku(db: Session, name: str) -> str:
    base = "".join(c for c in name.upper() if c.isalnum())[:4] or "PRD"
    count = db.query(Product).count()
    return f"{base}-{(count + 1):05d}"


def _product_out(p: Product, db: Session) -> ProductOut:
    stock = db.query(func.coalesce(func.sum(InventoryBatch.quantity_on_hand), 0)).filter(
        InventoryBatch.product_id == p.id,
        InventoryBatch.status == BatchStatus.RELEASED,
    ).scalar() or Decimal("0")
    cat_name = p.category.name if p.category else None
    return ProductOut(
        id=p.id, sku=p.sku, barcode=p.barcode, name=p.name, brand=p.brand,
        category_id=p.category_id, category_name=cat_name,
        product_type=p.product_type.value if hasattr(p.product_type, "value") else p.product_type,
        status=p.status.value if hasattr(p.status, "value") else p.status,
        description=p.description, unit_of_measure=p.unit_of_measure,
        pack_size=p.pack_size, flavour=p.flavour,
        purchase_price=p.purchase_price, selling_price=p.selling_price, mrp=p.mrp,
        tax_rate=p.tax_rate, hsn_code=p.hsn_code, shelf_life_days=p.shelf_life_days,
        reorder_level=p.reorder_level, min_stock=p.min_stock, max_stock=p.max_stock,
        allergens=p.allergens or [], nutrition_facts=p.nutrition_facts or {},
        ingredients=p.ingredients, image_url=p.image_url,
        stock_on_hand=Decimal(stock), created_at=p.created_at,
    )


@router.get("", response_model=List[ProductOut])
def list_products(
    search: Optional[str] = None,
    status: Optional[str] = None,
    product_type: Optional[str] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("product:read")),
):
    q = db.query(Product)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter((Product.name.ilike(s)) | (Product.sku.ilike(s)) | (Product.brand.ilike(s)))
    if status:
        q = q.filter(Product.status == status)
    if product_type:
        q = q.filter(Product.product_type == product_type)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    products = q.order_by(Product.name).all()
    return [_product_out(p, db) for p in products]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db),
                _: User = Depends(require_permission("product:read"))):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return _product_out(p, db)


@router.post("", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("product:write")),
):
    sku = payload.sku or _generate_sku(db, payload.name)
    if db.query(Product).filter(Product.sku == sku).first():
        raise HTTPException(400, f"SKU {sku} already exists")
    p = Product(**payload.model_dump(exclude={"sku"}), sku=sku)
    db.add(p)
    log_audit(db, current, "CREATE", "Product", p.id, {"sku": sku, "name": p.name})
    db.commit()
    db.refresh(p)
    return _product_out(p, db)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("product:write")),
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    log_audit(db, current, "UPDATE", "Product", p.id, data)
    db.commit()
    db.refresh(p)
    return _product_out(p, db)


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("product:delete")),
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    # Soft-delete: discontinue instead of hard delete to preserve references
    p.status = "DISCONTINUED"
    log_audit(db, current, "DELETE", "Product", p.id)
    db.commit()
    return {"message": "Product discontinued"}


# ----- Categories -----
@cat_router.get("", response_model=List[ProductCategoryOut])
def list_categories(db: Session = Depends(get_db),
                    _: User = Depends(require_permission("product:read"))):
    return db.query(ProductCategory).order_by(ProductCategory.name).all()


@cat_router.post("", response_model=ProductCategoryOut)
def create_category(payload: ProductCategoryCreate, db: Session = Depends(get_db),
                    current: User = Depends(require_permission("product:write"))):
    c = ProductCategory(**payload.model_dump())
    db.add(c)
    log_audit(db, current, "CREATE", "ProductCategory", c.id, {"name": c.name})
    db.commit()
    db.refresh(c)
    return c
