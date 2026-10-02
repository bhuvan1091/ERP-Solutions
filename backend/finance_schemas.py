"""Finance / accounting schemas."""
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ======= Accounts =======
class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str   # ASSET/LIABILITY/EQUITY/INCOME/EXPENSE
    parent_id: Optional[str] = None
    description: Optional[str] = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    account_type: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    is_system: bool
    is_active: bool


class AccountBalance(BaseModel):
    id: str
    code: str
    name: str
    account_type: str
    debit_total: Decimal
    credit_total: Decimal
    balance: Decimal   # natural balance for the type


# ======= Journal =======
class JournalLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    account_id: str
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    debit: Decimal
    credit: Decimal
    notes: Optional[str] = None
    counterparty_type: Optional[str] = None
    counterparty_id: Optional[str] = None


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    entry_number: str
    entry_date: date
    narration: Optional[str] = None
    reference_type: Optional[str] = None
    reference_number: Optional[str] = None
    is_reversed: bool
    posted_by_email: Optional[str] = None
    created_at: datetime
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    lines: List[JournalLineOut] = []


class ManualJournalLine(BaseModel):
    account_id: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    notes: Optional[str] = None


class ManualJournalCreate(BaseModel):
    entry_date: Optional[date] = None
    narration: str
    lines: List[ManualJournalLine]


# ======= Invoices =======
class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    description: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    discount: Decimal
    line_total: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    invoice_number: str
    invoice_type: str
    status: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    sales_order_id: Optional[str] = None
    sales_order_number: Optional[str] = None
    purchase_order_id: Optional[str] = None
    purchase_order_number: Optional[str] = None
    goods_receipt_id: Optional[str] = None
    grn_number: Optional[str] = None
    supplier_bill_reference: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    cogs_amount: Decimal
    notes: Optional[str] = None
    journal_entry_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    lines: List[InvoiceLineOut] = []


class CreateCustomerInvoiceFromSO(BaseModel):
    sales_order_id: str
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class CreateSupplierBillFromGRN(BaseModel):
    goods_receipt_id: str
    supplier_bill_reference: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


# ======= Payments =======
class PaymentCreate(BaseModel):
    direction: str   # RECEIPT or PAYMENT
    invoice_id: Optional[str] = None
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    amount: Decimal
    method: str = "BANK"
    bank_account_id: Optional[str] = None  # defaults to system Bank
    payment_date: Optional[date] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    payment_number: str
    direction: str
    payment_date: date
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    amount: Decimal
    method: str
    bank_account_name: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    journal_entry_id: Optional[str] = None
    created_at: datetime


# ======= Reports =======
class AgingBucket(BaseModel):
    label: str
    amount: Decimal
    count: int


class AgingRow(BaseModel):
    counterparty_id: str
    counterparty_name: str
    total_outstanding: Decimal
    current: Decimal = Decimal("0")
    d_1_30: Decimal = Decimal("0")
    d_31_60: Decimal = Decimal("0")
    d_61_90: Decimal = Decimal("0")
    d_over_90: Decimal = Decimal("0")


class AgingReport(BaseModel):
    as_of_date: date
    rows: List[AgingRow]
    totals: AgingRow


class TrialBalanceRow(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    debit: Decimal
    credit: Decimal


class TrialBalanceReport(BaseModel):
    as_of_date: date
    rows: List[TrialBalanceRow]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool


class ProfitLossSection(BaseModel):
    label: str
    accounts: List[dict]
    total: Decimal


class ProfitLossReport(BaseModel):
    from_date: date
    to_date: date
    income: ProfitLossSection
    expenses: ProfitLossSection
    net_profit: Decimal
