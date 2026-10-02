# GreenPeak Nutrition ERP — Product Requirements

## Original Problem Statement
Production-oriented ERP web application for a nutrition products company (health supplements, protein powders, vitamins, minerals, nutraceuticals, sports nutrition). Must manage the entire business lifecycle: product management, procurement, inventory, manufacturing, QA, batch traceability, expiry management, sales, CRM, finance, logistics, e-commerce, advertising campaigns, marketing attribution, and reporting. (14 modules total.)

## Architecture Decision
- User chose Java Spring Boot + PostgreSQL originally. Environment constraint (supervisor hardcoded to uvicorn, no JDK pre-installed) made that unworkable in this preview container. User approved **Option A: Python FastAPI + PostgreSQL + React**, preserving ERP-grade relational schema, double-entry readiness, and clean module boundaries.
- Modular monolith: `/app/backend/{models.py, auth.py, schemas.py, helpers.py, routers/*}`.
- Frontend: React 19 + CRA + Tailwind + Shadcn primitives + TanStack Query + Recharts + lucide-react.

## Tech Stack
| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2, python-jose JWT, passlib bcrypt |
| DB | PostgreSQL 15 (`erp` user / `nutrition_erp` database) |
| Frontend | React 19 + Tailwind + Shadcn + TanStack Query + Recharts |
| Auth | JWT access (24h) + refresh (30d), 14 default roles, permission-based RBAC |

## User Personas (14 role templates)
Super Admin, Company Admin, Managing Director, Finance Mgr, Procurement Mgr, Warehouse Mgr, Production Mgr, Quality Mgr, Sales Mgr, Sales Rep, Marketing Mgr, Marketing Executive, HR Mgr, Auditor (read-only).

## Phase 1 — Implemented (Oct 2026)
- **Auth / RBAC**: JWT login/refresh/me/logout, 14 seeded roles with permission catalogue (`product:*, supplier:*, inventory:adjust, purchase:approve, sales:dispatch, quality:release, advertising:*, admin:*, audit:read, ...`). Backend enforces permissions on every endpoint via `require_permission()`.
- **Product masters**: SKU, brand, category, type (RAW/PACK/SEMI/FG/SERVICE), pricing (purchase/sell/MRP), GST %, HSN, pack size, flavour, UoM, shelf-life, reorder/min/max, allergens, nutrition facts, image. CRUD + filters.
- **Suppliers**: CRUD, GSTIN/PAN, payment terms, approval workflow.
- **Customers**: CRUD, type (RETAIL/WHOLESALE/DISTRIBUTOR/DIRECT), credit limit, terms.
- **Warehouses**: 3 seeded (BLR / MUM / DEL), CRUD.
- **Inventory ledger**: `InventoryBatch` (product × warehouse × batch_number, mfg/exp, status QUARANTINE/RELEASED/HOLD/REJECTED/EXPIRED). `StockMovement` immutable ledger (GRN, ISSUE, ADJUSTMENT, TRANSFER_IN/OUT, PRODUCTION_IN/OUT, RETURN_IN/OUT). Filters: near-expiry (≤60d), expired, warehouse, status, search. Stock adjustments logged + negative-stock blocked.
- **Procurement**: Draft→PendingApproval→Approved→PartiallyReceived/Received→Cancelled. Multi-line, tax breakdown. Approve/cancel. GRN with batch# + mfg/exp dates creates `InventoryBatch` + `StockMovement`. PO status auto-updates on partial vs full receipt.
- **Sales**: Confirmed→Allocated (FEFO: earliest-expiry released batch, respecting warehouse)→Dispatched. Dispatch decrements on-hand and emits negative-signed movement. Cancel releases reservations.
- **Dashboard**: 8 KPIs, 14-day revenue trend, campaign spend by platform, pending approvals, near-expiry batches, low-stock, top products (30d), recent audit activity.
- **Advertising (mock data, production-shaped schema)**: 5 platform connectors (Meta, Google Ads, LinkedIn, TikTok, Amazon), 8 seeded campaigns with impressions/clicks/CTR/CPC/CPA/ROAS, platform summary + ERP-attributed revenue (via `SalesOrder.campaign_id` + UTM).
- **Audit log**: Every CREATE / UPDATE / DELETE / APPROVE / LOGIN / LOGOUT logged with user email, entity, details JSON.
- **Users admin**: Invite users, assign one of 14 roles, see all permissions.
- **UI**: Forest-green ERP shell, collapsible sidebar, topbar w/ global search + notifications + profile, breadcrumbs, dense data tables, filters, modal forms, shimmer loading, status badges. Chivo + IBM Plex Sans typography. All interactives have `data-testid`.

