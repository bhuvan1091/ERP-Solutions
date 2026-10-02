"""
End-to-end backend tests for Nutrition ERP (Phase 1).
Covers Auth/RBAC, Products, Suppliers, Customers, Warehouses, Inventory,
Purchase Orders (full lifecycle), Sales Orders (FEFO allocate+dispatch),
Dashboard, Advertising, and Audit logs.
"""
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend/.env
    try:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break
    except Exception:
        pass
assert BASE_URL, "REACT_APP_BACKEND_URL not configured"

API = f"{BASE_URL}/api"

CREDS = {
    "admin": ("admin@greenpeak.in", "Admin@12345"),
    "md": ("md@greenpeak.in", "Welcome@123"),
    "procurement": ("procurement@greenpeak.in", "Welcome@123"),
    "warehouse": ("warehouse@greenpeak.in", "Welcome@123"),
    "sales": ("sales@greenpeak.in", "Welcome@123"),
    "rep": ("rep@greenpeak.in", "Welcome@123"),
}


# --------- fixtures ---------
def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def tokens():
    return {k: _login(*v) for k, v in CREDS.items()}


def hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- Health ----------
def test_health():
    r = requests.get(f"{API}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ---------- Auth ----------
class TestAuth:
    def test_login_admin(self, tokens):
        assert tokens["admin"]
        r = requests.get(f"{API}/auth/me", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        me = r.json()
        assert me["email"] == "admin@greenpeak.in"
        assert me["role_code"] in ("SUPER_ADMIN", "ADMIN")
        assert isinstance(me["permissions"], list) and len(me["permissions"]) > 0

    def test_login_sales(self, tokens):
        r = requests.get(f"{API}/auth/me", headers=hdr(tokens["sales"]))
        assert r.status_code == 200
        me = r.json()
        assert me["email"] == "sales@greenpeak.in"
        assert me["role_code"]
        # should include a sales-related perm
        assert any("sales" in p for p in me["permissions"])

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@greenpeak.in", "password": "wrong"})
        assert r.status_code in (400, 401)


# ---------- RBAC ----------
class TestRBAC:
    def test_rep_cannot_create_product(self, tokens):
        r = requests.post(f"{API}/products",
                          headers=hdr(tokens["rep"]),
                          json={"name": "Illegal Rep Product", "selling_price": 100})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_admin_can_create_product(self, tokens):
        suffix = uuid.uuid4().hex[:6].upper()
        r = requests.post(f"{API}/products",
                          headers=hdr(tokens["admin"]),
                          json={"sku": f"TEST-A-{suffix}",
                                "name": f"TEST_Admin_{suffix}", "selling_price": 199})
        assert r.status_code == 200, r.text
        # cleanup via soft delete
        pid = r.json()["id"]
        requests.delete(f"{API}/products/{pid}", headers=hdr(tokens["admin"]))


# ---------- Products ----------
class TestProducts:
    def test_list_seeded(self, tokens):
        r = requests.get(f"{API}/products", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 14, f"Expected >=14 seeded products, got {len(data)}"

    def test_create_update_softdelete(self, tokens):
        suffix = uuid.uuid4().hex[:6].upper()
        name = f"TEST_Prod_{suffix}"
        r = requests.post(f"{API}/products", headers=hdr(tokens["admin"]),
                          json={"sku": f"TEST-P-{suffix}", "name": name,
                                "selling_price": 299, "mrp": 349})
        assert r.status_code == 200, r.text
        p = r.json()
        pid = p["id"]
        assert p["name"] == name
        assert p["sku"]

        # update
        r = requests.patch(f"{API}/products/{pid}", headers=hdr(tokens["admin"]),
                           json={"selling_price": 399})
        assert r.status_code == 200
        assert Decimal(r.json()["selling_price"]) == Decimal("399")

        # soft delete
        r = requests.delete(f"{API}/products/{pid}", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        r = requests.get(f"{API}/products/{pid}", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        assert r.json()["status"] == "DISCONTINUED"


# ---------- Suppliers ----------
class TestSuppliers:
    def test_create_and_approve(self, tokens):
        payload = {"name": f"TEST_Sup_{uuid.uuid4().hex[:6]}", "email": "sup@test.com"}
        r = requests.post(f"{API}/suppliers", headers=hdr(tokens["admin"]), json=payload)
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        assert r.json()["is_approved"] is False

        r = requests.post(f"{API}/suppliers/{sid}/approve", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        assert r.json()["is_approved"] is True


# ---------- Customers ----------
class TestCustomers:
    def test_create_and_filter(self, tokens):
        payload = {"name": f"TEST_Cust_{uuid.uuid4().hex[:6]}", "customer_type": "WHOLESALE"}
        r = requests.post(f"{API}/customers", headers=hdr(tokens["admin"]), json=payload)
        assert r.status_code == 200, r.text

        r = requests.get(f"{API}/customers?customer_type=WHOLESALE", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        data = r.json()
        assert all(c["customer_type"] == "WHOLESALE" for c in data)
        assert len(data) >= 1


# ---------- Warehouses ----------
class TestWarehouses:
    def test_list_seeded(self, tokens):
        r = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_create(self, tokens):
        code = f"TWH{uuid.uuid4().hex[:4].upper()}"
        r = requests.post(f"{API}/warehouses", headers=hdr(tokens["admin"]),
                          json={"code": code, "name": f"TEST_WH_{code}", "city": "TestCity"})
        assert r.status_code == 200, r.text
        assert r.json()["code"] == code


# ---------- Inventory ----------
class TestInventory:
    def test_near_expiry_filter(self, tokens):
        r = requests.get(f"{API}/inventory/batches?near_expiry_days=60", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        today = date.today()
        for b in r.json():
            if b.get("expiry_date"):
                exp = date.fromisoformat(b["expiry_date"])
                assert today <= exp <= today + timedelta(days=60), f"Batch {b['batch_number']} out of range"

    def test_expired_only_filter(self, tokens):
        r = requests.get(f"{API}/inventory/batches?expired_only=true", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        today = date.today()
        for b in r.json():
            if b.get("expiry_date"):
                assert date.fromisoformat(b["expiry_date"]) < today

    def test_adjust_positive_and_negative(self, tokens):
        # Pick any batch
        r = requests.get(f"{API}/inventory/batches", headers=hdr(tokens["warehouse"]))
        assert r.status_code == 200
        batches = [b for b in r.json() if Decimal(b["quantity_on_hand"]) > 5]
        assert batches, "No batch with stock available"
        b = batches[0]
        initial = Decimal(b["quantity_on_hand"])

        # +5
        r = requests.post(f"{API}/inventory/adjust", headers=hdr(tokens["warehouse"]),
                          json={"batch_id": b["id"], "quantity_delta": "5", "notes": "TEST+"})
        assert r.status_code == 200
        assert Decimal(r.json()["new_quantity"]) == initial + Decimal("5")

        # -5 back
        r = requests.post(f"{API}/inventory/adjust", headers=hdr(tokens["warehouse"]),
                          json={"batch_id": b["id"], "quantity_delta": "-5", "notes": "TEST-"})
        assert r.status_code == 200

    def test_adjust_negative_rejected(self, tokens):
        r = requests.get(f"{API}/inventory/batches", headers=hdr(tokens["warehouse"]))
        b = r.json()[0]
        huge_neg = f"-{int(Decimal(b['quantity_on_hand']) + 10000)}"
        r = requests.post(f"{API}/inventory/adjust", headers=hdr(tokens["warehouse"]),
                          json={"batch_id": b["id"], "quantity_delta": huge_neg, "notes": "TEST neg"})
        assert r.status_code == 400


# ---------- Purchase Order lifecycle ----------
class TestPurchaseLifecycle:
    def test_full_po_grn_flow(self, tokens):
        # pick supplier, warehouse, product
        suppliers = requests.get(f"{API}/suppliers?is_approved=true", headers=hdr(tokens["admin"])).json()
        assert suppliers, "No approved suppliers seeded"
        warehouses = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"])).json()
        products = requests.get(f"{API}/products", headers=hdr(tokens["admin"])).json()
        supplier_id = suppliers[0]["id"]
        warehouse_id = warehouses[0]["id"]
        product_id = products[0]["id"]

        # create as procurement
        r = requests.post(f"{API}/purchase-orders", headers=hdr(tokens["procurement"]),
                          json={"supplier_id": supplier_id, "warehouse_id": warehouse_id,
                                "lines": [{"product_id": product_id, "quantity": "20",
                                           "unit_price": "100", "tax_rate": "18"}]})
        assert r.status_code == 200, r.text
        po = r.json()
        assert po["status"] == "PENDING_APPROVAL"
        po_id = po["id"]
        po_line_id = po["lines"][0]["id"]

        # Rep cannot approve
        r_bad = requests.post(f"{API}/purchase-orders/{po_id}/approve", headers=hdr(tokens["rep"]))
        assert r_bad.status_code == 403

        # Approve as MD
        r = requests.post(f"{API}/purchase-orders/{po_id}/approve", headers=hdr(tokens["md"]))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "APPROVED"

        # GRN as warehouse
        batch_no = f"TBATCH{uuid.uuid4().hex[:6].upper()}"
        today = date.today()
        r = requests.post(f"{API}/goods-receipts", headers=hdr(tokens["warehouse"]),
                          json={"purchase_order_id": po_id,
                                "lines": [{"po_line_id": po_line_id, "quantity": "20",
                                           "batch_number": batch_no,
                                           "manufacture_date": today.isoformat(),
                                           "expiry_date": (today + timedelta(days=365)).isoformat()}]})
        assert r.status_code == 200, r.text
        assert r.json()["po_status"] == "RECEIVED"

        # Verify batch created with qty 20
        batches = requests.get(f"{API}/inventory/batches", headers=hdr(tokens["admin"])).json()
        new_batch = next((b for b in batches if b["batch_number"] == batch_no), None)
        assert new_batch is not None
        assert Decimal(new_batch["quantity_on_hand"]) == Decimal("20")

        # Verify stock movement GRN
        movs = requests.get(f"{API}/inventory/movements?product_id={product_id}",
                            headers=hdr(tokens["admin"])).json()
        assert any(m["movement_type"] == "GRN" and m["batch_number"] == batch_no for m in movs)


# ---------- Sales Order FEFO ----------
class TestSalesLifecycle:
    def test_fefo_allocate_and_dispatch(self, tokens):
        # Find Bengaluru warehouse
        whs = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"])).json()
        bengaluru = next((w for w in whs if "Bengaluru" in w["name"] or "Bangalore" in w["name"]), whs[0])
        wh_id = bengaluru["id"]

        # Find product with 2+ released batches in this warehouse
        batches = requests.get(
            f"{API}/inventory/batches?warehouse_id={wh_id}&status=RELEASED",
            headers=hdr(tokens["admin"])).json()
        from collections import defaultdict
        by_prod = defaultdict(list)
        for b in batches:
            if Decimal(b["quantity_on_hand"]) - Decimal(b["quantity_reserved"]) >= Decimal("1"):
                by_prod[b["product_id"]].append(b)
        product_id = None
        for pid, bl in by_prod.items():
            if len(bl) >= 2:
                product_id = pid
                prod_batches = sorted(bl, key=lambda x: x["expiry_date"] or "9999-12-31")
                break
        if product_id is None:
            pytest.skip("No product with 2+ batches in Bengaluru warehouse")

        earliest_batch = prod_batches[0]

        customers = requests.get(f"{API}/customers", headers=hdr(tokens["admin"])).json()
        assert customers
        cust_id = customers[0]["id"]

        # Create SO as sales mgr
        r = requests.post(f"{API}/sales-orders", headers=hdr(tokens["sales"]),
                          json={"customer_id": cust_id, "warehouse_id": wh_id,
                                "lines": [{"product_id": product_id, "quantity": "1"}]})
        assert r.status_code == 200, r.text
        so = r.json()
        so_id = so["id"]
        assert so["status"] == "CONFIRMED"

        # Allocate
        r = requests.post(f"{API}/sales-orders/{so_id}/allocate", headers=hdr(tokens["sales"]))
        assert r.status_code == 200, r.text
        so = r.json()
        assert so["status"] == "ALLOCATED"
        allocated = so["lines"][0]["allocated_batch_id"]
        # FEFO: allocated batch must have the earliest expiry (ties allowed)
        min_expiry = min(b["expiry_date"] for b in prod_batches if b["expiry_date"])
        allocated_batch = next(b for b in prod_batches if b["id"] == allocated)
        assert allocated_batch["expiry_date"] == min_expiry, \
            f"FEFO failed: allocated expiry {allocated_batch['expiry_date']} != min {min_expiry}"

        # Pre-dispatch qty from the actually allocated batch
        pre_q = Decimal(allocated_batch["quantity_on_hand"])

        # Dispatch
        r = requests.post(f"{API}/sales-orders/{so_id}/dispatch", headers=hdr(tokens["sales"]))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "DISPATCHED"

        # Verify quantity reduced
        batches2 = requests.get(f"{API}/inventory/batches?warehouse_id={wh_id}",
                                headers=hdr(tokens["admin"])).json()
        updated = next(b for b in batches2 if b["id"] == allocated)
        assert Decimal(updated["quantity_on_hand"]) == pre_q - Decimal("1")

        # Verify ISSUE movement with negative qty
        movs = requests.get(f"{API}/inventory/movements?product_id={product_id}",
                            headers=hdr(tokens["admin"])).json()
        issue = next((m for m in movs if m["movement_type"] == "ISSUE"
                      and m["reference_number"] == so["so_number"]), None)
        assert issue is not None
        assert Decimal(issue["quantity"]) < 0

    def test_allocate_insufficient_stock(self, tokens):
        whs = requests.get(f"{API}/warehouses", headers=hdr(tokens["admin"])).json()
        products = requests.get(f"{API}/products", headers=hdr(tokens["admin"])).json()
        customers = requests.get(f"{API}/customers", headers=hdr(tokens["admin"])).json()
        # Order huge qty
        r = requests.post(f"{API}/sales-orders", headers=hdr(tokens["sales"]),
                          json={"customer_id": customers[0]["id"],
                                "warehouse_id": whs[0]["id"],
                                "lines": [{"product_id": products[0]["id"], "quantity": "999999"}]})
        assert r.status_code == 200
        so_id = r.json()["id"]
        r = requests.post(f"{API}/sales-orders/{so_id}/allocate", headers=hdr(tokens["sales"]))
        assert r.status_code == 400
        # cleanup
        requests.post(f"{API}/sales-orders/{so_id}/cancel", headers=hdr(tokens["sales"]))


# ---------- Dashboard ----------
class TestDashboard:
    def test_dashboard_shape(self, tokens):
        r = requests.get(f"{API}/dashboard", headers=hdr(tokens["admin"]))
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["kpis"]) == 8
        assert len(d["revenue_trend"]) == 14
        assert isinstance(d["low_stock"], list)
        assert isinstance(d["near_expiry"], list)
        assert isinstance(d["pending_approvals"], list)
        assert isinstance(d["top_products"], list)
        assert isinstance(d["campaign_summary"], list)
        assert len(d["campaign_summary"]) == 5, \
            f"Expected 5 platforms, got {len(d['campaign_summary'])}"
        assert isinstance(d["recent_activity"], list)


# ---------- Advertising ----------
class TestAdvertising:
    def test_campaigns(self, tokens):
        r = requests.get(f"{API}/advertising/campaigns", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        assert len(r.json()) >= 8

    def test_connections(self, tokens):
        r = requests.get(f"{API}/advertising/connections", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        assert len(r.json()) >= 5

    def test_summary(self, tokens):
        r = requests.get(f"{API}/advertising/summary", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (dict, list))


# ---------- Audit Logs ----------
class TestAudit:
    def test_logs_present(self, tokens):
        r = requests.get(f"{API}/audit-logs?limit=200", headers=hdr(tokens["admin"]))
        assert r.status_code == 200
        logs = r.json()
        assert len(logs) > 0
        actions = {l["action"] for l in logs}
        assert "CREATE" in actions
        # user_email filled on most entries
        emails = [l.get("user_email") for l in logs if l.get("user_email")]
        assert emails, "No audit entries carry user_email"
