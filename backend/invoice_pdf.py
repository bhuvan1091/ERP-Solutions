"""Printable tax-invoice PDF generator (reportlab).

Produces a clean GST-style A4 invoice for both customer invoices and supplier bills.
"""
from __future__ import annotations
from decimal import Decimal
from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image,
)
from reportlab.lib.utils import ImageReader
from num2words import num2words
import base64
from io import BytesIO as _BIO


FOREST = colors.HexColor("#047857")
FOREST_LIGHT = colors.HexColor("#d1fae5")
SLATE_900 = colors.HexColor("#0f172a")
SLATE_600 = colors.HexColor("#475569")
SLATE_400 = colors.HexColor("#94a3b8")
SLATE_200 = colors.HexColor("#e2e8f0")
SLATE_100 = colors.HexColor("#f1f5f9")


def _rupees(v) -> str:
    v = Decimal(v or 0)
    s = f"{v:,.2f}"
    # Convert to Indian number system
    parts = s.split(".")
    integer, dec = parts[0], parts[1]
    neg = integer.startswith("-")
    if neg:
        integer = integer[1:]
    integer = integer.replace(",", "")
    if len(integer) > 3:
        last3 = integer[-3:]
        rest = integer[:-3]
        # Group rest in 2s
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        indian = ",".join(reversed(groups)) + "," + last3
    else:
        indian = integer
    return ("-" if neg else "") + "Rs. " + indian + "." + dec


def _amount_in_words(amount: Decimal) -> str:
    try:
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))
        words = f"{num2words(rupees, lang='en_IN').title()} Rupees"
        if paise:
            words += f" and {num2words(paise, lang='en_IN').title()} Paise"
        return words + " Only"
    except Exception:
        return f"Rs. {amount:,.2f} Only"


