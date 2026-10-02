"""Finance / accounting router.

Covers:
- Chart of Accounts (seeded)
- Journal entries (view + manual posting)
- Customer invoices from Sales Orders (AR)
- Supplier bills from Goods Receipts (AP)
- Payments (receipts + disbursements)
- Reports: Trial Balance, AR / AP Aging, Profit & Loss

Posting rules (Phase 1):
  Customer Invoice (from SO):
    Dr Accounts Receivable       total
       Cr Sales Revenue           subtotal
       Cr GST Output              tax
    Plus COGS:
    Dr Cost of Goods Sold        cogs
       Cr Inventory               cogs

  Supplier Bill (from GRN):
    Dr Inventory (or Purchase)   subtotal
    Dr GST Input                 tax
       Cr Accounts Payable       total

  Receipt (customer pays):
    Dr Bank / Cash               amount
       Cr Accounts Receivable    amount

  Payment (we pay supplier):
    Dr Accounts Payable          amount
       Cr Bank / Cash            amount
"""
from __future__ import annotations
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_
from typing import List, Optional
from io import BytesIO

from database import get_db
from models import (
    Account, JournalEntry, JournalEntryLine, Invoice, InvoiceLine, Payment,
    Customer, Supplier, SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine,
    GoodsReceipt, GoodsReceiptLine, InventoryBatch, User, Company,
    AccountType, InvoiceType, InvoiceStatus, PaymentDirection, PaymentMethod,
    SalesOrderStatus,
)
from finance_schemas import (
    AccountCreate, AccountOut, AccountBalance,
    JournalEntryOut, JournalLineOut, ManualJournalCreate, ManualJournalLine,
    InvoiceOut, InvoiceLineOut,
    CreateCustomerInvoiceFromSO, CreateSupplierBillFromGRN,
    PaymentCreate, PaymentOut,
    TrialBalanceReport, TrialBalanceRow,
    AgingReport, AgingRow,
    ProfitLossReport, ProfitLossSection,
)
from auth import require_permission
from helpers import log_audit
from invoice_pdf import generate_invoice_pdf
from email_service import send_email


router = APIRouter(prefix="/api/finance", tags=["finance"])


# ======================= System accounts helper =======================
SYSTEM_ACCOUNTS = {
    "1100": ("Cash in Hand", AccountType.ASSET),
    "1110": ("Bank Account", AccountType.ASSET),
    "1200": ("Accounts Receivable", AccountType.ASSET),
    "1300": ("Inventory", AccountType.ASSET),
    "1400": ("GST Input", AccountType.ASSET),
    "2100": ("Accounts Payable", AccountType.LIABILITY),
    "2200": ("GST Output", AccountType.LIABILITY),
    "3100": ("Owner Equity", AccountType.EQUITY),
    "3200": ("Retained Earnings", AccountType.EQUITY),
    "4100": ("Sales Revenue", AccountType.INCOME),
    "4200": ("Other Income", AccountType.INCOME),
    "5100": ("Cost of Goods Sold", AccountType.EXPENSE),
    "5200": ("Purchases", AccountType.EXPENSE),
    "6100": ("Operating Expenses", AccountType.EXPENSE),
    "6200": ("Marketing & Advertising", AccountType.EXPENSE),
    "6300": ("Salaries & Wages", AccountType.EXPENSE),
    "6400": ("Freight & Shipping", AccountType.EXPENSE),
}


def ensure_system_accounts(db: Session):
    """Ensure the system chart of accounts exists. Idempotent."""
    for code, (name, atype) in SYSTEM_ACCOUNTS.items():
        if not db.query(Account).filter(Account.code == code).first():
            db.add(Account(code=code, name=name, account_type=atype, is_system=True))
    db.flush()


def _acct(db: Session, code: str) -> Account:
    a = db.query(Account).filter(Account.code == code).first()
    if not a:
        ensure_system_accounts(db)
        a = db.query(Account).filter(Account.code == code).first()
    return a


def _next_entry_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(JournalEntry).count()
    return f"JE-{year}-{(count + 1):06d}"


def _next_invoice_number(db: Session, invoice_type: InvoiceType) -> str:
    year = datetime.now().year
    prefix = "INV" if invoice_type == InvoiceType.CUSTOMER else "BILL"
    count = db.query(Invoice).filter(Invoice.invoice_type == invoice_type).count()
    return f"{prefix}-{year}-{(count + 1):05d}"


def _next_payment_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(Payment).count()
    return f"PAY-{year}-{(count + 1):05d}"


