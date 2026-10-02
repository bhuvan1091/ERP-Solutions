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
