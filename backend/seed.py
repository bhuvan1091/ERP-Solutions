"""Seed roles, admin user, demo products, suppliers, customers, warehouses,
inventory batches, POs, SOs, and ad campaigns."""
from __future__ import annotations
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
import random

from sqlalchemy.orm import Session

from models import (
    Role, User, Company, Warehouse, ProductCategory, Product, Supplier, Customer,
    InventoryBatch, StockMovement, PurchaseOrder, PurchaseOrderLine,
    GoodsReceipt, GoodsReceiptLine, SalesOrder, SalesOrderLine,
    AdPlatformConnection, AdCampaign, AuditLog,
    ProductType, ProductStatus, PurchaseOrderStatus, SalesOrderStatus,
    BatchStatus, StockMovementType,
)
from auth import ROLE_PERMISSIONS, hash_password


SEED_ROLES = [
    ("SUPER_ADMIN", "Super Administrator", "Full system access"),
    ("COMPANY_ADMIN", "Company Administrator", "Company-wide admin"),
    ("MANAGING_DIRECTOR", "Managing Director", "Executive leadership"),
    ("FINANCE_MANAGER", "Finance Manager", "Finance & accounting"),
    ("PROCUREMENT_MANAGER", "Procurement Manager", "Purchasing & supplier mgmt"),
    ("WAREHOUSE_MANAGER", "Warehouse Manager", "Inventory & warehouse ops"),
    ("PRODUCTION_MANAGER", "Production Manager", "Manufacturing"),
    ("QUALITY_MANAGER", "Quality Manager", "QA & batch release"),
    ("SALES_MANAGER", "Sales Manager", "Sales leadership"),
    ("SALES_REPRESENTATIVE", "Sales Representative", "Sales ops"),
    ("MARKETING_MANAGER", "Marketing Manager", "Marketing leadership"),
    ("MARKETING_EXECUTIVE", "Marketing Executive", "Campaign execution"),
    ("HR_MANAGER", "HR Manager", "Human resources"),
    ("AUDITOR", "Auditor / Read-only", "Read-only auditor"),
]