def _post_journal(
    db: Session, narration: str,
    lines: List[dict],
    reference_type: str, reference_id: str, reference_number: str,
    user: User, entry_date: date | None = None,
) -> JournalEntry:
    """Create a balanced journal entry. lines=[{account_id, debit, credit, notes, counterparty_type?, counterparty_id?}]"""
    total_dr = sum(Decimal(l.get("debit") or 0) for l in lines)
    total_cr = sum(Decimal(l.get("credit") or 0) for l in lines)
    if total_dr <= 0 and total_cr <= 0:
        raise HTTPException(400, "Journal entry has no amounts")
    if abs(total_dr - total_cr) > Decimal("0.01"):
        raise HTTPException(400, f"Entry out of balance: Dr {total_dr} vs Cr {total_cr}")

    entry = JournalEntry(
        entry_number=_next_entry_number(db),
        entry_date=entry_date or date.today(),
        narration=narration,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        posted_by=user.id,
    )
    db.add(entry)
    db.flush()
    for l in lines:
        db.add(JournalEntryLine(
            entry_id=entry.id, account_id=l["account_id"],
            debit=Decimal(l.get("debit") or 0),
            credit=Decimal(l.get("credit") or 0),
            notes=l.get("notes"),
            counterparty_type=l.get("counterparty_type"),
            counterparty_id=l.get("counterparty_id"),
        ))
    return entry


