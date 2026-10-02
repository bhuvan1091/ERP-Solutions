"""
SQLAlchemy ORM models for Nutrition ERP Phase 1.
Covers: Users/Roles, Products, Suppliers, Customers, Warehouses, Inventory
(batch/expiry), Purchase Orders, Sales Orders, Audit, Advertising stubs.
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, Date, ForeignKey,
    Text, Enum, UniqueConstraint, Index, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


# ======= ENUMS =======
class ProductType(str, enum.Enum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PACKAGING = "PACKAGING"
    SEMI_FINISHED = "SEMI_FINISHED"
    FINISHED_GOOD = "FINISHED_GOOD"
    SERVICE = "SERVICE"


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class SalesOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    ALLOCATED = "ALLOCATED"
    PARTIALLY_DISPATCHED = "PARTIALLY_DISPATCHED"
    DISPATCHED = "DISPATCHED"
    INVOICED = "INVOICED"
    CANCELLED = "CANCELLED"


class BatchStatus(str, enum.Enum):
    QUARANTINE = "QUARANTINE"
    RELEASED = "RELEASED"
    HOLD = "HOLD"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class StockMovementType(str, enum.Enum):
    GRN = "GRN"              # Goods receipt
    ISSUE = "ISSUE"          # Dispatch / sale
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT = "ADJUSTMENT"
    PRODUCTION_IN = "PRODUCTION_IN"
    PRODUCTION_OUT = "PRODUCTION_OUT"
    RETURN_IN = "RETURN_IN"
    RETURN_OUT = "RETURN_OUT"


# ======= COMPANY & USERS =======
class Company(Base):
    __tablename__ = "companies"
    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255))
    gstin = Column(String(32))
    fssai_license = Column(String(32))
    address = Column(Text)
    currency = Column(String(8), default="INR")
    timezone = Column(String(64), default="Asia/Kolkata")
    fiscal_year_start_month = Column(Integer, default=4)
    logo_url = Column(String(500))
    logo_base64 = Column(Text)              # Data URL for inline logo
    bank_name = Column(String(128))
    bank_account_name = Column(String(128))
    bank_account_number = Column(String(64))
    bank_ifsc = Column(String(32))
    bank_branch = Column(String(128))
    upi_id = Column(String(64))
    invoice_notes = Column(Text)            # default footer notes on every invoice
    finance_email = Column(String(255))     # BCC on invoice emails
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Role(Base):
    __tablename__ = "roles"
    id = Column(String(36), primary_key=True, default=new_uuid)
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    permissions = Column(JSON, default=list)  # list of permission codes
    is_system = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(32))
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    role = relationship("Role")


# ======= WAREHOUSES =======
class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(String(36), primary_key=True, default=new_uuid)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    city = Column(String(128))
    state = Column(String(128))
    pincode = Column(String(16))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ======= PRODUCTS =======
class ProductCategory(Base):
    __tablename__ = "product_categories"
    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(128), unique=True, nullable=False)
    parent_id = Column(String(36), ForeignKey("product_categories.id"))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=new_uuid)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    barcode = Column(String(64), index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(128))
    category_id = Column(String(36), ForeignKey("product_categories.id"))
    product_type = Column(Enum(ProductType), nullable=False, default=ProductType.FINISHED_GOOD)
    status = Column(Enum(ProductStatus), nullable=False, default=ProductStatus.ACTIVE)
    description = Column(Text)
    unit_of_measure = Column(String(16), default="unit")  # unit, kg, g, L, ml
    pack_size = Column(String(64))  # e.g. "500g", "60 capsules"
    flavour = Column(String(64))
    purchase_price = Column(Numeric(14, 2), default=0)
    selling_price = Column(Numeric(14, 2), default=0)
    mrp = Column(Numeric(14, 2), default=0)
    tax_rate = Column(Numeric(5, 2), default=18)  # GST %
    hsn_code = Column(String(16))
    shelf_life_days = Column(Integer, default=365)
    reorder_level = Column(Numeric(14, 3), default=0)
    min_stock = Column(Numeric(14, 3), default=0)
    max_stock = Column(Numeric(14, 3), default=0)
    allergens = Column(JSON, default=list)
    nutrition_facts = Column(JSON, default=dict)  # per serving
    ingredients = Column(Text)
    image_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    category = relationship("ProductCategory")


# ======= SUPPLIERS =======
class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(String(36), primary_key=True, default=new_uuid)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255))
    gstin = Column(String(32))
    pan = Column(String(32))
    contact_person = Column(String(128))
    email = Column(String(255))
    phone = Column(String(32))
    address = Column(Text)
    city = Column(String(128))
    state = Column(String(128))
    pincode = Column(String(16))
    payment_terms_days = Column(Integer, default=30)
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ======= CUSTOMERS =======
class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(36), primary_key=True, default=new_uuid)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    customer_type = Column(String(32), default="RETAIL")  # RETAIL, WHOLESALE, DISTRIBUTOR, DIRECT
    gstin = Column(String(32))
    contact_person = Column(String(128))
    email = Column(String(255), index=True)
    phone = Column(String(32))
    billing_address = Column(Text)
    shipping_address = Column(Text)
    city = Column(String(128))
    state = Column(String(128))
    pincode = Column(String(16))
    credit_limit = Column(Numeric(14, 2), default=0)
    payment_terms_days = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ======= INVENTORY =======
class InventoryBatch(Base):
    """A specific batch/lot of a product. All stock operates on batches for FEFO."""
    __tablename__ = "inventory_batches"
    id = Column(String(36), primary_key=True, default=new_uuid)
    batch_number = Column(String(64), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"), nullable=False)
    manufacture_date = Column(Date)
    expiry_date = Column(Date, index=True)
    quantity_on_hand = Column(Numeric(14, 3), default=0)
    quantity_reserved = Column(Numeric(14, 3), default=0)
    cost_per_unit = Column(Numeric(14, 4), default=0)
    status = Column(Enum(BatchStatus), nullable=False, default=BatchStatus.QUARANTINE)
    source_grn_id = Column(String(36))  # link to GRN that created it
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product = relationship("Product")
    warehouse = relationship("Warehouse")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "batch_number", name="uq_batch_unique"),
        Index("ix_batch_product_wh", "product_id", "warehouse_id"),
    )


class StockMovement(Base):
    """Immutable audit ledger of every stock change."""
    __tablename__ = "stock_movements"
    id = Column(String(36), primary_key=True, default=new_uuid)
    batch_id = Column(String(36), ForeignKey("inventory_batches.id"), nullable=False)
    movement_type = Column(Enum(StockMovementType), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)  # signed: + in, - out
    reference_type = Column(String(32))  # PO, SO, GRN, ADJ, etc
    reference_id = Column(String(36))
    reference_number = Column(String(64))
    notes = Column(Text)
    user_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    batch = relationship("InventoryBatch")


# ======= PURCHASE ORDERS =======
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(String(36), primary_key=True, default=new_uuid)
    po_number = Column(String(32), unique=True, nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"), nullable=False)
    order_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    expected_delivery_date = Column(Date)
    status = Column(Enum(PurchaseOrderStatus), nullable=False, default=PurchaseOrderStatus.DRAFT)
    subtotal = Column(Numeric(14, 2), default=0)
    tax_amount = Column(Numeric(14, 2), default=0)
    total = Column(Numeric(14, 2), default=0)
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    approved_by = Column(String(36), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    lines = relationship("PurchaseOrderLine", back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    id = Column(String(36), primary_key=True, default=new_uuid)
    order_id = Column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)
    received_quantity = Column(Numeric(14, 3), default=0)
    unit_price = Column(Numeric(14, 4), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=18)
    line_total = Column(Numeric(14, 2), default=0)

    order = relationship("PurchaseOrder", back_populates="lines")
    product = relationship("Product")


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"
    id = Column(String(36), primary_key=True, default=new_uuid)
    grn_number = Column(String(32), unique=True, nullable=False, index=True)
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id"), nullable=False)
    received_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    purchase_order = relationship("PurchaseOrder")
    lines = relationship("GoodsReceiptLine", back_populates="receipt", cascade="all, delete-orphan")


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"
    id = Column(String(36), primary_key=True, default=new_uuid)
    receipt_id = Column(String(36), ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False)
    po_line_id = Column(String(36), ForeignKey("purchase_order_lines.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(64), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)
    manufacture_date = Column(Date)
    expiry_date = Column(Date)
    unit_cost = Column(Numeric(14, 4), nullable=False)
    batch_id = Column(String(36), ForeignKey("inventory_batches.id"))

    receipt = relationship("GoodsReceipt", back_populates="lines")
    product = relationship("Product")


# ======= SALES ORDERS =======
class SalesOrder(Base):
    __tablename__ = "sales_orders"
    id = Column(String(36), primary_key=True, default=new_uuid)
    so_number = Column(String(32), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"), nullable=False)
    order_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    expected_dispatch_date = Column(Date)
    status = Column(Enum(SalesOrderStatus), nullable=False, default=SalesOrderStatus.DRAFT)
    subtotal = Column(Numeric(14, 2), default=0)
    tax_amount = Column(Numeric(14, 2), default=0)
    discount_amount = Column(Numeric(14, 2), default=0)
    total = Column(Numeric(14, 2), default=0)
    source_channel = Column(String(32), default="DIRECT")  # DIRECT, SHOPIFY, WOOCOMMERCE, META_AD, GOOGLE_AD
    campaign_id = Column(String(36), ForeignKey("ad_campaigns.id"))
    utm_source = Column(String(64))
    utm_medium = Column(String(64))
    utm_campaign = Column(String(128))
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer = relationship("Customer")
    warehouse = relationship("Warehouse")
    lines = relationship("SalesOrderLine", back_populates="order", cascade="all, delete-orphan")


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    id = Column(String(36), primary_key=True, default=new_uuid)
    order_id = Column(String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)
    dispatched_quantity = Column(Numeric(14, 3), default=0)
    unit_price = Column(Numeric(14, 4), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=18)
    discount = Column(Numeric(14, 2), default=0)
    line_total = Column(Numeric(14, 2), default=0)
    allocated_batch_id = Column(String(36), ForeignKey("inventory_batches.id"))

    order = relationship("SalesOrder", back_populates="lines")
    product = relationship("Product")


# ======= ADVERTISING / MARKETING (Phase 1 stub w/ mock data) =======
class AdPlatformConnection(Base):
    __tablename__ = "ad_platform_connections"
    id = Column(String(36), primary_key=True, default=new_uuid)
    platform = Column(String(32), nullable=False)  # META, GOOGLE_ADS, LINKEDIN, TIKTOK, AMAZON
    account_name = Column(String(255), nullable=False)
    account_id = Column(String(128), nullable=False)
    status = Column(String(32), default="CONNECTED")  # CONNECTED, EXPIRED, DISCONNECTED, ERROR
    connected_at = Column(DateTime(timezone=True), default=utcnow)
    last_sync_at = Column(DateTime(timezone=True))
    meta = Column(JSON, default=dict)


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    id = Column(String(36), primary_key=True, default=new_uuid)
    external_id = Column(String(128))
    platform = Column(String(32), nullable=False)
    account_id = Column(String(36), ForeignKey("ad_platform_connections.id"))
    name = Column(String(255), nullable=False)
    objective = Column(String(64))  # CONVERSIONS, TRAFFIC, LEADS, AWARENESS
    status = Column(String(32), default="ACTIVE")  # ACTIVE, PAUSED, ENDED
    product_id = Column(String(36), ForeignKey("products.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    daily_budget = Column(Numeric(14, 2), default=0)
    total_budget = Column(Numeric(14, 2), default=0)
    spend_to_date = Column(Numeric(14, 2), default=0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    conversion_value = Column(Numeric(14, 2), default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product = relationship("Product")


# ======= AUDIT =======
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"))
    user_email = Column(String(255))
    action = Column(String(64), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, APPROVE
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(36))
    details = Column(JSON, default=dict)
    ip_address = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)


# ======= APPROVAL REQUESTS =======
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id = Column(String(36), primary_key=True, default=new_uuid)
    entity_type = Column(String(64), nullable=False)  # PURCHASE_ORDER, SALES_ORDER, CAMPAIGN
    entity_id = Column(String(36), nullable=False)
    requested_by = Column(String(36), ForeignKey("users.id"))
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    notes = Column(Text)
    resolved_by = Column(String(36), ForeignKey("users.id"))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)



# ======= FINANCE / ACCOUNTING =======
class AccountType(str, enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class InvoiceType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"   # AR - we sell to a customer
    SUPPLIER = "SUPPLIER"   # AP - supplier bills us


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentDirection(str, enum.Enum):
    RECEIPT = "RECEIPT"      # Money IN from customer
    PAYMENT = "PAYMENT"      # Money OUT to supplier


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    BANK = "BANK"
    UPI = "UPI"
    CHEQUE = "CHEQUE"
    CARD = "CARD"


class Account(Base):
    """Chart of accounts (single-currency Phase 1)."""
    __tablename__ = "accounts"
    id = Column(String(36), primary_key=True, default=new_uuid)
    code = Column(String(16), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    parent_id = Column(String(36), ForeignKey("accounts.id"))
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class JournalEntry(Base):
    """Posted journal entry. Must be balanced (sum debits == sum credits)."""
    __tablename__ = "journal_entries"
    id = Column(String(36), primary_key=True, default=new_uuid)
    entry_number = Column(String(32), unique=True, nullable=False, index=True)
    entry_date = Column(Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    narration = Column(Text)
    reference_type = Column(String(32))    # INVOICE, PAYMENT, MANUAL, GRN, SO
    reference_id = Column(String(36))
    reference_number = Column(String(64))
    is_reversed = Column(Boolean, default=False)
    reversed_by_entry_id = Column(String(36), ForeignKey("journal_entries.id"))
    posted_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    lines = relationship("JournalEntryLine", back_populates="entry", cascade="all, delete-orphan")


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"
    id = Column(String(36), primary_key=True, default=new_uuid)
    entry_id = Column(String(36), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    debit = Column(Numeric(14, 2), default=0, nullable=False)
    credit = Column(Numeric(14, 2), default=0, nullable=False)
    notes = Column(String(255))
    counterparty_type = Column(String(32))     # CUSTOMER, SUPPLIER (for sub-ledger)
    counterparty_id = Column(String(36))

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account")


class Invoice(Base):
    """Customer invoice (AR) or Supplier bill (AP)."""
    __tablename__ = "invoices"
    id = Column(String(36), primary_key=True, default=new_uuid)
    invoice_number = Column(String(32), unique=True, nullable=False, index=True)
    invoice_type = Column(Enum(InvoiceType), nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)

    # One of these is set
    customer_id = Column(String(36), ForeignKey("customers.id"))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"))

    # Source documents
    sales_order_id = Column(String(36), ForeignKey("sales_orders.id"))
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id"))
    goods_receipt_id = Column(String(36), ForeignKey("goods_receipts.id"))
    supplier_bill_reference = Column(String(64))  # supplier's own invoice number for AP

    invoice_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    due_date = Column(Date)

    subtotal = Column(Numeric(14, 2), default=0)
    tax_amount = Column(Numeric(14, 2), default=0)
    discount_amount = Column(Numeric(14, 2), default=0)
    total = Column(Numeric(14, 2), default=0)
    amount_paid = Column(Numeric(14, 2), default=0)

    cogs_amount = Column(Numeric(14, 2), default=0)   # COGS for customer invoices
    notes = Column(Text)

    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"))
    created_by = Column(String(36), ForeignKey("users.id"))
    posted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer = relationship("Customer")
    supplier = relationship("Supplier")
    sales_order = relationship("SalesOrder")
    purchase_order = relationship("PurchaseOrder")
    goods_receipt = relationship("GoodsReceipt")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(String(36), primary_key=True, default=new_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"))
    description = Column(String(255))
    quantity = Column(Numeric(14, 3), nullable=False, default=1)
    unit_price = Column(Numeric(14, 4), nullable=False, default=0)
    tax_rate = Column(Numeric(5, 2), default=18)
    discount = Column(Numeric(14, 2), default=0)
    line_total = Column(Numeric(14, 2), default=0)

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(36), primary_key=True, default=new_uuid)
    payment_number = Column(String(32), unique=True, nullable=False, index=True)
    direction = Column(Enum(PaymentDirection), nullable=False)
    payment_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())

    customer_id = Column(String(36), ForeignKey("customers.id"))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"))
    invoice_id = Column(String(36), ForeignKey("invoices.id"))

    amount = Column(Numeric(14, 2), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False, default=PaymentMethod.BANK)
    bank_account_id = Column(String(36), ForeignKey("accounts.id"))  # Cash/Bank account
    reference = Column(String(128))   # UTR / cheque # / UPI txn id
    notes = Column(Text)

    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"))
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    customer = relationship("Customer")
    supplier = relationship("Supplier")
    invoice = relationship("Invoice")
    bank_account = relationship("Account")