## Seeded demo data (auto-run on first startup)
- 1 Company, 3 Warehouses, 9 Product Categories, 14 Products (incl. 2 raw materials + 1 packaging), 5 Suppliers (4 approved), 8 Customers, 22 Inventory Batches (incl. 1 near-expiry + 1 expired for the dashboard), 2 Purchase Orders (1 pending, 1 received), 6 Sales Orders (mix of statuses), 5 Ad Platform Connections, 8 Ad Campaigns.
- 10 seeded users spanning all key roles. Credentials in `/app/memory/test_credentials.md`.

## Testing status
- Backend: 24/24 tests pass (`/app/backend/tests/backend_test.py`) covering Auth, RBAC, Products CRUD, Suppliers approve, Customers, Warehouses, Inventory filters/adjust/negative-guard, PO→GRN lifecycle, SO FEFO allocate+dispatch (incl. insufficient-stock rejection), Dashboard, Advertising, Audit.
- Frontend: Login→Dashboard flow verified; all 10 pages render; Products/POs/SOs/Advertising/Inventory data visible.
- Fixed during testing: `AuditLog.details` JSON column rejecting Decimal — `helpers._jsonable()` now sanitises Decimal/date before persistence.

## Prioritised backlog
### P0 — Finish Phase 1 polish
- Replace `count(*)+1` numbering (SKU/PO/GRN/SO/supplier codes) with race-safe DB sequences.
- Convert `@app.on_event` → FastAPI lifespan + add Alembic for migrations before production.

### P1 — Modules 6-9 (next sessions)
- Manufacturing: BOM, formulations, work orders, batch-level production.
- Quality: inspection plans, test results, CoA attachments, batch release / recall workflows.
- Finance: double-entry journals, invoices, payments, GST configuration, financial statements.
- Logistics: pick-list, delivery challan, shipment, PoD attachments, courier tracking.

### P2 — Modules 10-14
- E-commerce connectors (Shopify / WooCommerce webhooks).
- Advertising OAuth connectors (Meta, Google, LinkedIn, TikTok, Amazon) with real token storage.
- Customer retention (loyalty, discount codes).
- HR / payroll stubs.
- Reports & BI exports (CSV / PDF).

## File map
```
/app/backend
├── server.py             FastAPI entry, router mount, startup seed
├── database.py           SQLAlchemy engine + session
├── models.py             All ORM entities (23 tables)
├── schemas.py            Pydantic DTOs
├── auth.py               JWT, bcrypt, ROLE_PERMISSIONS, require_permission()
├── helpers.py            audit log + json sanitiser
├── seed.py               Demo data for Phase 1 showcase
└── routers/
    ├── auth_router.py           /api/auth/*
    ├── users_router.py          /api/users, /api/roles
    ├── products_router.py       /api/products, /api/product-categories
    ├── suppliers_router.py      /api/suppliers
    ├── customers_router.py      /api/customers
    ├── inventory_router.py      /api/warehouses, /api/inventory/*
    ├── purchase_router.py       /api/purchase-orders, /api/goods-receipts
    ├── sales_router.py          /api/sales-orders (incl. FEFO)
    ├── advertising_router.py    /api/advertising/*
    └── dashboard_router.py      /api/dashboard, /api/audit-logs

/app/frontend/src
├── App.js                routing + QueryClient + AuthProvider
├── index.css             forest-green theme, Chivo + IBM Plex fonts
├── lib/
│   ├── api.js            axios client + endpoints map
│   ├── auth.jsx          AuthProvider + useAuth
│   └── format.js         currency/date/status helpers
├── components/
│   ├── Layout.jsx        Sidebar + Topbar + main
│   └── UI.jsx            PageHeader, Card, DataTable, Modal, Button, StatusBadge, etc.
└── pages/
    ├── Login.jsx
    ├── Dashboard.jsx
    ├── Products.jsx, Suppliers.jsx, Customers.jsx
    ├── Warehouses.jsx, Inventory.jsx
    ├── PurchaseOrders.jsx, SalesOrders.jsx
    ├── Advertising.jsx, Users.jsx, Audit.jsx
```