# ======================= Accounts =======================
@router.get("/accounts", response_model=List[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    ensure_system_accounts(db)
    db.commit()
    return db.query(Account).order_by(Account.code).all()


@router.post("/accounts", response_model=AccountOut)
def create_account(
    payload: AccountCreate, db: Session = Depends(get_db),
    current: User = Depends(require_permission("finance:write")),
):
    if db.query(Account).filter(Account.code == payload.code).first():
        raise HTTPException(400, "Account code already exists")
    a = Account(
        code=payload.code, name=payload.name,
        account_type=AccountType(payload.account_type),
        parent_id=payload.parent_id, description=payload.description,
    )
    db.add(a)
    log_audit(db, current, "CREATE", "Account", a.id, {"code": payload.code})
    db.commit()
    db.refresh(a)
    return a


@router.get("/accounts/balances", response_model=List[AccountBalance])
def account_balances(
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    ensure_system_accounts(db)
    db.commit()
    as_of = as_of or date.today()
    rows = (
        db.query(
            Account.id, Account.code, Account.name, Account.account_type,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label("debit"),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label("credit"),
        )
        .outerjoin(JournalEntryLine, JournalEntryLine.account_id == Account.id)
        .outerjoin(JournalEntry, (JournalEntry.id == JournalEntryLine.entry_id) & (JournalEntry.entry_date <= as_of) & (JournalEntry.is_reversed == False))
        .group_by(Account.id)
        .order_by(Account.code)
        .all()
    )
    out = []
    for r in rows:
        atype = r.account_type.value if hasattr(r.account_type, "value") else r.account_type
        # Natural balance direction: ASSET/EXPENSE = Debit normal; LIAB/EQUITY/INCOME = Credit normal
        if atype in ("ASSET", "EXPENSE"):
            bal = Decimal(r.debit) - Decimal(r.credit)
        else:
            bal = Decimal(r.credit) - Decimal(r.debit)
        out.append(AccountBalance(
            id=r.id, code=r.code, name=r.name, account_type=atype,
            debit_total=Decimal(r.debit), credit_total=Decimal(r.credit), balance=bal,
        ))
    return out


# ======================= Journal Entries =======================
def _je_out(e: JournalEntry, db: Session) -> JournalEntryOut:
    lines = []
    tot_dr = Decimal(0); tot_cr = Decimal(0)
    for l in e.lines:
        lines.append(JournalLineOut(
            id=l.id, account_id=l.account_id,
            account_code=l.account.code if l.account else None,
            account_name=l.account.name if l.account else None,
            debit=l.debit, credit=l.credit, notes=l.notes,
            counterparty_type=l.counterparty_type, counterparty_id=l.counterparty_id,
        ))
        tot_dr += Decimal(l.debit); tot_cr += Decimal(l.credit)
    poster_email = None
    if e.posted_by:
        u = db.query(User).filter(User.id == e.posted_by).first()
        poster_email = u.email if u else None
    return JournalEntryOut(
        id=e.id, entry_number=e.entry_number, entry_date=e.entry_date,
        narration=e.narration, reference_type=e.reference_type,
        reference_number=e.reference_number, is_reversed=e.is_reversed,
        posted_by_email=poster_email, created_at=e.created_at,
        total_debit=tot_dr, total_credit=tot_cr, lines=lines,
    )


@router.get("/journal-entries", response_model=List[JournalEntryOut])
def list_journal_entries(
    reference_type: Optional[str] = None,
    from_date: Optional[date] = None, to_date: Optional[date] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    q = db.query(JournalEntry).options(selectinload(JournalEntry.lines).selectinload(JournalEntryLine.account))
    if reference_type:
        q = q.filter(JournalEntry.reference_type == reference_type)
    if from_date:
        q = q.filter(JournalEntry.entry_date >= from_date)
    if to_date:
        q = q.filter(JournalEntry.entry_date <= to_date)
    entries = q.order_by(JournalEntry.created_at.desc()).limit(min(limit, 500)).all()
    return [_je_out(e, db) for e in entries]


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryOut)
def get_journal_entry(entry_id: str, db: Session = Depends(get_db),
                     _: User = Depends(require_permission("finance:read"))):
    e = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not e:
        raise HTTPException(404, "Entry not found")
    return _je_out(e, db)


@router.post("/journal-entries", response_model=JournalEntryOut)
def post_manual_journal(
    payload: ManualJournalCreate, db: Session = Depends(get_db),
    current: User = Depends(require_permission("finance:write")),
):
    if not payload.lines or len(payload.lines) < 2:
        raise HTTPException(400, "A journal entry needs at least 2 lines")
    entry = _post_journal(
        db, payload.narration,
        [{"account_id": l.account_id, "debit": l.debit, "credit": l.credit, "notes": l.notes} for l in payload.lines],
        reference_type="MANUAL", reference_id=None, reference_number=None,
        user=current, entry_date=payload.entry_date,
    )
    log_audit(db, current, "CREATE", "JournalEntry", entry.id, {"entry_number": entry.entry_number})
    db.commit()
    db.refresh(entry)
    return _je_out(entry, db)


# ======================= Invoices =======================
def _invoice_out(inv: Invoice) -> InvoiceOut:
    lines = [
        InvoiceLineOut(
            id=l.id, product_id=l.product_id,
            product_sku=l.product.sku if l.product else None,
            product_name=l.product.name if l.product else None,
            description=l.description,
            quantity=l.quantity, unit_price=l.unit_price,
            tax_rate=l.tax_rate, discount=l.discount, line_total=l.line_total,
        ) for l in inv.lines
    ]
    return InvoiceOut(
        id=inv.id, invoice_number=inv.invoice_number,
        invoice_type=inv.invoice_type.value if hasattr(inv.invoice_type, "value") else inv.invoice_type,
        status=inv.status.value if hasattr(inv.status, "value") else inv.status,
        customer_id=inv.customer_id,
        customer_name=inv.customer.name if inv.customer else None,
        supplier_id=inv.supplier_id,
        supplier_name=inv.supplier.name if inv.supplier else None,
        sales_order_id=inv.sales_order_id,
        sales_order_number=inv.sales_order.so_number if inv.sales_order else None,
        purchase_order_id=inv.purchase_order_id,
        purchase_order_number=inv.purchase_order.po_number if inv.purchase_order else None,
        goods_receipt_id=inv.goods_receipt_id,
        grn_number=inv.goods_receipt.grn_number if inv.goods_receipt else None,
        supplier_bill_reference=inv.supplier_bill_reference,
        invoice_date=inv.invoice_date, due_date=inv.due_date,
        subtotal=inv.subtotal, tax_amount=inv.tax_amount,
        discount_amount=inv.discount_amount, total=inv.total,
        amount_paid=inv.amount_paid,
        amount_due=Decimal(inv.total) - Decimal(inv.amount_paid),
        cogs_amount=inv.cogs_amount,
        notes=inv.notes, journal_entry_id=inv.journal_entry_id,
        posted_at=inv.posted_at, created_at=inv.created_at, lines=lines,
    )


@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    invoice_type: Optional[str] = None,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    q = db.query(Invoice).options(selectinload(Invoice.lines).selectinload(InvoiceLine.product))
    if invoice_type:
        q = q.filter(Invoice.invoice_type == invoice_type)
    if status:
        q = q.filter(Invoice.status == status)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    if supplier_id:
        q = q.filter(Invoice.supplier_id == supplier_id)
    invoices = q.order_by(Invoice.created_at.desc()).all()
    return [_invoice_out(i) for i in invoices]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, db: Session = Depends(get_db),
                _: User = Depends(require_permission("finance:read"))):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return _invoice_out(inv)


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: str, db: Session = Depends(get_db),
                         _: User = Depends(require_permission("finance:read"))):
    inv = db.query(Invoice).options(
        selectinload(Invoice.lines).selectinload(InvoiceLine.product),
    ).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    company = db.query(Company).first()
    pdf_bytes = generate_invoice_pdf(inv, company)
    headers = {
        "Content-Disposition": f'inline; filename="{inv.invoice_number}.pdf"',
        "Cache-Control": "no-store",
    }
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.post("/invoices/{invoice_id}/email")
async def email_invoice(
    invoice_id: str, db: Session = Depends(get_db),
    current: User = Depends(require_permission("finance:write")),
):
    """Email the invoice PDF to the counterparty. Templates and recipients are
    strictly derived from server-side records - caller only supplies the ID (G4)."""
    inv = db.query(Invoice).options(
        selectinload(Invoice.lines).selectinload(InvoiceLine.product),
    ).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == InvoiceStatus.CANCELLED:
        raise HTTPException(400, "Cannot email a cancelled invoice")

    # Only customer invoices are emailable (supplier bills go to us, not to them)
    if inv.invoice_type != InvoiceType.CUSTOMER:
        raise HTTPException(400, "Only customer invoices can be emailed")

    customer = inv.customer
    if not customer or not customer.email:
        raise HTTPException(400, "Customer has no email on file")

    company = db.query(Company).first()
    pdf_bytes = generate_invoice_pdf(inv, company)

    subject = f"Invoice {inv.invoice_number} from {company.name}"
    contact_name = customer.contact_person or customer.name
    amount_due = Decimal(inv.total) - Decimal(inv.amount_paid)
    due_date = inv.due_date.strftime("%d %b %Y") if inv.due_date else "the due date on the invoice"
    html = (
        '<table role="presentation" width="100%" style="font-family:Arial,sans-serif;color:#0f172a">'
        '<tr><td style="padding:24px">'
        f'<p>Dear {_html_escape(contact_name)},</p>'
        f'<p>Please find attached invoice <strong>{_html_escape(inv.invoice_number)}</strong> '
        f'for the amount of <strong>INR {amount_due:,.2f}</strong>, due by <strong>{due_date}</strong>.</p>'
        '<p>Payment details are on the invoice. If you have any questions about this invoice, '
        'please reply to this email and our team will get back to you.</p>'
        f'<p>Thank you for your business.</p>'
        f'<p style="margin-top:24px">Regards,<br/><strong>{_html_escape(company.name)}</strong></p>'
        f'<hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0"/>'
        f'<p style="font-size:12px;color:#64748b">Sent by {_html_escape(company.name)} via GreenPeak Nutrition ERP. '
        'We never ask for your password or card details by email.</p>'
        '</td></tr></table>'
    )

    try:
        reply_to = company.finance_email or None
        email_id = await send_email(
            to=customer.email, subject=subject, html=html,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"{inv.invoice_number}.pdf",
            reply_to=reply_to,
        )
    except Exception as e:
        raise HTTPException(502, f"Failed to send email: {str(e)[:200]}")

    log_audit(db, current, "EMAIL", "Invoice", inv.id, {
        "invoice_number": inv.invoice_number, "to": customer.email, "email_id": email_id,
    })
    db.commit()
    return {"status": "sent", "to": customer.email, "email_id": email_id,
            "invoice_number": inv.invoice_number}


def _html_escape(s: str) -> str:
    from html import escape
    return escape(s or "")


# ----- Customer invoice from Sales Order -----
@router.post("/invoices/from-sales-order", response_model=InvoiceOut)
def create_invoice_from_so(
    payload: CreateCustomerInvoiceFromSO,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("finance:write")),
):
    so = db.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).first()
    if not so:
        raise HTTPException(404, "Sales order not found")
    if so.status != SalesOrderStatus.DISPATCHED:
        raise HTTPException(400, f"SO {so.so_number} must be DISPATCHED to invoice (current: {so.status.value})")
    if db.query(Invoice).filter(Invoice.sales_order_id == so.id, Invoice.status != InvoiceStatus.CANCELLED).first():
        raise HTTPException(400, "Invoice for this sales order already exists")

    ensure_system_accounts(db)
    inv_date = payload.invoice_date or date.today()
    customer = so.customer
    due = payload.due_date or (inv_date + timedelta(days=int(customer.payment_terms_days or 0) or 30))

    inv = Invoice(
        invoice_number=_next_invoice_number(db, InvoiceType.CUSTOMER),
        invoice_type=InvoiceType.CUSTOMER,
        status=InvoiceStatus.DRAFT,
        customer_id=customer.id,
        sales_order_id=so.id,
        invoice_date=inv_date, due_date=due,
        subtotal=so.subtotal, tax_amount=so.tax_amount,
        discount_amount=so.discount_amount, total=so.total,
        notes=payload.notes, created_by=current.id,
    )
    db.add(inv)
    db.flush()

    cogs_total = Decimal(0)
    for sol in so.lines:
        line_sub = Decimal(sol.quantity) * Decimal(sol.unit_price) - Decimal(sol.discount)
        line_tax = line_sub * Decimal(sol.tax_rate) / Decimal(100)
        db.add(InvoiceLine(
            invoice_id=inv.id, product_id=sol.product_id,
            description=sol.product.name if sol.product else None,
            quantity=sol.quantity, unit_price=sol.unit_price,
            tax_rate=sol.tax_rate, discount=sol.discount,
            line_total=line_sub + line_tax,
        ))
        # COGS from allocated batch cost
        if sol.allocated_batch_id:
            batch = db.query(InventoryBatch).filter(InventoryBatch.id == sol.allocated_batch_id).first()
            if batch:
                cogs_total += Decimal(batch.cost_per_unit) * Decimal(sol.quantity)
    inv.cogs_amount = cogs_total

    # Post the journal
    narration = f"Customer invoice {inv.invoice_number} for {customer.name} (SO {so.so_number})"
    ar = _acct(db, "1200")
    sales = _acct(db, "4100")
    gst_out = _acct(db, "2200")
    cogs = _acct(db, "5100")
    inv_acct = _acct(db, "1300")

    lines = [
        {"account_id": ar.id, "debit": inv.total, "credit": 0,
         "counterparty_type": "CUSTOMER", "counterparty_id": customer.id,
         "notes": inv.invoice_number},
        {"account_id": sales.id, "debit": 0, "credit": inv.subtotal - inv.discount_amount,
         "notes": inv.invoice_number},
    ]
    if Decimal(inv.tax_amount) > 0:
        lines.append({"account_id": gst_out.id, "debit": 0, "credit": inv.tax_amount,
                      "notes": inv.invoice_number})
    if cogs_total > 0:
        lines.append({"account_id": cogs.id, "debit": cogs_total, "credit": 0,
                      "notes": f"COGS for {inv.invoice_number}"})
        lines.append({"account_id": inv_acct.id, "debit": 0, "credit": cogs_total,
                      "notes": f"COGS for {inv.invoice_number}"})
    entry = _post_journal(
        db, narration, lines,
        reference_type="INVOICE", reference_id=inv.id, reference_number=inv.invoice_number,
        user=current, entry_date=inv_date,
    )
    inv.journal_entry_id = entry.id
    inv.status = InvoiceStatus.POSTED
    inv.posted_at = datetime.now(timezone.utc)
    so.status = SalesOrderStatus.INVOICED

    log_audit(db, current, "CREATE", "Invoice", inv.id, {
        "invoice_number": inv.invoice_number, "so": so.so_number,
        "total": str(inv.total), "cogs": str(cogs_total),
    })
    db.commit()
    db.refresh(inv)
    return _invoice_out(inv)


