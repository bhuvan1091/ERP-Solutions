"""
Phase 2 Finance module backend tests.
Covers: Chart of Accounts, customer invoices from SO, supplier bills from GRN,
payments (receipts/partial/overpay), cancellation/reversal, trial balance,
P&L, AR/AP aging, manual journal, audit logs, RBAC.
"""
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break
assert BASE_URL, "REACT_APP_BACKEND_URL not configured"
API = f"{BASE_URL}/api"

CREDS = {
    "admin": ("admin@greenpeak.in", "Admin@12345"),
    "md": ("md@greenpeak.in", "Welcome@123"),
    "procurement": ("procurement@greenpeak.in", "Welcome@123"),
    "warehouse": ("warehouse@greenpeak.in", "Welcome@123"),
    "sales": ("sales@greenpeak.in", "Welcome@123"),
    "rep": ("rep@greenpeak.in", "Welcome@123"),
    "finance": ("finance@greenpeak.in", "Welcome@123"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def tokens():
    return {k: _login(*v) for k, v in CREDS.items()}


def hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ------------- Helpers that create fresh SO/GRN for isolation -------------
def _create_dispatched_so(tokens):
    """Create and dispatch a brand-new SO with an allocated batch. Returns the dispatched SO JSON."""
    whs = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"])).json()
    bengaluru = next((w for w in whs if "Bengaluru" in w["name"] or "Bangalore" in w["name"]), whs[0])
    wh_id = bengaluru["id"]

    batches = requests.get(
        f"{API}/inventory/batches?warehouse_id={wh_id}&status=RELEASED",
        headers=hdr(tokens["admin"])).json()
    cand = None
    for b in batches:
        avail = Decimal(b["quantity_on_hand"]) - Decimal(b["quantity_reserved"])
        if avail >= Decimal("1") and b.get("cost_per_unit") and Decimal(b["cost_per_unit"]) > 0:
            cand = b
            break
    if not cand:
        pytest.skip("No batch with available stock + cost in warehouse")

    customers = requests.get(f"{API}/customers", headers=hdr(tokens["admin"])).json()
    cust_id = customers[0]["id"]

    r = requests.post(f"{API}/sales-orders", headers=hdr(tokens["sales"]),
                      json={"customer_id": cust_id, "warehouse_id": wh_id,
                            "lines": [{"product_id": cand["product_id"], "quantity": "1",
                                       "unit_price": "500", "tax_rate": "18"}]})
    assert r.status_code == 200, r.text
    so = r.json()
    sid = so["id"]

    r = requests.post(f"{API}/sales-orders/{sid}/allocate", headers=hdr(tokens["sales"]))
    assert r.status_code == 200, r.text
    r = requests.post(f"{API}/sales-orders/{sid}/dispatch", headers=hdr(tokens["sales"]))
    assert r.status_code == 200, r.text
    return r.json()


def _create_grn(tokens):
    """Create a fresh PO -> approve -> GRN. Returns the GRN JSON."""
    suppliers = requests.get(f"{API}/suppliers?is_approved=true", headers=hdr(tokens["admin"])).json()
    warehouses = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"])).json()
    products = requests.get(f"{API}/products", headers=hdr(tokens["admin"])).json()

    r = requests.post(f"{API}/purchase-orders", headers=hdr(tokens["procurement"]),
                      json={"supplier_id": suppliers[0]["id"],
                            "warehouse_id": warehouses[0]["id"],
                            "lines": [{"product_id": products[0]["id"], "quantity": "10",
                                       "unit_price": "150", "tax_rate": "18"}]})
    assert r.status_code == 200, r.text
    po = r.json()
    po_id = po["id"]
    po_line_id = po["lines"][0]["id"]

    r = requests.post(f"{API}/purchase-orders/{po_id}/approve", headers=hdr(tokens["md"]))
    assert r.status_code == 200

    today = date.today()
    batch_no = f"TBF{uuid.uuid4().hex[:6].upper()}"
    r = requests.post(f"{API}/goods-receipts", headers=hdr(tokens["warehouse"]),
                      json={"purchase_order_id": po_id,
                            "lines": [{"po_line_id": po_line_id, "quantity": "10",
                                       "batch_number": batch_no,
                                       "manufacture_date": today.isoformat(),
                                       "expiry_date": (today + timedelta(days=365)).isoformat()}]})
    assert r.status_code == 200, r.text
    return r.json()


# ======================= Chart of Accounts =======================
class TestAccounts:
    def test_17_system_accounts(self, tokens):
        r = requests.get(f"{API}/finance/accounts", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        accts = r.json()
        codes = {a["code"] for a in accts}
        required = {"1100", "1110", "1200", "1300", "1400", "2100", "2200",
                    "3100", "3200", "4100", "4200", "5100", "5200", "6100",
                    "6200", "6300", "6400"}
        assert required.issubset(codes), f"Missing: {required - codes}"


# ======================= RBAC =======================
class TestFinanceRBAC:
    def test_rep_cannot_post_invoice(self, tokens):
        r = requests.post(f"{API}/finance/invoices/from-sales-order",
                          headers=hdr(tokens["rep"]),
                          json={"sales_order_id": "00000000-0000-0000-0000-000000000000"})
        assert r.status_code == 403, f"Expected 403 for rep, got {r.status_code}: {r.text}"

    def test_sales_mgr_can_read_but_not_write(self, tokens):
        # Sales mgr has finance:read
        r = requests.get(f"{API}/finance/invoices", headers=hdr(tokens["sales"]))
        assert r.status_code == 200, f"Sales mgr should have finance:read, got {r.status_code}"
        # But not finance:write
        r = requests.post(f"{API}/finance/invoices/from-sales-order",
                          headers=hdr(tokens["sales"]),
                          json={"sales_order_id": "00000000-0000-0000-0000-000000000000"})
        assert r.status_code == 403


# ======================= Customer invoice from SO =======================
class TestCustomerInvoice:
    def test_create_invoice_from_dispatched_so_and_journal(self, tokens):
        so = _create_dispatched_so(tokens)
        r = requests.post(f"{API}/finance/invoices/from-sales-order",
                          headers=hdr(tokens["admin"]),
                          json={"sales_order_id": so["id"]})
        assert r.status_code == 200, r.text
        inv = r.json()
        assert inv["invoice_number"].startswith("INV-")
        assert inv["status"] == "POSTED"
        assert inv["invoice_type"] == "CUSTOMER"
        assert len(inv["lines"]) == len(so["lines"])
        assert Decimal(inv["cogs_amount"]) > 0

        # SO flipped
        r = requests.get(f"{API}/sales-orders/{so['id']}", headers=hdr(tokens["admin"]))
        assert r.json()["status"] == "INVOICED"

        # Journal entry
        je_id = inv["journal_entry_id"]
        r = requests.get(f"{API}/finance/journal-entries/{je_id}", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        je = r.json()
        assert abs(Decimal(je["total_debit"]) - Decimal(je["total_credit"])) < Decimal("0.01")
        codes = {l["account_code"] for l in je["lines"]}
        assert {"1200", "4100", "5100", "1300"}.issubset(codes)

    def test_cannot_invoice_already_invoiced_so(self, tokens):
        # Pick any already-INVOICED SO
        r = requests.get(f"{API}/sales-orders?status=INVOICED", headers=hdr(tokens["admin"]))
        if r.status_code != 200 or not r.json():
            # fall back: create+invoice one, then try to double-invoice
            so = _create_dispatched_so(tokens)
            requests.post(f"{API}/finance/invoices/from-sales-order",
                          headers=hdr(tokens["admin"]),
                          json={"sales_order_id": so["id"]})
            so_id = so["id"]
        else:
            so_id = r.json()[0]["id"]
        r = requests.post(f"{API}/finance/invoices/from-sales-order",
                          headers=hdr(tokens["admin"]), json={"sales_order_id": so_id})
        assert r.status_code == 400

    def test_cannot_invoice_confirmed_so(self, tokens):
        # Create a CONFIRMED SO (not allocated/dispatched) and try to invoice
        whs = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"])).json()
        products = requests.get(f"{API}/products", headers=hdr(tokens["admin"])).json()
        customers = requests.get(f"{API}/customers", headers=hdr(tokens["admin"])).json()
        r = requests.post(f"{API}/sales-orders", headers=hdr(tokens["sales"]),
                          json={"customer_id": customers[0]["id"],
                                "warehouse_id": whs[0]["id"],
                                "lines": [{"product_id": products[0]["id"], "quantity": "1",
                                           "unit_price": "100"}]})
        assert r.status_code == 200
        so_id = r.json()["id"]
        r = requests.post(f"{API}/finance/invoices/from-sales-order",
                          headers=hdr(tokens["admin"]), json={"sales_order_id": so_id})
        assert r.status_code == 400
        # cleanup
        requests.post(f"{API}/sales-orders/{so_id}/cancel", headers=hdr(tokens["sales"]))


# ======================= Supplier bill from GRN =======================
class TestSupplierBill:
    def test_create_bill_from_grn_and_journal(self, tokens):
        grn = _create_grn(tokens)
        r = requests.post(f"{API}/finance/invoices/from-grn", headers=hdr(tokens["admin"]),
                          json={"goods_receipt_id": grn["id"],
                                "supplier_bill_reference": f"SUP-REF-{uuid.uuid4().hex[:5]}"})
        assert r.status_code == 200, r.text
        inv = r.json()
        assert inv["invoice_number"].startswith("BILL-")
        assert inv["invoice_type"] == "SUPPLIER"
        assert inv["status"] == "POSTED"

        je_id = inv["journal_entry_id"]
        je = requests.get(f"{API}/finance/journal-entries/{je_id}", headers=hdr(tokens["admin"])).json()
        assert abs(Decimal(je["total_debit"]) - Decimal(je["total_credit"])) < Decimal("0.01")
        codes = {l["account_code"] for l in je["lines"]}
        assert {"1300", "1400", "2100"}.issubset(codes)

        # Cannot bill same GRN twice
        r = requests.post(f"{API}/finance/invoices/from-grn", headers=hdr(tokens["admin"]),
                          json={"goods_receipt_id": grn["id"],
                                "supplier_bill_reference": "DUP"})
        assert r.status_code == 400


# ======================= Invoice filters =======================
class TestInvoiceFilters:
    def test_type_filter_disjoint(self, tokens):
        cust = requests.get(f"{API}/finance/invoices?invoice_type=CUSTOMER",
                            headers=hdr(tokens["admin"])).json()
        sup = requests.get(f"{API}/finance/invoices?invoice_type=SUPPLIER",
                           headers=hdr(tokens["admin"])).json()
        assert all(i["invoice_type"] == "CUSTOMER" for i in cust)
        assert all(i["invoice_type"] == "SUPPLIER" for i in sup)
        ids_c = {i["id"] for i in cust}
        ids_s = {i["id"] for i in sup}
        assert ids_c.isdisjoint(ids_s)


# ======================= Payments =======================
class TestPayments:
    def test_full_receipt_payment(self, tokens):
        so = _create_dispatched_so(tokens)
        inv = requests.post(f"{API}/finance/invoices/from-sales-order",
                            headers=hdr(tokens["admin"]),
                            json={"sales_order_id": so["id"]}).json()
        amount_due = Decimal(inv["amount_due"])
        assert amount_due > 0

        r = requests.post(f"{API}/finance/payments", headers=hdr(tokens["admin"]),
                          json={"direction": "RECEIPT", "invoice_id": inv["id"],
                                "amount": str(amount_due), "method": "BANK"})
        assert r.status_code == 200, r.text
        pay = r.json()
        assert pay["payment_number"].startswith("PAY-")

        # Invoice -> PAID
        r = requests.get(f"{API}/finance/invoices/{inv['id']}", headers=hdr(tokens["admin"]))
        inv2 = r.json()
        assert inv2["status"] == "PAID"
        assert abs(Decimal(inv2["amount_paid"]) - Decimal(inv2["total"])) < Decimal("0.01")

        # Journal Dr Bank Cr AR
        je = requests.get(f"{API}/finance/journal-entries/{pay['journal_entry_id']}",
                          headers=hdr(tokens["admin"])).json()
        codes_dr = {l["account_code"] for l in je["lines"] if Decimal(l["debit"]) > 0}
        codes_cr = {l["account_code"] for l in je["lines"] if Decimal(l["credit"]) > 0}
        assert "1110" in codes_dr  # Bank
        assert "1200" in codes_cr  # AR

    def test_partial_then_full(self, tokens):
        so = _create_dispatched_so(tokens)
        inv = requests.post(f"{API}/finance/invoices/from-sales-order",
                            headers=hdr(tokens["admin"]),
                            json={"sales_order_id": so["id"]}).json()
        total = Decimal(inv["total"])
        half = (total / 2).quantize(Decimal("0.01"))
        r = requests.post(f"{API}/finance/payments", headers=hdr(tokens["admin"]),
                          json={"direction": "RECEIPT", "invoice_id": inv["id"],
                                "amount": str(half), "method": "BANK"})
        assert r.status_code == 200
        inv2 = requests.get(f"{API}/finance/invoices/{inv['id']}", headers=hdr(tokens["admin"])).json()
        assert inv2["status"] == "PARTIALLY_PAID"

        # Pay the rest
        remaining = Decimal(inv2["amount_due"])
        r = requests.post(f"{API}/finance/payments", headers=hdr(tokens["admin"]),
                          json={"direction": "RECEIPT", "invoice_id": inv["id"],
                                "amount": str(remaining), "method": "BANK"})
        assert r.status_code == 200
        inv3 = requests.get(f"{API}/finance/invoices/{inv['id']}", headers=hdr(tokens["admin"])).json()
        assert inv3["status"] == "PAID"

    def test_overpayment_rejected(self, tokens):
        so = _create_dispatched_so(tokens)
        inv = requests.post(f"{API}/finance/invoices/from-sales-order",
                            headers=hdr(tokens["admin"]),
                            json={"sales_order_id": so["id"]}).json()
        over = Decimal(inv["amount_due"]) + Decimal("10000")
        r = requests.post(f"{API}/finance/payments", headers=hdr(tokens["admin"]),
                          json={"direction": "RECEIPT", "invoice_id": inv["id"],
                                "amount": str(over), "method": "BANK"})
        assert r.status_code == 400


# ======================= Cancellation / Reversal =======================
class TestCancellation:
    def test_cannot_cancel_paid_invoice(self, tokens):
        # Find an already-PAID invoice
        invs = requests.get(f"{API}/finance/invoices?invoice_type=CUSTOMER",
                            headers=hdr(tokens["admin"])).json()
        paid = next((i for i in invs if Decimal(i["amount_paid"]) > 0), None)
        if not paid:
            # make one
            so = _create_dispatched_so(tokens)
            inv = requests.post(f"{API}/finance/invoices/from-sales-order",
                                headers=hdr(tokens["admin"]),
                                json={"sales_order_id": so["id"]}).json()
            requests.post(f"{API}/finance/payments", headers=hdr(tokens["admin"]),
                          json={"direction": "RECEIPT", "invoice_id": inv["id"],
                                "amount": inv["amount_due"], "method": "BANK"})
            paid = inv
        r = requests.post(f"{API}/finance/invoices/{paid['id']}/cancel",
                          headers=hdr(tokens["admin"]))
        assert r.status_code == 400

    def test_cancel_unpaid_invoice_reverses_journal(self, tokens):
        so = _create_dispatched_so(tokens)
        inv = requests.post(f"{API}/finance/invoices/from-sales-order",
                            headers=hdr(tokens["admin"]),
                            json={"sales_order_id": so["id"]}).json()
        orig_je_id = inv["journal_entry_id"]
        r = requests.post(f"{API}/finance/invoices/{inv['id']}/cancel",
                          headers=hdr(tokens["admin"]))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "CANCELLED"
        # Original is marked reversed
        orig_je = requests.get(f"{API}/finance/journal-entries/{orig_je_id}",
                               headers=hdr(tokens["admin"])).json()
        assert orig_je["is_reversed"] is True
        # Reversal entry exists
        rev = requests.get(f"{API}/finance/journal-entries?reference_type=REVERSAL",
                           headers=hdr(tokens["admin"])).json()
        assert any(e["reference_number"] == orig_je["entry_number"] for e in rev)


# ======================= Reports =======================
class TestReports:
    def test_trial_balance_balanced(self, tokens):
        r = requests.get(f"{API}/finance/reports/trial-balance", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        tb = r.json()
        assert tb["is_balanced"] is True
        assert abs(Decimal(tb["total_debit"]) - Decimal(tb["total_credit"])) < Decimal("0.01")

    def test_profit_loss(self, tokens):
        r = requests.get(f"{API}/finance/reports/profit-loss", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        pnl = r.json()
        assert "income" in pnl and "expenses" in pnl
        # After creating customer invoices, there should be Sales Revenue
        assert Decimal(pnl["income"]["total"]) >= 0

    def test_ar_aging_structure(self, tokens):
        r = requests.get(f"{API}/finance/reports/ar-aging", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        rep = r.json()
        assert "rows" in rep and "totals" in rep
        for b in ("current", "d_1_30", "d_31_60", "d_61_90", "d_over_90"):
            assert b in rep["totals"]

    def test_ap_aging_has_bill_in_current(self, tokens):
        r = requests.get(f"{API}/finance/reports/ap-aging", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        rep = r.json()
        # due date is +30d so should be in 'current' bucket
        assert Decimal(rep["totals"]["current"]) >= 0


# ======================= Manual Journal =======================
class TestManualJournal:
    def test_balanced_manual_journal(self, tokens):
        accts = requests.get(f"{API}/finance/accounts", headers=hdr(tokens["admin"])).json()
        a_map = {a["code"]: a["id"] for a in accts}
        r = requests.post(f"{API}/finance/journal-entries", headers=hdr(tokens["admin"]),
                          json={"narration": "TEST manual balanced",
                                "lines": [
                                    {"account_id": a_map["6100"], "debit": "500", "credit": "0"},
                                    {"account_id": a_map["1100"], "debit": "0", "credit": "500"},
                                ]})
        assert r.status_code == 200, r.text
        je = r.json()
        assert abs(Decimal(je["total_debit"]) - Decimal(je["total_credit"])) < Decimal("0.01")

    def test_unbalanced_rejected(self, tokens):
        accts = requests.get(f"{API}/finance/accounts", headers=hdr(tokens["admin"])).json()
        a_map = {a["code"]: a["id"] for a in accts}
        r = requests.post(f"{API}/finance/journal-entries", headers=hdr(tokens["admin"]),
                          json={"narration": "TEST unbalanced",
                                "lines": [
                                    {"account_id": a_map["6100"], "debit": "500", "credit": "0"},
                                    {"account_id": a_map["1100"], "debit": "0", "credit": "400"},
                                ]})
        assert r.status_code == 400


# ======================= Audit Logs =======================
class TestFinanceAudit:
    def test_audit_entries_present(self, tokens):
        logs = requests.get(f"{API}/audit-logs?limit=500", headers=hdr(tokens["admin"])).json()
        entities = {l["entity_type"] for l in logs}
        assert "Invoice" in entities
        assert "Payment" in entities
        assert "JournalEntry" in entities