def seed_if_empty(db: Session):
    if db.query(Role).count() > 0:
        return

    # ---- Roles ----
    role_map = {}
    for code, name, desc in SEED_ROLES:
        r = Role(code=code, name=name, description=desc,
                 permissions=list(ROLE_PERMISSIONS.get(code, [])))
        db.add(r)
        db.flush()
        role_map[code] = r

    # ---- Company ----
    company = Company(
        name="GreenPeak Nutrition Pvt Ltd",
        legal_name="GreenPeak Nutrition Private Limited",
        gstin="29ABCDE1234F1Z5",
        fssai_license="10012345000123",
        address="Plot 42, Industrial Area Phase II, Bengaluru 560058",
        currency="INR", timezone="Asia/Kolkata",
        logo_url=None,
    )
    db.add(company)

    # ---- Users ----
    users_to_seed = [
        ("admin@greenpeak.in", "Admin User", "SUPER_ADMIN", "Admin@12345"),
        ("md@greenpeak.in", "Rohan Mehta", "MANAGING_DIRECTOR", "Welcome@123"),
        ("finance@greenpeak.in", "Priya Sharma", "FINANCE_MANAGER", "Welcome@123"),
        ("procurement@greenpeak.in", "Arjun Patel", "PROCUREMENT_MANAGER", "Welcome@123"),
        ("warehouse@greenpeak.in", "Suresh Kumar", "WAREHOUSE_MANAGER", "Welcome@123"),
        ("quality@greenpeak.in", "Dr Neha Rao", "QUALITY_MANAGER", "Welcome@123"),
        ("sales@greenpeak.in", "Kavita Iyer", "SALES_MANAGER", "Welcome@123"),
        ("rep@greenpeak.in", "Vikram Singh", "SALES_REPRESENTATIVE", "Welcome@123"),
        ("marketing@greenpeak.in", "Ananya Desai", "MARKETING_MANAGER", "Welcome@123"),
        ("auditor@greenpeak.in", "Internal Audit", "AUDITOR", "Welcome@123"),
    ]
    users = {}
    for email, name, role_code, pwd in users_to_seed:
        u = User(email=email, full_name=name,
                 password_hash=hash_password(pwd),
                 role_id=role_map[role_code].id, is_active=True)
        db.add(u)
        db.flush()
        users[role_code] = u
    admin = users["SUPER_ADMIN"]

    # ---- Warehouses ----
    wh1 = Warehouse(code="BLR-MAIN", name="Bengaluru Main Warehouse",
                    address="Plot 42, Industrial Area Phase II",
                    city="Bengaluru", state="Karnataka", pincode="560058")
    wh2 = Warehouse(code="MUM-WH", name="Mumbai Distribution Center",
                    address="Andheri East Logistics Park",
                    city="Mumbai", state="Maharashtra", pincode="400059")
    wh3 = Warehouse(code="DEL-WH", name="Delhi NCR Warehouse",
                    address="Sector 63, Noida",
                    city="Noida", state="Uttar Pradesh", pincode="201301")
    for w in [wh1, wh2, wh3]:
        db.add(w)
    db.flush()

    # ---- Categories ----
    cats = {}
    for name in ["Protein & Mass Gainers", "Vitamins & Minerals",
                 "Sports Nutrition", "Herbal Supplements", "Wellness & Immunity",
                 "Weight Management", "Pre & Post Workout",
                 "Raw Materials", "Packaging Materials"]:
        c = ProductCategory(name=name)
        db.add(c)
        db.flush()
        cats[name] = c

    # ---- Products ----
    products_data = [
        ("Whey Protein Isolate Chocolate 1kg", "GreenPeak Pure", "Protein & Mass Gainers",
         ProductType.FINISHED_GOOD, "1kg", "Chocolate", "kg", 1800, 2999, 3499, 100, 20,
         "https://images.unsplash.com/photo-1693996045899-7cf0ac0229c7?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwzfHxwcm90ZWluJTIwcG93ZGVyJTIwc3VwcGxlbWVudCUyMGJvdHRsZXxlbnwwfHx8fDE3OTA5NDYxODh8MA&ixlib=rb-4.1.0&q=85"),
        ("Whey Protein Blend Vanilla 2kg", "GreenPeak Core", "Protein & Mass Gainers",
         ProductType.FINISHED_GOOD, "2kg", "Vanilla", "kg", 2400, 3999, 4599, 80, 15,
         "https://images.unsplash.com/photo-1693996045899-7cf0ac0229c7?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwzfHxwcm90ZWluJTIwcG93ZGVyJTIwc3VwcGxlbWVudCUyMGJvdHRsZXxlbnwwfHx8fDE3OTA5NDYxODh8MA&ixlib=rb-4.1.0&q=85"),
        ("Multivitamin Daily 60 Tablets", "GreenPeak Core", "Vitamins & Minerals",
         ProductType.FINISHED_GOOD, "60 tabs", None, "unit", 180, 449, 549, 300, 50,
         "https://images.unsplash.com/photo-1633171036157-78d53387fdc0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzV8MHwxfHNlYXJjaHwyfHx2aXRhbWluJTIwcGlsbHMlMjBib3R0bGUlMjB3aGl0ZSUyMGJhY2tncm91bmR8ZW58MHx8fHwxNzkwOTQ2MTg4fDA&ixlib=rb-4.1.0&q=85"),
        ("Vitamin D3 2000 IU 90 Capsules", "GreenPeak Core", "Vitamins & Minerals",
         ProductType.FINISHED_GOOD, "90 caps", None, "unit", 220, 599, 699, 250, 60,
         "https://images.unsplash.com/photo-1633171036157-78d53387fdc0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzV8MHwxfHNlYXJjaHwyfHx2aXRhbWluJTIwcGlsbHMlMjBib3R0bGUlMjB3aGl0ZSUyMGJhY2tncm91bmR8ZW58MHx8fHwxNzkwOTQ2MTg4fDA&ixlib=rb-4.1.0&q=85"),
        ("BCAA 2:1:1 Powder 300g", "GreenPeak Pro", "Sports Nutrition",
         ProductType.FINISHED_GOOD, "300g", "Watermelon", "unit", 950, 1799, 2099, 150, 30, None),
        ("Creatine Monohydrate 250g", "GreenPeak Pro", "Sports Nutrition",
         ProductType.FINISHED_GOOD, "250g", "Unflavoured", "unit", 480, 1099, 1299, 200, 40, None),
        ("Ashwagandha KSM-66 60 Caps", "GreenPeak Herbal", "Herbal Supplements",
         ProductType.FINISHED_GOOD, "60 caps", None, "unit", 350, 849, 999, 180, 40, None),
        ("Omega-3 Fish Oil 90 Softgels", "GreenPeak Core", "Wellness & Immunity",
         ProductType.FINISHED_GOOD, "90 softgels", None, "unit", 320, 799, 949, 220, 50, None),
        ("Immunity Booster Chewables 30", "GreenPeak Kids", "Wellness & Immunity",
         ProductType.FINISHED_GOOD, "30 chewables", "Orange", "unit", 140, 399, 499, 150, 30, None),
        ("L-Carnitine 1500 Liquid Shot", "GreenPeak Lean", "Weight Management",
         ProductType.FINISHED_GOOD, "60ml", "Citrus", "unit", 110, 299, 349, 200, 40, None),
        ("Pre-Workout Explosive 400g", "GreenPeak Pro", "Pre & Post Workout",
         ProductType.FINISHED_GOOD, "400g", "Blueberry Blast", "unit", 1300, 2499, 2799, 100, 20, None),
        ("Whey Protein Concentrate (Bulk)", "Ingredion", "Raw Materials",
         ProductType.RAW_MATERIAL, "25kg sack", None, "kg", 820, 0, 0, 500, 100, None),
        ("Vitamin C Ascorbic Acid Powder", "DSM Nutritional", "Raw Materials",
         ProductType.RAW_MATERIAL, "10kg", None, "kg", 650, 0, 0, 200, 50, None),
        ("HDPE Supplement Bottles 500ml", "Pack-Right Industries", "Packaging Materials",
         ProductType.PACKAGING, "pcs", None, "unit", 18, 0, 0, 5000, 1000, None),
    ]
    products = []
    for i, (name, brand, cat_name, ptype, pack, flav, uom, pp, sp, mrp, max_s, reorder, img) in enumerate(products_data):
        sku_base = "".join(x for x in name.upper() if x.isalnum())[:4]
        sku = f"{sku_base}-{i+1:04d}"
        p = Product(
            sku=sku, name=name, brand=brand,
            category_id=cats[cat_name].id,
            product_type=ptype, status=ProductStatus.ACTIVE,
            description=f"{brand} premium {name}",
            unit_of_measure=uom, pack_size=pack, flavour=flav,
            purchase_price=Decimal(str(pp)),
            selling_price=Decimal(str(sp)),
            mrp=Decimal(str(mrp)),
            tax_rate=Decimal("18"),
            hsn_code="21069099",
            shelf_life_days=730,
            reorder_level=Decimal(str(reorder)),
            min_stock=Decimal(str(reorder)),
            max_stock=Decimal(str(max_s)),
            allergens=["Milk", "Soy"] if "Whey" in name or "Protein" in name else [],
            nutrition_facts={
                "serving_size": "30g" if "Protein" in name else "1 unit",
                "protein_g": 24 if "Protein" in name else 0,
                "calories": 120 if "Protein" in name else 5,
            },
            ingredients="Whey protein isolate, cocoa, natural flavors" if "Whey" in name else "Vitamin blend",
            image_url=img,
        )
        db.add(p)
        db.flush()
        products.append(p)

    # ---- Suppliers ----
    suppliers_data = [
        ("Ingredion India Pvt Ltd", "ingredion@supplier.in", "7ABCDE1234F1Z5", True),
        ("DSM Nutritional Products", "dsm@supplier.in", "27ABCDE5678G1Z2", True),
        ("Pack-Right Industries", "sales@packright.in", "27PQRST9876A1Z4", True),
        ("Herbal Extract Co", "orders@herbalextract.in", "29ABCHE1234D1Z8", True),
        ("Flavor Masters India", "info@flavormasters.in", "33ABCFM4567K1Z9", False),
    ]
    suppliers = []
    for i, (name, email, gst, approved) in enumerate(suppliers_data):
        s = Supplier(code=f"SUP-{i+1:04d}", name=name,
                     legal_name=name, gstin=gst,
                     contact_person="Procurement Lead", email=email,
                     phone=f"+91 98765 4321{i}",
                     address="Industrial Area", city="Bengaluru",
                     state="Karnataka", pincode="560058",
                     payment_terms_days=30, is_approved=approved)
        db.add(s)
        db.flush()
        suppliers.append(s)

    # ---- Customers ----
    customers_data = [
        ("HealthMart Retail Chain", "WHOLESALE", "orders@healthmart.in", "29ABCHM1234R1Z1", 500000, 30),
        ("FitLife Gym Network", "WHOLESALE", "procurement@fitlife.in", "29ABCFL5678G1Z3", 300000, 30),
        ("Wellness Pharmacy Group", "WHOLESALE", "ap@wellnesspharma.in", "27ABCWP9876A1Z5", 400000, 45),
        ("Nutrition Direct Distributors", "DISTRIBUTOR", "info@nutridirect.in", "33ABCND1111D1Z7", 1000000, 60),
        ("Priya Nair", "RETAIL", "priya.nair@email.com", None, 0, 0),
        ("Rajesh Verma", "RETAIL", "rajesh.v@email.com", None, 0, 0),
        ("GymKing Mumbai", "WHOLESALE", "orders@gymking.in", "27ABCGK2222M1Z8", 200000, 30),
        ("Sports Edge Chennai", "DISTRIBUTOR", "sports@sportsedge.in", "33ABCSE3333C1Z1", 600000, 45),
    ]
    customers = []
    for i, (name, ctype, email, gst, limit, terms) in enumerate(customers_data):
        c = Customer(
            code=f"CUST-{i+1:04d}", name=name, customer_type=ctype, gstin=gst,
            email=email, phone=f"+91 90000 1111{i}",
            contact_person=name if ctype == "RETAIL" else "Purchase Head",
            billing_address=f"{name} HQ Address",
            shipping_address=f"{name} Delivery Address",
            city=["Mumbai", "Bengaluru", "Chennai", "Delhi", "Pune"][i % 5],
            state=["Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Maharashtra"][i % 5],
            pincode="400001",
            credit_limit=Decimal(str(limit)), payment_terms_days=terms,
        )
        db.add(c)
        db.flush()
        customers.append(c)

    # ---- Inventory Batches (direct seed, bypasses PO for demo) ----
    today = date.today()
    for p in products[:11]:  # finished goods
        for j, wh in enumerate([wh1, wh2]):
            batch_num = f"B{today.strftime('%y%m')}{p.sku[-4:]}{j+1:02d}"
            # Mix of near-expiry, fresh, and one expired
            if p.id == products[0].id and j == 0:
                exp = today + timedelta(days=35)  # near expiry
            elif p.id == products[2].id and j == 1:
                exp = today - timedelta(days=5)  # expired
            else:
                exp = today + timedelta(days=random.randint(180, 540))
            mfg = exp - timedelta(days=p.shelf_life_days)
            qty = Decimal(random.randint(30, 180))
            b = InventoryBatch(
                batch_number=batch_num, product_id=p.id, warehouse_id=wh.id,
                manufacture_date=mfg, expiry_date=exp,
                quantity_on_hand=qty, cost_per_unit=p.purchase_price,
                status=BatchStatus.EXPIRED if exp < today else BatchStatus.RELEASED,
            )
            db.add(b)
            db.flush()
            db.add(StockMovement(batch_id=b.id, movement_type=StockMovementType.GRN,
                                 quantity=qty, reference_type="SEED",
                                 reference_number="OPENING", notes="Opening stock",
                                 user_id=admin.id))

    # ---- Sample PO (pending approval) ----
    po1 = PurchaseOrder(
        po_number="PO-2026-00001",
        supplier_id=suppliers[0].id, warehouse_id=wh1.id,
        order_date=today, expected_delivery_date=today + timedelta(days=14),
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        created_by=users["PROCUREMENT_MANAGER"].id,
    )
    db.add(po1)
    db.flush()
    subtotal, tax = Decimal(0), Decimal(0)
    for prod, qty, price in [(products[11], 200, 820), (products[12], 80, 650)]:
        sub = Decimal(qty) * Decimal(price)
        t = sub * Decimal("0.18")
        db.add(PurchaseOrderLine(
            order_id=po1.id, product_id=prod.id, quantity=Decimal(qty),
            unit_price=Decimal(price), tax_rate=Decimal(18), line_total=sub + t,
        ))
        subtotal += sub
        tax += t
    po1.subtotal = subtotal
    po1.tax_amount = tax
    po1.total = subtotal + tax

    # ---- Approved PO (received) demonstration ----
    po2 = PurchaseOrder(
        po_number="PO-2026-00002",
        supplier_id=suppliers[2].id, warehouse_id=wh1.id,
        order_date=today - timedelta(days=15),
        expected_delivery_date=today - timedelta(days=2),
        status=PurchaseOrderStatus.RECEIVED,
        created_by=users["PROCUREMENT_MANAGER"].id,
        approved_by=users["MANAGING_DIRECTOR"].id,
        approved_at=datetime.now(timezone.utc) - timedelta(days=14),
    )
    db.add(po2)
    db.flush()
    pl = PurchaseOrderLine(
        order_id=po2.id, product_id=products[13].id,  # packaging bottles
        quantity=Decimal(2000), received_quantity=Decimal(2000),
        unit_price=Decimal(18), tax_rate=Decimal(18),
        line_total=Decimal(2000 * 18) * Decimal("1.18"),
    )
    db.add(pl)
    po2.subtotal = Decimal(2000 * 18)
    po2.tax_amount = Decimal(2000 * 18) * Decimal("0.18")
    po2.total = po2.subtotal + po2.tax_amount

    # ---- Sales Orders ----
    for i in range(6):
        cust = customers[i % len(customers)]
        prod = products[i % 11]
        qty = Decimal(random.randint(5, 25))
        unit_price = prod.selling_price
        line_sub = qty * unit_price
        tax_amt = line_sub * Decimal("0.18")
        total = line_sub + tax_amt
        channel = ["DIRECT", "SHOPIFY", "META_AD", "GOOGLE_AD", "DIRECT", "WOOCOMMERCE"][i]
        so = SalesOrder(
            so_number=f"SO-2026-{i+1:05d}",
            customer_id=cust.id, warehouse_id=wh1.id,
            order_date=today - timedelta(days=i * 2),
            expected_dispatch_date=today - timedelta(days=i * 2 - 3),
            status=[SalesOrderStatus.DISPATCHED, SalesOrderStatus.CONFIRMED,
                    SalesOrderStatus.ALLOCATED, SalesOrderStatus.CONFIRMED,
                    SalesOrderStatus.DISPATCHED, SalesOrderStatus.CONFIRMED][i],
            subtotal=line_sub, tax_amount=tax_amt, total=total,
            source_channel=channel,
            utm_source="meta" if "META" in channel else ("google" if "GOOGLE" in channel else None),
            utm_campaign="Summer Protein Launch" if "META" in channel else ("Vitamin Push" if "GOOGLE" in channel else None),
            created_by=users["SALES_REPRESENTATIVE"].id,
        )
        db.add(so)
        db.flush()
        db.add(SalesOrderLine(
            order_id=so.id, product_id=prod.id, quantity=qty,
            unit_price=unit_price, tax_rate=Decimal(18),
            line_total=total,
        ))

    # ---- Ad Platform Connections ----
    connections = []
    for plat, acc_name, acc_id in [
        ("META", "GreenPeak Nutrition - Meta", "act_1234567890"),
        ("GOOGLE_ADS", "GreenPeak Google Ads", "123-456-7890"),
        ("LINKEDIN", "GreenPeak LinkedIn", "ln_987654"),
        ("TIKTOK", "GreenPeak TikTok Ads", "tt_567890"),
        ("AMAZON", "GreenPeak Amazon Advertising", "amz_111222"),
    ]:
        conn = AdPlatformConnection(platform=plat, account_name=acc_name,
                                    account_id=acc_id, status="CONNECTED",
                                    last_sync_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 6)))
        db.add(conn)
        db.flush()
        connections.append(conn)

    # ---- Ad Campaigns (mock) ----
    campaign_specs = [
        ("META", "Summer Protein Launch - IG Feed", "CONVERSIONS", products[0]),
        ("META", "Whey Vanilla Retargeting", "CONVERSIONS", products[1]),
        ("GOOGLE_ADS", "Vitamin D3 Search", "LEADS", products[3]),
        ("GOOGLE_ADS", "Multivitamin Shopping Ads", "CONVERSIONS", products[2]),
        ("LINKEDIN", "B2B Wholesale Outreach", "LEADS", None),
        ("TIKTOK", "Pre-Workout UGC", "AWARENESS", products[10]),
        ("AMAZON", "Omega-3 Sponsored Products", "CONVERSIONS", products[7]),
        ("META", "Immunity Winter Push", "CONVERSIONS", products[8]),
    ]
    for i, (plat, name, obj, prod) in enumerate(campaign_specs):
        imp = random.randint(80000, 500000)
        clicks = int(imp * random.uniform(0.015, 0.045))
        conv = int(clicks * random.uniform(0.02, 0.08))
        avg_order = random.uniform(900, 2500)
        spend = Decimal(str(round(clicks * random.uniform(8, 25), 2)))
        rev = Decimal(str(round(conv * avg_order, 2)))
        conn_id = next((c.id for c in connections if c.platform == plat), None)
        c = AdCampaign(
            external_id=f"{plat.lower()}_{10000+i}",
            platform=plat, account_id=conn_id,
            name=name, objective=obj,
            status="ACTIVE" if i % 4 != 3 else "PAUSED",
            product_id=prod.id if prod else None,
            start_date=today - timedelta(days=random.randint(10, 45)),
            end_date=today + timedelta(days=random.randint(10, 60)),
            daily_budget=Decimal(str(random.randint(500, 5000))),
            total_budget=Decimal(str(random.randint(30000, 300000))),
            spend_to_date=spend,
            impressions=imp, clicks=clicks, conversions=conv,
            conversion_value=rev,
        )
        db.add(c)

    db.commit()