# ----- Supplier bill from Goods Receipt -----
@router.post("/invoices/from-grn", response_model=InvoiceOut)
def create_bill_from_grn(
    payload: CreateSupplierBillFromGRN,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("finance:write")),
):
    grn = db.query(GoodsReceipt).filter(GoodsReceipt.id == payload.goods_receipt_id).first()
    if not grn:
        raise HTTPException(404, "GRN not found")
    if db.query(Invoice).filter(Invoice.goods_receipt_id == grn.id,
                                 Invoice.status != InvoiceStatus.CANCELLED).first():
        raise HTTPException(400, "Bill for this GRN already exists")

    ensure_system_accounts(db)
    po = grn.purchase_order
    supplier = po.supplier

    # Compute totals from GRN lines using unit_cost
    subtotal = Decimal(0); tax_amount = Decimal(0)
    for gl in grn.lines:
        line_sub = Decimal(gl.quantity) * Decimal(gl.unit_cost)
        # Use PO line tax rate
        pol = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.id == gl.po_line_id).first()
        rate = Decimal(pol.tax_rate) if pol else Decimal(18)
        subtotal += line_sub
        tax_amount += line_sub * rate / Decimal(100)
    total = subtotal + tax_amount

    inv_date = payload.invoice_date or date.today()
    due = payload.due_date or (inv_date + timedelta(days=int(supplier.payment_terms_days or 30)))

    inv = Invoice(
        invoice_number=_next_invoice_number(db, InvoiceType.SUPPLIER),
        invoice_type=InvoiceType.SUPPLIER,
        status=InvoiceStatus.DRAFT,
        supplier_id=supplier.id,
        purchase_order_id=po.id,
        goods_receipt_id=grn.id,
        supplier_bill_reference=payload.supplier_bill_reference,
        invoice_date=inv_date, due_date=due,
        subtotal=subtotal, tax_amount=tax_amount, total=total,
        notes=payload.notes, created_by=current.id,
    )
    db.add(inv)
    db.flush()

    for gl in grn.lines:
        line_sub = Decimal(gl.quantity) * Decimal(gl.unit_cost)
        pol = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.id == gl.po_line_id).first()
        rate = Decimal(pol.tax_rate) if pol else Decimal(18)
        line_tax = line_sub * rate / Decimal(100)
        db.add(InvoiceLine(
            invoice_id=inv.id, product_id=gl.product_id,
            description=gl.product.name if gl.product else None,
            quantity=gl.quantity, unit_price=gl.unit_cost,
            tax_rate=rate, line_total=line_sub + line_tax,
        ))

    narration = f"Supplier bill {inv.invoice_number} from {supplier.name} (GRN {grn.grn_number})"
    inv_acct = _acct(db, "1300")   # Inventory
    gst_in = _acct(db, "1400")
    ap = _acct(db, "2100")

    lines = [
        {"account_id": inv_acct.id, "debit": subtotal, "credit": 0,
         "notes": inv.invoice_number},
    ]
    if tax_amount > 0:
        lines.append({"account_id": gst_in.id, "debit": tax_amount, "credit": 0,
                      "notes": inv.invoice_number})
    lines.append({"account_id": ap.id, "debit": 0, "credit": total,
                  "counterparty_type": "SUPPLIER", "counterparty_id": supplier.id,
                  "notes": inv.invoice_number})

    entry = _post_journal(db, narration, lines,
                          reference_type="INVOICE", reference_id=inv.id,
                          reference_number=inv.invoice_number,
                          user=current, entry_date=inv_date)
    inv.journal_entry_id = entry.id
    inv.status = InvoiceStatus.POSTED
    inv.posted_at = datetime.now(timezone.utc)

    log_audit(db, current, "CREATE", "Invoice", inv.id, {
        "invoice_number": inv.invoice_number, "grn": grn.grn_number,
        "total": str(total),
    })
    db.commit()
    db.refresh(inv)
    return _invoice_out(inv)


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(invoice_id: str, db: Session = Depends(get_db),
                   current: User = Depends(require_permission("finance:write"))):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == InvoiceStatus.CANCELLED:
        raise HTTPException(400, "Already cancelled")
    if Decimal(inv.amount_paid) > 0:
        raise HTTPException(400, "Cannot cancel an invoice with payments; please reverse payments first")

    # Reverse the journal entry
    if inv.journal_entry_id:
        orig = db.query(JournalEntry).filter(JournalEntry.id == inv.journal_entry_id).first()
        if orig and not orig.is_reversed:
            reverse_lines = [{"account_id": l.account_id, "debit": l.credit, "credit": l.debit,
                              "notes": f"Reversal of {orig.entry_number}",
                              "counterparty_type": l.counterparty_type,
                              "counterparty_id": l.counterparty_id} for l in orig.lines]
            rev = _post_journal(db, f"Reversal of {orig.entry_number} - invoice cancelled",
                                reverse_lines, reference_type="REVERSAL",
                                reference_id=orig.id, reference_number=orig.entry_number,
                                user=current)
            orig.is_reversed = True
            orig.reversed_by_entry_id = rev.id

    inv.status = InvoiceStatus.CANCELLED
    log_audit(db, current, "UPDATE", "Invoice", inv.id, {"action": "cancel"})
    db.commit()
    db.refresh(inv)
    return _invoice_out(inv)


