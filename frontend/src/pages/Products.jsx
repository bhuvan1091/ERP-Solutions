import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Pencil, Package as PkgIcon } from "lucide-react";
import {
    PageHeader, Card, Button, Input, Select, Label, Modal, DataTable, StatusBadge,
    EmptyState, Textarea,
} from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtNumber, fmtDate } from "../lib/format";
import { useAuth } from "../lib/auth";

const EMPTY_FORM = {
    name: "", brand: "", sku: "", barcode: "",
    product_type: "FINISHED_GOOD", status: "ACTIVE",
    unit_of_measure: "unit", pack_size: "", flavour: "",
    purchase_price: 0, selling_price: 0, mrp: 0, tax_rate: 18,
    hsn_code: "", shelf_life_days: 365,
    reorder_level: 0, min_stock: 0, max_stock: 0,
    description: "", ingredients: "", image_url: "",
    category_id: "",
};

const Products = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("");
    const [type, setType] = useState("");
    const [open, setOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(EMPTY_FORM);

    const { data: products = [], isLoading } = useQuery({
        queryKey: ["products", search, status, type],
        queryFn: async () => (await endpoints.products.list({
            search: search || undefined,
            status: status || undefined,
            product_type: type || undefined,
        })).data,
    });

    const { data: cats = [] } = useQuery({
        queryKey: ["categories"],
        queryFn: async () => (await endpoints.categories.list()).data,
    });

    const save = useMutation({
        mutationFn: async () => {
            const payload = { ...form };
            ["purchase_price", "selling_price", "mrp", "tax_rate",
                "reorder_level", "min_stock", "max_stock", "shelf_life_days"].forEach((k) => {
                payload[k] = Number(payload[k] || 0);
            });
            if (!payload.sku) delete payload.sku;
            if (editing) return (await endpoints.products.update(editing.id, payload)).data;
            return (await endpoints.products.create(payload)).data;
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["products"] });
            setOpen(false); setEditing(null); setForm(EMPTY_FORM);
        },
    });

    const openCreate = () => { setEditing(null); setForm(EMPTY_FORM); setOpen(true); };
    const openEdit = (p) => {
        setEditing(p);
        setForm({
            name: p.name || "", brand: p.brand || "", sku: p.sku,
            barcode: p.barcode || "", product_type: p.product_type,
            status: p.status, unit_of_measure: p.unit_of_measure,
            pack_size: p.pack_size || "", flavour: p.flavour || "",
            purchase_price: p.purchase_price, selling_price: p.selling_price,
            mrp: p.mrp, tax_rate: p.tax_rate, hsn_code: p.hsn_code || "",
            shelf_life_days: p.shelf_life_days,
            reorder_level: p.reorder_level, min_stock: p.min_stock, max_stock: p.max_stock,
            description: p.description || "", ingredients: p.ingredients || "",
            image_url: p.image_url || "", category_id: p.category_id || "",
        });
        setOpen(true);
    };

    const columns = [
        {
            key: "sku", label: "SKU / Product",
            render: (r) => (
                <div className="flex items-center gap-3">
                    {r.image_url ? (
                        <img src={r.image_url} alt={r.name} className="w-11 h-11 shrink-0 object-contain rounded-md border border-slate-200 bg-white p-1" />
                    ) : (
                        <div className="w-9 h-9 rounded border border-slate-200 bg-slate-50 flex items-center justify-center"><PkgIcon className="w-4 h-4 text-slate-400" /></div>
                    )}
                    <div>
                        <div className="font-medium text-slate-900">{r.name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{r.sku}{r.brand ? ` • ${r.brand}` : ""}</div>
                    </div>
                </div>
            )
        },
        { key: "type", label: "Type", render: (r) => <span className="text-xs">{r.product_type?.replace("_", " ")}</span> },
        { key: "pack", label: "Pack / UOM", render: (r) => <span className="text-xs">{r.pack_size || "—"} <span className="text-slate-400">({r.unit_of_measure})</span></span> },
        { key: "sell", label: "Price (Sell / MRP)", render: (r) => <div className="tabular-nums"><div>{fmtCurrency(r.selling_price)}</div><div className="text-[10px] text-slate-400">MRP {fmtCurrency(r.mrp)}</div></div> },
        { key: "stock", label: "Stock", render: (r) => <span className={`tabular-nums ${Number(r.stock_on_hand) <= Number(r.reorder_level) && Number(r.reorder_level) > 0 ? "text-rose-700 font-semibold" : "text-slate-700"}`}>{fmtNumber(r.stock_on_hand)}</span> },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
        {
            key: "actions", label: "", render: (r) => hasPermission("product:write") && (
                <button data-testid={`edit-product-${r.id}`} title="Edit product" aria-label={`Edit ${r.name}`} onClick={() => openEdit(r)} className="text-slate-400 hover:text-forest-700 hover:bg-forest-50 rounded-md p-2">
                    <Pencil className="w-4 h-4" />
                </button>
            )
        },
    ];

    return (
        <div data-testid="products-page">
            <PageHeader
                title="Products"
                description="Your product catalog, pricing and stock at a glance."
                breadcrumbs={[{ label: "Catalog" }, { label: "Products" }]}
                actions={hasPermission("product:write") && (
                    <Button data-testid="new-product-btn" onClick={openCreate}><Plus className="w-4 h-4" /> New product</Button>
                )}
            />

            <Card className="mb-4">
                <div className="p-4 flex gap-3 flex-wrap items-end">
                    <div className="flex-1 min-w-56">
                        <Label>Search</Label>
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                            <Input data-testid="product-search" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, SKU, brand..." />
                        </div>
                    </div>
                    <div className="w-40">
                        <Label>Status</Label>
                        <Select data-testid="product-filter-status" value={status} onChange={(e) => setStatus(e.target.value)}>
                            <option value="">All</option>
                            <option value="ACTIVE">Active</option>
                            <option value="DRAFT">Draft</option>
                            <option value="DISCONTINUED">Discontinued</option>
                        </Select>
                    </div>
                    <div className="w-44">
                        <Label>Type</Label>
                        <Select data-testid="product-filter-type" value={type} onChange={(e) => setType(e.target.value)}>
                            <option value="">All</option>
                            <option value="FINISHED_GOOD">Finished goods</option>
                            <option value="RAW_MATERIAL">Raw material</option>
                            <option value="PACKAGING">Packaging</option>
                            <option value="SEMI_FINISHED">Semi-finished</option>
                        </Select>
                    </div>
                </div>
            </Card>

            <Card>
                <DataTable
                    testId="products-table"
                    columns={columns}
                    rows={products}
                    loading={isLoading}
                    empty={<EmptyState title="No products" description="Create your first product to begin managing inventory and sales." icon={PkgIcon} />}
                />
            </Card>

            <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit product" : "New product"} size="xl">
                <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                        <Label required>Name</Label>
                        <Input data-testid="product-form-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                    </div>
                    <div><Label>SKU {editing ? "" : "(auto if blank)"}</Label><Input value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} disabled={!!editing} /></div>
                    <div><Label>Brand</Label><Input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} /></div>
                    <div>
                        <Label>Category</Label>
                        <Select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                            <option value="">—</option>
                            {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </Select>
                    </div>
                    <div>
                        <Label>Type</Label>
                        <Select value={form.product_type} onChange={(e) => setForm({ ...form, product_type: e.target.value })}>
                            <option value="FINISHED_GOOD">Finished goods</option>
                            <option value="RAW_MATERIAL">Raw material</option>
                            <option value="PACKAGING">Packaging</option>
                            <option value="SEMI_FINISHED">Semi-finished</option>
                            <option value="SERVICE">Service</option>
                        </Select>
                    </div>
                    <div><Label>Pack size</Label><Input value={form.pack_size} onChange={(e) => setForm({ ...form, pack_size: e.target.value })} placeholder="e.g. 1kg, 60 caps" /></div>
                    <div>
                        <Label>UOM</Label>
                        <Select value={form.unit_of_measure} onChange={(e) => setForm({ ...form, unit_of_measure: e.target.value })}>
                            <option value="unit">unit</option><option value="kg">kg</option>
                            <option value="g">g</option><option value="L">L</option><option value="ml">ml</option>
                        </Select>
                    </div>
                    <div><Label>Flavour</Label><Input value={form.flavour} onChange={(e) => setForm({ ...form, flavour: e.target.value })} /></div>
                    <div><Label>Purchase price (₹)</Label><Input type="number" step="0.01" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} /></div>
                    <div><Label>Selling price (₹)</Label><Input type="number" step="0.01" value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} /></div>
                    <div><Label>MRP (₹)</Label><Input type="number" step="0.01" value={form.mrp} onChange={(e) => setForm({ ...form, mrp: e.target.value })} /></div>
                    <div><Label>GST %</Label><Input type="number" step="0.5" value={form.tax_rate} onChange={(e) => setForm({ ...form, tax_rate: e.target.value })} /></div>
                    <div><Label>HSN code</Label><Input value={form.hsn_code} onChange={(e) => setForm({ ...form, hsn_code: e.target.value })} /></div>
                    <div><Label>Shelf life (days)</Label><Input type="number" value={form.shelf_life_days} onChange={(e) => setForm({ ...form, shelf_life_days: e.target.value })} /></div>
                    <div><Label>Reorder level</Label><Input type="number" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: e.target.value })} /></div>
                    <div><Label>Min stock</Label><Input type="number" value={form.min_stock} onChange={(e) => setForm({ ...form, min_stock: e.target.value })} /></div>
                    <div><Label>Max stock</Label><Input type="number" value={form.max_stock} onChange={(e) => setForm({ ...form, max_stock: e.target.value })} /></div>
                    <div className="col-span-2"><Label>Image URL</Label><Input value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} /></div>
                    <div className="col-span-2"><Label>Description</Label><Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
                    <div className="col-span-2"><Label>Ingredients</Label><Textarea rows={2} value={form.ingredients} onChange={(e) => setForm({ ...form, ingredients: e.target.value })} /></div>
                </div>
                {save.isError && <div className="mt-3 text-sm text-rose-700">{save.error?.response?.data?.detail || "Save failed"}</div>}
                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="product-form-save" onClick={() => save.mutate()} disabled={!form.name || save.isPending}>{save.isPending ? "Saving..." : (editing ? "Save changes" : "Create product")}</Button>
                </div>
            </Modal>
        </div>
    );
};

export default Products;