def generate_invoice_pdf(invoice, company) -> bytes:
    """Generate a professional A4 tax invoice.

    Args:
      invoice: Invoice ORM object (with .lines, .customer or .supplier, .sales_order etc)
      company: Company ORM object (name, address, gstin, fssai_license, currency)
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=invoice.invoice_number,
    )

    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=SLATE_600)
    small_mono = ParagraphStyle("smallMono", parent=small, fontName="Courier")
    label = ParagraphStyle("label", parent=small, fontSize=7, textColor=SLATE_400, spaceAfter=1,
                           alignment=TA_LEFT, leading=9)
    val = ParagraphStyle("val", parent=small, fontSize=9, textColor=SLATE_900, leading=11)
    val_bold = ParagraphStyle("valBold", parent=val, fontName="Helvetica-Bold")
    title_style = ParagraphStyle("tt", parent=styles["Title"], fontSize=22, textColor=FOREST,
                                 fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=24)
    section_h = ParagraphStyle("secH", parent=small, fontSize=7, textColor=FOREST,
                               fontName="Helvetica-Bold", spaceAfter=4, leading=9)

    flow = []
    is_customer = (invoice.invoice_type.value if hasattr(invoice.invoice_type, "value") else invoice.invoice_type) == "CUSTOMER"

    # ---- HEADER ----
    doc_label = "TAX INVOICE" if is_customer else "PURCHASE BILL"

    # Logo (data URL -> ReportLab Image). Any decode/render error silently skips the logo.
    logo_flow = None
    if getattr(company, "logo_base64", None):
        try:
            s = company.logo_base64
            if "," in s:
                s = s.split(",", 1)[1]
            img_bytes = base64.b64decode(s)
            # Validate via PIL before handing to ReportLab
            from PIL import Image as _PILImage
            with _PILImage.open(_BIO(img_bytes)) as im:
                im.verify()
            logo_flow = Image(_BIO(img_bytes), width=28 * mm, height=28 * mm, kind="proportional")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Could not render company logo: %s", e)
            logo_flow = None

    company_block = [
        Paragraph(f"<font size=14><b>{company.name}</b></font>", val),
        Paragraph(company.address or "", small),
        Paragraph(f"GSTIN: <b>{company.gstin or '—'}</b>", small),
        Paragraph(f"FSSAI: <b>{company.fssai_license or '—'}</b>", small),
    ]
    if logo_flow:
        header_left_tbl = Table([[logo_flow, company_block]], colWidths=[30 * mm, 68 * mm])
    else:
        header_left_tbl = Table([[company_block]], colWidths=[98 * mm])
    header_left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    header_right = [
        Paragraph(doc_label, title_style),
        Spacer(1, 2),
        Paragraph(f"<b>{invoice.invoice_number}</b>", ParagraphStyle("inv", parent=val, alignment=TA_RIGHT, fontSize=11)),
    ]
    header = Table([[header_left_tbl, header_right]], colWidths=[100 * mm, 80 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    flow.append(header)
    flow.append(Spacer(1, 6))

    # Thin forest-green separator
    sep = Table([[""]], colWidths=[180 * mm], rowHeights=[1.5])
    sep.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FOREST)]))
    flow.append(sep)
    flow.append(Spacer(1, 10))

    # ---- META / BILL TO / SHIP TO ----
    party = invoice.customer if is_customer else invoice.supplier
    party_name = party.name if party else "—"
    party_gstin = getattr(party, "gstin", None) if party else None
    bill_addr = ""
    ship_addr = ""
    if is_customer and invoice.customer:
        bill_addr = invoice.customer.billing_address or ""
        ship_addr = invoice.customer.shipping_address or bill_addr
        party_phone = invoice.customer.phone
        party_email = invoice.customer.email
    else:
        bill_addr = invoice.supplier.address if invoice.supplier else ""
        ship_addr = bill_addr
        party_phone = invoice.supplier.phone if invoice.supplier else ""
        party_email = invoice.supplier.email if invoice.supplier else ""

    meta_left_rows = [
        [Paragraph("INVOICE DATE", label), Paragraph(invoice.invoice_date.strftime("%d %b %Y"), val_bold)],
        [Paragraph("DUE DATE", label), Paragraph(invoice.due_date.strftime("%d %b %Y") if invoice.due_date else "—", val_bold)],
    ]
    if is_customer and invoice.sales_order:
        meta_left_rows.append([Paragraph("SALES ORDER", label), Paragraph(invoice.sales_order.so_number, val)])
    if not is_customer:
        if invoice.goods_receipt:
            meta_left_rows.append([Paragraph("GRN", label), Paragraph(invoice.goods_receipt.grn_number, val)])
        if invoice.supplier_bill_reference:
            meta_left_rows.append([Paragraph("SUPPLIER REF", label), Paragraph(invoice.supplier_bill_reference, val)])

    meta_tbl = Table(meta_left_rows, colWidths=[26 * mm, 60 * mm])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    party_block = [
        Paragraph("BILL TO" if is_customer else "SUPPLIER", section_h),
        Paragraph(f"<b>{party_name}</b>", val),
    ]
    if bill_addr:
        party_block.append(Paragraph(bill_addr.replace("\n", "<br/>"), small))
    if party_gstin:
        party_block.append(Paragraph(f"GSTIN: <b>{party_gstin}</b>", small))
    if party_phone:
        party_block.append(Paragraph(f"Phone: {party_phone}", small))
    if party_email:
        party_block.append(Paragraph(f"Email: {party_email}", small))

    ship_block = []
    if is_customer and ship_addr and ship_addr != bill_addr:
        ship_block = [
            Paragraph("SHIP TO", section_h),
            Paragraph(f"<b>{party_name}</b>", val),
            Paragraph(ship_addr.replace("\n", "<br/>"), small),
        ]

    cols = [party_block, ship_block or [Paragraph("", small)], [meta_tbl]]
    bill_section = Table([cols], colWidths=[60 * mm, 50 * mm, 70 * mm])
    bill_section.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow.append(bill_section)
    flow.append(Spacer(1, 14))

    # ---- LINE ITEMS ----
    header_row = [
        Paragraph("#", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_CENTER)),
        Paragraph("ITEM", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8)),
        Paragraph("HSN", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_CENTER)),
        Paragraph("QTY", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
        Paragraph("RATE", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
        Paragraph("DISC", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
        Paragraph("TAX %", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
        Paragraph("AMOUNT", ParagraphStyle("h", parent=small, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
    ]
    rows = [header_row]
    for i, l in enumerate(invoice.lines, start=1):
        prod = l.product
        name_block = [Paragraph(f"<b>{(prod.name if prod else l.description) or ''}</b>", val)]
        if prod and prod.sku:
            name_block.append(Paragraph(prod.sku, small_mono))
        rows.append([
            Paragraph(str(i), ParagraphStyle("c", parent=small, alignment=TA_CENTER)),
            name_block,
            Paragraph(prod.hsn_code if prod and prod.hsn_code else "—", ParagraphStyle("c", parent=small, alignment=TA_CENTER)),
            Paragraph(f"{Decimal(l.quantity):,.2f}", ParagraphStyle("r", parent=small, alignment=TA_RIGHT)),
            Paragraph(_rupees(l.unit_price).replace("Rs. ", ""), ParagraphStyle("r", parent=small, alignment=TA_RIGHT)),
            Paragraph(_rupees(l.discount).replace("Rs. ", "") if Decimal(l.discount) > 0 else "—", ParagraphStyle("r", parent=small, alignment=TA_RIGHT)),
            Paragraph(f"{Decimal(l.tax_rate):.1f}%", ParagraphStyle("r", parent=small, alignment=TA_RIGHT)),
            Paragraph(_rupees(l.line_total).replace("Rs. ", ""), ParagraphStyle("r", parent=val, alignment=TA_RIGHT, fontName="Helvetica-Bold")),
        ])

    items_tbl = Table(rows, colWidths=[8 * mm, 60 * mm, 16 * mm, 16 * mm, 22 * mm, 18 * mm, 14 * mm, 26 * mm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FOREST),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("GRID", (0, 1), (-1, -1), 0.3, SLATE_200),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SLATE_100]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]))
    flow.append(items_tbl)
    flow.append(Spacer(1, 10))

    # ---- TOTALS + AMOUNT IN WORDS ----
    gross = Decimal(invoice.subtotal) - Decimal(invoice.discount_amount)
    cgst = Decimal(invoice.tax_amount) / 2
    sgst = Decimal(invoice.tax_amount) / 2
    totals = Table([
        [Paragraph("Subtotal", small), Paragraph(_rupees(invoice.subtotal), ParagraphStyle("r", parent=val, alignment=TA_RIGHT))],
        [Paragraph("Discount", small), Paragraph("- " + _rupees(invoice.discount_amount), ParagraphStyle("r", parent=val, alignment=TA_RIGHT))],
        [Paragraph("Taxable amount", small), Paragraph(_rupees(gross), ParagraphStyle("r", parent=val, alignment=TA_RIGHT))],
        [Paragraph("CGST", small), Paragraph(_rupees(cgst), ParagraphStyle("r", parent=val, alignment=TA_RIGHT))],
        [Paragraph("SGST", small), Paragraph(_rupees(sgst), ParagraphStyle("r", parent=val, alignment=TA_RIGHT))],
        [Paragraph("<b>Total due</b>", ParagraphStyle("b", parent=val, fontName="Helvetica-Bold", textColor=colors.white)),
         Paragraph(f"<b>{_rupees(invoice.total)}</b>", ParagraphStyle("rr", parent=val, alignment=TA_RIGHT, fontName="Helvetica-Bold", textColor=colors.white, fontSize=11))],
    ], colWidths=[35 * mm, 35 * mm])
    totals.setStyle(TableStyle([
        ("LINEABOVE", (0, 2), (-1, 2), 0.3, SLATE_200),
        ("BACKGROUND", (0, -1), (-1, -1), FOREST),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))

    paid_due_rows = []
    if Decimal(invoice.amount_paid) > 0:
        paid_due_rows = [
            [Paragraph("Already paid", small), Paragraph(_rupees(invoice.amount_paid), ParagraphStyle("r", parent=val, alignment=TA_RIGHT, textColor=colors.HexColor("#047857")))],
            [Paragraph("Balance due", ParagraphStyle("b", parent=val, fontName="Helvetica-Bold")), Paragraph(_rupees(Decimal(invoice.total) - Decimal(invoice.amount_paid)), ParagraphStyle("r", parent=val, alignment=TA_RIGHT, fontName="Helvetica-Bold", textColor=colors.HexColor("#dc2626") if Decimal(invoice.amount_paid) < Decimal(invoice.total) else colors.HexColor("#047857")))],
        ]
    paid_tbl = Table(paid_due_rows, colWidths=[35 * mm, 35 * mm]) if paid_due_rows else Spacer(1, 1)
    if paid_due_rows:
        paid_tbl.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

    words_block = [
        Paragraph("AMOUNT IN WORDS", section_h),
        Paragraph(f"<i>{_amount_in_words(Decimal(invoice.total))}</i>", val),
    ]

    bottom = Table([[words_block, [totals, Spacer(1, 4), paid_tbl]]], colWidths=[100 * mm, 80 * mm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(bottom)
    flow.append(Spacer(1, 20))

    # ---- NOTES & FOOTER ----
    if invoice.notes:
        flow.append(Paragraph("NOTES", section_h))
        flow.append(Paragraph(invoice.notes, small))
        flow.append(Spacer(1, 10))

    # Bank details block for customer invoices with bank_account_number set
    bank_block = []
    if is_customer and getattr(company, "bank_account_number", None):
        bank_rows = [[Paragraph("BANK DETAILS", section_h), ""]]
        if company.bank_account_name:
            bank_rows.append([Paragraph("Account name", small), Paragraph(f"<b>{company.bank_account_name}</b>", small)])
        if company.bank_name:
            bank_rows.append([Paragraph("Bank", small), Paragraph(company.bank_name, small)])
        if company.bank_account_number:
            bank_rows.append([Paragraph("A/C number", small), Paragraph(f"<b>{company.bank_account_number}</b>", small)])
        if company.bank_ifsc:
            bank_rows.append([Paragraph("IFSC", small), Paragraph(f"<b>{company.bank_ifsc}</b>", small)])
        if company.bank_branch:
            bank_rows.append([Paragraph("Branch", small), Paragraph(company.bank_branch, small)])
        if company.upi_id:
            bank_rows.append([Paragraph("UPI", small), Paragraph(f"<b>{company.upi_id}</b>", small)])
        bank_tbl = Table(bank_rows, colWidths=[24 * mm, 60 * mm])
        bank_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 1), (-1, -1), SLATE_100),
            ("BOX", (0, 1), (-1, -1), 0.3, SLATE_200),
            ("LEFTPADDING", (0, 1), (-1, -1), 6),
            ("RIGHTPADDING", (0, 1), (-1, -1), 6),
        ]))
        bank_block = [bank_tbl]

    footer_rows = [[
        [
            Paragraph("TERMS & CONDITIONS", section_h),
            Paragraph(getattr(company, "invoice_notes", None) or "1. Payment due within the stated due date.<br/>2. Goods once sold are not returnable except as per our returns policy.<br/>3. Please quote invoice number on all remittances.<br/>4. Subject to local jurisdiction.", small),
            Spacer(1, 8),
            *bank_block,
        ],
        [
            Paragraph("FOR " + (company.name or "").upper(), section_h),
            Spacer(1, 36),
            Paragraph("<i>Authorised Signatory</i>", small),
        ],
    ]]
    footer = Table(footer_rows, colWidths=[110 * mm, 70 * mm])
    footer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(footer)
    flow.append(Spacer(1, 14))

    flow.append(Paragraph(
        f"This is a computer-generated {doc_label.lower()}. Generated via GreenPeak Nutrition ERP.",
        ParagraphStyle("f", parent=small, fontSize=6.5, textColor=SLATE_400, alignment=TA_CENTER),
    ))

    doc.build(flow)
    return buf.getvalue()
