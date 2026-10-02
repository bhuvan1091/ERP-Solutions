"""Pydantic schemas (DTOs) for request/response validation."""
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ======= Auth =======
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    permissions: List[str] = []
    is_active: bool


# ======= Users =======
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)
    role_code: str
    phone: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    role_id: str
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


# ======= Products =======
class ProductCategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None


class ProductCategoryOut(ProductCategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class ProductCreate(BaseModel):
    sku: Optional[str] = None  # auto-gen if blank
    name: str
    brand: Optional[str] = None
    category_id: Optional[str] = None
    product_type: str = "FINISHED_GOOD"
    status: str = "ACTIVE"
    description: Optional[str] = None
    unit_of_measure: str = "unit"
    pack_size: Optional[str] = None
    flavour: Optional[str] = None
    purchase_price: Decimal = Decimal("0")
    selling_price: Decimal = Decimal("0")
    mrp: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("18")
    hsn_code: Optional[str] = None
    shelf_life_days: int = 365
    reorder_level: Decimal = Decimal("0")
    min_stock: Decimal = Decimal("0")
    max_stock: Decimal = Decimal("0")
    allergens: List[str] = []
    nutrition_facts: dict = {}
    ingredients: Optional[str] = None
    image_url: Optional[str] = None
    barcode: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[str] = None
    product_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    unit_of_measure: Optional[str] = None
    pack_size: Optional[str] = None
    flavour: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    mrp: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    hsn_code: Optional[str] = None
    shelf_life_days: Optional[int] = None
    reorder_level: Optional[Decimal] = None
    min_stock: Optional[Decimal] = None
    max_stock: Optional[Decimal] = None
    allergens: Optional[List[str]] = None
    nutrition_facts: Optional[dict] = None
    ingredients: Optional[str] = None
    image_url: Optional[str] = None
    barcode: Optional[str] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sku: str
    barcode: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    product_type: str
    status: str
    description: Optional[str] = None
    unit_of_measure: str
    pack_size: Optional[str] = None
    flavour: Optional[str] = None
    purchase_price: Decimal
    selling_price: Decimal
    mrp: Decimal
    tax_rate: Decimal
    hsn_code: Optional[str] = None
    shelf_life_days: int
    reorder_level: Decimal
    min_stock: Decimal
    max_stock: Decimal
    allergens: List[str] = []
    nutrition_facts: dict = {}
    ingredients: Optional[str] = None
    image_url: Optional[str] = None
    stock_on_hand: Optional[Decimal] = Decimal("0")
    created_at: datetime


# ======= Suppliers =======
class SupplierCreate(BaseModel):
    name: str
    code: Optional[str] = None
    legal_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    payment_terms_days: int = 30
    is_approved: bool = False
    notes: Optional[str] = None


class SupplierUpdate(SupplierCreate):
    name: Optional[str] = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    legal_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    payment_terms_days: int
    is_approved: bool
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime


# ======= Customers =======
class CustomerCreate(BaseModel):
    name: str
    code: Optional[str] = None
    customer_type: str = "RETAIL"
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    credit_limit: Decimal = Decimal("0")
    payment_terms_days: int = 0


class CustomerUpdate(CustomerCreate):
    name: Optional[str] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    customer_type: str
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    credit_limit: Decimal
    payment_terms_days: int
    is_active: bool
    created_at: datetime


# ======= Warehouses =======
class WarehouseCreate(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_active: bool


# ======= Inventory / Batch =======
class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    batch_number: str
    product_id: str
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    warehouse_id: str
    warehouse_name: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    cost_per_unit: Decimal
    status: str
    days_to_expiry: Optional[int] = None
    created_at: datetime


class StockAdjustment(BaseModel):
    batch_id: str
    quantity_delta: Decimal  # +/- adjustment
    notes: str = ""


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    batch_id: str
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    batch_number: Optional[str] = None
    warehouse_name: Optional[str] = None
    movement_type: str
    quantity: Decimal
    reference_type: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    user_email: Optional[str] = None
    created_at: datetime


# ======= Purchase Orders =======
class POLineCreate(BaseModel):
    product_id: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal = Decimal("18")


class POCreate(BaseModel):
    supplier_id: str
    warehouse_id: str
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[POLineCreate]


class POLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Decimal
    received_quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


class POOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    po_number: str
    supplier_id: str
    supplier_name: Optional[str] = None
    warehouse_id: str
    warehouse_name: Optional[str] = None
    order_date: date
    expected_delivery_date: Optional[date] = None
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    notes: Optional[str] = None
    created_at: datetime
    lines: List[POLineOut] = []


class GRNLineCreate(BaseModel):
    po_line_id: str
    quantity: Decimal
    batch_number: str
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None


class GRNCreate(BaseModel):
    purchase_order_id: str
    received_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[GRNLineCreate]


# ======= Sales Orders =======
class SOLineCreate(BaseModel):
    product_id: str
    quantity: Decimal
    unit_price: Optional[Decimal] = None  # defaults to product selling_price
    tax_rate: Optional[Decimal] = None
    discount: Decimal = Decimal("0")


class SOCreate(BaseModel):
    customer_id: str
    warehouse_id: str
    expected_dispatch_date: Optional[date] = None
    source_channel: str = "DIRECT"
    campaign_id: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    notes: Optional[str] = None
    lines: List[SOLineCreate]


class SOLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Decimal
    dispatched_quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    discount: Decimal
    line_total: Decimal
    allocated_batch_id: Optional[str] = None
    allocated_batch_number: Optional[str] = None


class SOOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    so_number: str
    customer_id: str
    customer_name: Optional[str] = None
    warehouse_id: str
    warehouse_name: Optional[str] = None
    order_date: date
    expected_dispatch_date: Optional[date] = None
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    source_channel: str
    campaign_id: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    lines: List[SOLineOut] = []


# ======= Advertising =======
class AdCampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    external_id: Optional[str] = None
    platform: str
    account_id: Optional[str] = None
    name: str
    objective: Optional[str] = None
    status: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    daily_budget: Decimal
    total_budget: Decimal
    spend_to_date: Decimal
    impressions: int
    clicks: int
    conversions: int
    conversion_value: Decimal
    ctr: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    created_at: datetime


class AdPlatformConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    platform: str
    account_name: str
    account_id: str
    status: str
    connected_at: datetime
    last_sync_at: Optional[datetime] = None


# ======= Audit =======
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: dict = {}
    created_at: datetime


# ======= Dashboard =======
class DashboardKPI(BaseModel):
    label: str
    value: Any
    delta: Optional[float] = None
    hint: Optional[str] = None


class DashboardResponse(BaseModel):
    kpis: List[DashboardKPI]
    revenue_trend: List[dict]
    low_stock: List[dict]
    near_expiry: List[dict]
    pending_approvals: List[dict]
    top_products: List[dict]
    campaign_summary: List[dict]
    recent_activity: List[dict]