# ======================= Payments =======================
def _payment_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id, payment_number=p.payment_number,
        direction=p.direction.value if hasattr(p.direction, "value") else p.direction,
        payment_date=p.payment_date,
        customer_id=p.customer_id, customer_name=p.customer.name if p.customer else None,
        supplier_id=p.supplier_id, supplier_name=p.supplier.name if p.supplier else None,
        invoice_id=p.invoice_id, invoice_number=p.invoice.invoice_number if p.invoice else None,
        amount=p.amount,
        method=p.method.value if hasattr(p.method, "value") else p.method,
        bank_account_name=p.bank_account.name if p.bank_account else None,
        reference=p.reference, notes=p.notes,
        journal_entry_id=p.journal_entry_id, created_at=p.created_at,
    )


@router.get("/payments", response_model=List[PaymentOut])
def list_payments(
    direction: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    q = db.query(Payment)
    if direction:
        q = q.filter(Payment.direction == direction)
    return [_payment_out(p) for p in q.order_by(Payment.created_at.desc()).limit(500).all()]


@router.post("/payments", response_model=PaymentOut)
def create_payment(
    payload: PaymentCreate, db: Session = Depends(get_db),
    current: User = Depends(require_permission("finance:write")),
):
    ensure_system_accounts(db)
    direction = PaymentDirection(payload.direction)
    amount = Decimal(payload.amount)
    if amount <= 0:
        raise HTTPException(400, "Amount must be > 0")

    invoice: Invoice | None = None
    if payload.invoice_id:
        invoice = db.query(Invoice).filter(Invoice.id == payload.invoice_id).first()
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        if invoice.status == InvoiceStatus.CANCELLED:
            raise HTTPException(400, "Cannot pay a cancelled invoice")
        due = Decimal(invoice.total) - Decimal(invoice.amount_paid)
        if amount - due > Decimal("0.01"):
            raise HTTPException(400, f"Payment {amount} exceeds outstanding {due}")
        # Infer direction + counterparty from invoice if not given
        if invoice.invoice_type == InvoiceType.CUSTOMER:
            direction = PaymentDirection.RECEIPT
            payload.customer_id = invoice.customer_id
        else:
            direction = PaymentDirection.PAYMENT
            payload.supplier_id = invoice.supplier_id

    if direction == PaymentDirection.RECEIPT and not payload.customer_id:
        raise HTTPException(400, "customer_id required for a RECEIPT")
    if direction == PaymentDirection.PAYMENT and not payload.supplier_id:
        raise HTTPException(400, "supplier_id required for a PAYMENT")

    # Resolve bank account
    bank_acct = None
    if payload.bank_account_id:
        bank_acct = db.query(Account).filter(Account.id == payload.bank_account_id).first()
    if not bank_acct:
        bank_acct = _acct(db, "1100" if payload.method == "CASH" else "1110")

    pay = Payment(
        payment_number=_next_payment_number(db),
        direction=direction,
        payment_date=payload.payment_date or date.today(),
        customer_id=payload.customer_id, supplier_id=payload.supplier_id,
        invoice_id=invoice.id if invoice else None,
        amount=amount,
        method=PaymentMethod(payload.method),
        bank_account_id=bank_acct.id,
        reference=payload.reference, notes=payload.notes,
        created_by=current.id,
    )
    db.add(pay)
    db.flush()

    # Journal entry
    ar = _acct(db, "1200"); ap = _acct(db, "2100")
    if direction == PaymentDirection.RECEIPT:
        narration = f"Receipt {pay.payment_number} from customer"
        lines = [
            {"account_id": bank_acct.id, "debit": amount, "credit": 0, "notes": pay.payment_number},
            {"account_id": ar.id, "debit": 0, "credit": amount,
             "counterparty_type": "CUSTOMER", "counterparty_id": payload.customer_id,
             "notes": pay.payment_number},
        ]
    else:
        narration = f"Payment {pay.payment_number} to supplier"
        lines = [
            {"account_id": ap.id, "debit": amount, "credit": 0,
             "counterparty_type": "SUPPLIER", "counterparty_id": payload.supplier_id,
             "notes": pay.payment_number},
            {"account_id": bank_acct.id, "debit": 0, "credit": amount, "notes": pay.payment_number},
        ]

    entry = _post_journal(db, narration, lines,
                          reference_type="PAYMENT", reference_id=pay.id,
                          reference_number=pay.payment_number,
                          user=current, entry_date=pay.payment_date)
    pay.journal_entry_id = entry.id

    # Update invoice if linked
    if invoice:
        invoice.amount_paid = Decimal(invoice.amount_paid) + amount
        if Decimal(invoice.amount_paid) >= Decimal(invoice.total) - Decimal("0.01"):
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

    log_audit(db, current, "CREATE", "Payment", pay.id,
              {"payment_number": pay.payment_number, "amount": str(amount), "direction": direction.value})
    db.commit()
    db.refresh(pay)
    return _payment_out(pay)


# ======================= Reports =======================
@router.get("/reports/trial-balance", response_model=TrialBalanceReport)
def trial_balance(
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    ensure_system_accounts(db)
    db.commit()
    as_of = as_of or date.today()
    rows = (
        db.query(
            Account.code, Account.name, Account.account_type,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label("debit"),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label("credit"),
        )
        .outerjoin(JournalEntryLine, JournalEntryLine.account_id == Account.id)
        .outerjoin(JournalEntry, (JournalEntry.id == JournalEntryLine.entry_id) & (JournalEntry.entry_date <= as_of) & (JournalEntry.is_reversed == False))
        .group_by(Account.id)
        .order_by(Account.code)
        .all()
    )
    tb_rows = []
    tot_dr = Decimal(0); tot_cr = Decimal(0)
    for r in rows:
        d = Decimal(r.debit); c = Decimal(r.credit)
        if d == 0 and c == 0:
            continue
        atype = r.account_type.value if hasattr(r.account_type, "value") else r.account_type
        net = d - c
        if atype in ("ASSET", "EXPENSE"):
            if net >= 0:
                tb_rows.append(TrialBalanceRow(account_code=r.code, account_name=r.name, account_type=atype, debit=net, credit=Decimal(0)))
                tot_dr += net
            else:
                tb_rows.append(TrialBalanceRow(account_code=r.code, account_name=r.name, account_type=atype, debit=Decimal(0), credit=-net))
                tot_cr += -net
        else:
            net = c - d
            if net >= 0:
                tb_rows.append(TrialBalanceRow(account_code=r.code, account_name=r.name, account_type=atype, debit=Decimal(0), credit=net))
                tot_cr += net
            else:
                tb_rows.append(TrialBalanceRow(account_code=r.code, account_name=r.name, account_type=atype, debit=-net, credit=Decimal(0)))
                tot_dr += -net
    return TrialBalanceReport(
        as_of_date=as_of, rows=tb_rows,
        total_debit=tot_dr, total_credit=tot_cr,
        is_balanced=abs(tot_dr - tot_cr) < Decimal("0.01"),
    )


def _aging(db: Session, invoice_type: InvoiceType, as_of: date) -> AgingReport:
    invoices = db.query(Invoice).filter(
        Invoice.invoice_type == invoice_type,
        Invoice.status.in_([InvoiceStatus.POSTED, InvoiceStatus.PARTIALLY_PAID]),
    ).all()
    agg: dict[str, dict] = {}
    for inv in invoices:
        counterparty = inv.customer if invoice_type == InvoiceType.CUSTOMER else inv.supplier
        if not counterparty:
            continue
        cid = counterparty.id
        cname = counterparty.name
        due = Decimal(inv.total) - Decimal(inv.amount_paid)
        if due <= 0:
            continue
        bucket_days = (as_of - (inv.due_date or inv.invoice_date)).days
        row = agg.setdefault(cid, {"name": cname, "total": Decimal(0),
                                    "current": Decimal(0), "d_1_30": Decimal(0),
                                    "d_31_60": Decimal(0), "d_61_90": Decimal(0),
                                    "d_over_90": Decimal(0)})
        row["total"] += due
        if bucket_days <= 0:
            row["current"] += due
        elif bucket_days <= 30:
            row["d_1_30"] += due
        elif bucket_days <= 60:
            row["d_31_60"] += due
        elif bucket_days <= 90:
            row["d_61_90"] += due
        else:
            row["d_over_90"] += due

    rows: list[AgingRow] = []
    totals = AgingRow(counterparty_id="TOTAL", counterparty_name="Totals", total_outstanding=Decimal(0))
    for cid, r in agg.items():
        rows.append(AgingRow(
            counterparty_id=cid, counterparty_name=r["name"],
            total_outstanding=r["total"], current=r["current"],
            d_1_30=r["d_1_30"], d_31_60=r["d_31_60"],
            d_61_90=r["d_61_90"], d_over_90=r["d_over_90"],
        ))
        totals.total_outstanding += r["total"]
        totals.current += r["current"]
        totals.d_1_30 += r["d_1_30"]
        totals.d_31_60 += r["d_31_60"]
        totals.d_61_90 += r["d_61_90"]
        totals.d_over_90 += r["d_over_90"]
    rows.sort(key=lambda x: x.total_outstanding, reverse=True)
    return AgingReport(as_of_date=as_of, rows=rows, totals=totals)


@router.get("/reports/ar-aging", response_model=AgingReport)
def ar_aging(as_of: Optional[date] = None, db: Session = Depends(get_db),
             _: User = Depends(require_permission("finance:read"))):
    return _aging(db, InvoiceType.CUSTOMER, as_of or date.today())


@router.get("/reports/ap-aging", response_model=AgingReport)
def ap_aging(as_of: Optional[date] = None, db: Session = Depends(get_db),
             _: User = Depends(require_permission("finance:read"))):
    return _aging(db, InvoiceType.SUPPLIER, as_of or date.today())


@router.get("/reports/profit-loss", response_model=ProfitLossReport)
def profit_loss(
    from_date: Optional[date] = None, to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance:read")),
):
    ensure_system_accounts(db); db.commit()
    today = date.today()
    to_date = to_date or today
    from_date = from_date or to_date.replace(day=1)

    def section(atype: AccountType, label: str) -> ProfitLossSection:
        rows = (
            db.query(
                Account.code, Account.name,
                func.coalesce(func.sum(JournalEntryLine.debit), 0).label("debit"),
                func.coalesce(func.sum(JournalEntryLine.credit), 0).label("credit"),
            )
            .outerjoin(JournalEntryLine, JournalEntryLine.account_id == Account.id)
            .outerjoin(JournalEntry, (JournalEntry.id == JournalEntryLine.entry_id)
                       & (JournalEntry.entry_date >= from_date)
                       & (JournalEntry.entry_date <= to_date)
                       & (JournalEntry.is_reversed == False))
            .filter(Account.account_type == atype)
            .group_by(Account.id).order_by(Account.code).all()
        )
        accs = []
        total = Decimal(0)
        for r in rows:
            net = Decimal(r.credit) - Decimal(r.debit) if atype == AccountType.INCOME else Decimal(r.debit) - Decimal(r.credit)
            if net == 0:
                continue
            accs.append({"code": r.code, "name": r.name, "amount": str(net)})
            total += net
        return ProfitLossSection(label=label, accounts=accs, total=total)

    income = section(AccountType.INCOME, "Income")
    expenses = section(AccountType.EXPENSE, "Expenses")
    return ProfitLossReport(
        from_date=from_date, to_date=to_date,
        income=income, expenses=expenses,
        net_profit=income.total - expenses.total,
    )