---

## Phase 2 — Finance module (Oct 2026)

Shipped: Chart of Accounts, double-entry journal engine, AR invoices from Sales Orders, AP bills from Goods Receipts, Payments (receipts / disbursements), finance reports.

### New endpoints
```
GET  /api/finance/accounts              # 17 system accounts auto-seeded
POST /api/finance/accounts
GET  /api/finance/accounts/balances
GET  /api/finance/invoices              # ?invoice_type=CUSTOMER|SUPPLIER
GET  /api/finance/invoices/{id}
POST /api/finance/invoices/from-sales-order
POST /api/finance/invoices/from-grn
POST /api/finance/invoices/{id}/cancel  # reverses journal
GET  /api/finance/payments
POST /api/finance/payments              # auto-infers direction from invoice
GET  /api/finance/journal-entries
POST /api/finance/journal-entries       # manual balanced entry
GET  /api/finance/reports/trial-balance
GET  /api/finance/reports/profit-loss
GET  /api/finance/reports/ar-aging
GET  /api/finance/reports/ap-aging
```

### Posting rules
| Transaction | Journal |
|---|---|
| Customer invoice (from SO) | Dr AR, Cr Sales Revenue, Cr GST Output; **plus** Dr COGS, Cr Inventory (using allocated-batch cost) |
| Supplier bill (from GRN) | Dr Inventory, Dr GST Input, Cr AP |
| Receipt (customer pays) | Dr Bank/Cash, Cr AR |
| Payment (we pay supplier) | Dr AP, Cr Bank/Cash |
| Invoice cancel | Reverses the original entry (sets `is_reversed=true` + new REVERSAL journal entry) |

Every posting is validated: `sum(debits) == sum(credits)` (±1 paisa).

### Frontend
- `/invoices` with Customer / Supplier tabs, detail modal, inline "Record receipt / payment" that posts a payment and updates the invoice status.
- `/payments` list with direction filter.
- `/journal` list + detail modal showing the balanced line breakdown.
- `/finance-reports` with 4 tabs: Trial Balance (shows "Balanced" indicator), P&L (Income/Expenses/Net card), AR Aging, AP Aging (bucketed Current / 1-30 / 31-60 / 61-90 / >90).
- Sales Orders page: `Generate invoice` action on DISPATCHED rows.
- Purchase Orders page: new `Goods Receipts` tab with `Create supplier bill` action.

### Testing status
- 20/20 Phase 2 finance tests pass (`/app/backend/tests/test_finance.py`).
- 24/24 Phase 1 tests still green.
- Live-system check: Trial Balance balances to the paisa; P&L correctly computes Net profit = Sales - COGS (₹749 after seed demo postings).

### Backlog carried forward
- `count(*)+1` numbering debt (SKU/PO/GRN/SO/INV/BILL/PAY/JE) → race-safe DB sequences.
- Alembic migrations before Phase 3.
- Decimal `.quantize(0.01)` throughout for tax rounding safety on very large invoices.

---

## Phase 2.1 — Printable PDF Invoices (Oct 2026)

### Shipped
- **One-click PDF generation** for both customer invoices (TAX INVOICE) and supplier bills (PURCHASE BILL).
- Professional A4 GST-style layout: company header with GSTIN + FSSAI, forest-green TAX INVOICE title bar, bill-to / ship-to blocks, line items table with HSN/qty/rate/disc/tax/amount, auto-split CGST+SGST, totals block, **amount in words (Indian numbering)**, paid vs balance due, terms & conditions, authorised signatory block.
- Uses `reportlab==4.2.5` + `num2words==0.5.14` (pure-Python, no native deps).

### Endpoint
```
GET /api/finance/invoices/{invoice_id}/pdf   → application/pdf stream
```
Requires `finance:read`. Returns 404 for missing invoice, 403 for unauthorised user.

### UI
- Invoice list rows: inline **Printer** (preview in new tab) + **Download** (save as `INV-YYYY-NNNNN.pdf`) icons on every row.
- Invoice detail modal: **Preview PDF** and **Download** buttons alongside Record receipt / Cancel actions.
- All actions use fetch + Blob + object-URL so the authenticated token is included.

### Verified
- Backend: Admin (200), sales rep (403), missing invoice (404), supplier bill (200, 1-page valid PDF).
- Frontend: Modal captured showing 4 action buttons; row-level icon buttons rendered on every invoice.
