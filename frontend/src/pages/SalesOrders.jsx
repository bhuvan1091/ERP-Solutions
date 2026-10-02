import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, ClipboardList, PackageSearch, Send } from "lucide-react";
import { PageHeader, Card, Button, Input, Select, Label, Modal, DataTable, StatusBadge, EmptyState, Textarea } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtDate, fmtNumber } from "../lib/format";
import { useAuth } from "../lib/auth";

const EMPTY_FORM = { customer_id: "", warehouse_id: "", expected_dispatch_date: "", source_channel: "DIRECT", utm_source: "", utm_medium: "", utm_campaign: "", notes: "", lines: [{ product_id: "", quantity: 1, unit_price: 0, tax_rate: 18, discount: 0 }] };

const SalesOrders = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [status, setStatus] = useState("");
    const [open, setOpen] = useState(false);
    const [detailOpen, setDetailOpen] = useState(false);
    const [selected, setSelected] = useState(null);
    const [form, setForm] = useState(EMPTY_FORM);

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["sos", status],
        queryFn: async () => (await endpoints.sales.list({ status: status || undefined })).data,
    });
    const { data: customers = [] } = useQuery({ queryKey: ["customers-list"], queryFn: async () => (await endpoints.customers.list()).data });
    const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: async () => (await endpoints.warehouses.list()).data });
    const { data: products = [] } = useQuery({ queryKey: ["products-list-sales"], queryFn: async () => (await endpoints.products.list({ status: "ACTIVE" })).data });

    const totals = useMemo(() => {
        const sub = form.lines.reduce((a, l) => a + Number(l.quantity || 0) * Number(l.unit_price || 0) - Number(l.discount || 0), 0);
        const tax = form.lines.reduce((a, l) => a + (Number(l.quantity || 0) * Number(l.unit_price || 0) - Number(l.discount || 0)) * Number(l.tax_rate || 0) / 100, 0);
        return { sub, tax, total: sub + tax };
    }, [form.lines]);

    const create = useMutation({
        mutationFn: () => endpoints.sales.create({
            ...form, expected_dispatch_date: form.expected_dispatch_date || null,
            lines: form.lines.map((l) => ({
                product_id: l.product_id, quantity: Number(l.quantity),
                unit_price: Number(l.unit_price), tax_rate: Number(l.tax_rate), discount: Number(l.discount || 0),
            })),
        }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["sos"] }); setOpen(false); setForm(EMPTY_FORM); },
    });
    const allocate = useMutation({ mutationFn: (id) => endpoints.sales.allocate(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["sos"] }) });
    const dispatch = useMutation({ mutationFn: (id) => endpoints.sales.dispatch(id), onSuccess: () => { qc.invalidateQueries({ queryKey: ["sos"] }); qc.invalidateQueries({ queryKey: ["batches"] }); } });
    const cancel = useMutation({ mutationFn: (id) => endpoints.sales.cancel(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["sos"] }) });

    const addLine = () => setForm({ ...form, lines: [...form.lines, { product_id: "", quantity: 1, unit_price: 0, tax_rate: 18, discount: 0 }] });
    const removeLine = (i) => setForm({ ...form, lines: form.lines.filter((_, idx) => idx !== i) });
    const updateLine = (i, k, v) => {
        const lines = [...form.lines];
        lines[i] = { ...lines[i], [k]: v };
        if (k === "product_id") {
            const p = products.find((x) => x.id === v);
            if (p) { lines[i].unit_price = Number(p.selling_price || 0); lines[i].tax_rate = Number(p.tax_rate || 18); }
        }
        setForm({ ...form, lines });
    };

    const openDetail = async (so) => { const { data } = await endpoints.sales.get(so.id); setSelected(data); setDetailOpen(true); };

    const columns = [
        { key: "so_number", label: "SO#", render: (r) => <button data-testid={`view-so-${r.id}`} className="font-mono text-xs text-forest-700 hover:underline" onClick={() => openDetail(r)}>{r.so_number}</button> },
        { key: "customer", label: "Customer", render: (r) => <span className="text-xs font-medium text-slate-900">{r.customer_name}</span> },
        { key: "channel", label: "Channel", render: (r) => <StatusBadge status="ACTIVE">{r.source_channel}</StatusBadge> },
        { key: "date", label: "Order date", render: (r) => <span className="text-xs">{fmtDate(r.order_date)}</span> },
        { key: "total", label: "Total", render: (r) => <span className="font-semibold text-sm tabular-nums">{fmtCurrency(r.total)}</span> },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
        {
            key: "actions", label: "", render: (r) => (
                <div className="flex gap-2 justify-end">
                    {r.status === "CONFIRMED" && hasPermission("sales:approve") && (
                        <>
                            <button data-testid={`allocate-so-${r.id}`} className="text-xs text-forest-700 hover:underline" onClick={() => allocate.mutate(r.id)}>Allocate (FEFO)</button>
                            <button className="text-xs text-rose-600 hover:underline" onClick={() => cancel.mutate(r.id)}>Cancel</button>
                        </>
                    )}
                    {r.status === "ALLOCATED" && hasPermission("sales:dispatch") && (
                        <button data-testid={`dispatch-so-${r.id}`} className="text-xs text-forest-700 hover:underline" onClick={() => dispatch.mutate(r.id)}>Dispatch</button>
                    )}
                </div>
            )
        },
    ];

    return (
        <div data-testid="sales-orders-page">
            <PageHeader title="Sales orders"
                description="Confirm → FEFO allocation → dispatch. Every unit traced back to its batch."
                breadcrumbs={[{ label: "Operations" }, { label: "Sales orders" }]}
                actions={hasPermission("sales:write") && <Button data-testid="new-so-btn" onClick={() => setOpen(true)}><Plus className="w-4 h-4" /> New SO</Button>} />

            <Card className="mb-4"><div className="p-4 flex gap-3 items-end">
                <div className="w-56"><Label>Status</Label>
                    <Select value={status} onChange={(e) => setStatus(e.target.value)}>
                        <option value="">All</option>
                        <option value="CONFIRMED">Confirmed</option>
                        <option value="ALLOCATED">Allocated</option>
                        <option value="DISPATCHED">Dispatched</option>
                        <option value="CANCELLED">Cancelled</option>
                    </Select></div>
            </div></Card>

            <Card>
                <DataTable testId="sos-table" columns={columns} rows={rows} loading={isLoading} empty={<EmptyState icon={ClipboardList} title="No sales orders yet" />} />
            </Card>

            {/* Create modal */}
            <Modal open={open} onClose={() => setOpen(false)} title="New sales order" size="xl">
                <div className="grid grid-cols-3 gap-3 mb-4">
                    <div><Label required>Customer</Label>
                        <Select data-testid="so-customer" value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
                            <option value="">—</option>
                            {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </Select></div>
                    <div><Label required>Warehouse</Label>
                        <Select data-testid="so-warehouse" value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}>
                            <option value="">—</option>
                            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </Select></div>
                    <div><Label>Expected dispatch</Label>
                        <Input type="date" value={form.expected_dispatch_date} onChange={(e) => setForm({ ...form, expected_dispatch_date: e.target.value })} /></div>
                    <div><Label>Source channel</Label>
                        <Select value={form.source_channel} onChange={(e) => setForm({ ...form, source_channel: e.target.value })}>
                            <option value="DIRECT">Direct</option>
                            <option value="SHOPIFY">Shopify</option>
                            <option value="WOOCOMMERCE">WooCommerce</option>
                            <option value="META_AD">Meta Ad</option>
                            <option value="GOOGLE_AD">Google Ad</option>
                            <option value="AMAZON">Amazon</option>
                        </Select></div>
                    <div><Label>UTM source</Label><Input value={form.utm_source} onChange={(e) => setForm({ ...form, utm_source: e.target.value })} placeholder="meta" /></div>
                    <div><Label>UTM campaign</Label><Input value={form.utm_campaign} onChange={(e) => setForm({ ...form, utm_campaign: e.target.value })} /></div>
                </div>

                <div className="border border-slate-200 rounded-md overflow-hidden mb-3">
                    <table className="min-w-full text-sm">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="text-left px-3 py-2 text-[11px] uppercase text-slate-500">Product</th>
                                <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500 w-24">Qty</th>
                                <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500 w-28">Unit</th>
                                <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500 w-24">Discount</th>
                                <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500 w-20">Tax %</th>
                                <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500 w-28">Line total</th>
                                <th className="w-8"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {form.lines.map((ln, i) => {
                                const sub = Number(ln.quantity || 0) * Number(ln.unit_price || 0) - Number(ln.discount || 0);
                                const total = sub + sub * Number(ln.tax_rate || 0) / 100;
                                return (
                                    <tr key={i}>
                                        <td className="p-1">
                                            <Select data-testid={`so-line-product-${i}`} value={ln.product_id} onChange={(e) => updateLine(i, "product_id", e.target.value)}>
                                                <option value="">—</option>
                                                {products.map((p) => <option key={p.id} value={p.id}>{p.sku} — {p.name} ({fmtNumber(p.stock_on_hand)} avail)</option>)}
                                            </Select>
                                        </td>
                                        <td className="p-1"><Input type="number" step="0.01" value={ln.quantity} onChange={(e) => updateLine(i, "quantity", e.target.value)} className="text-right" /></td>
                                        <td className="p-1"><Input type="number" step="0.01" value={ln.unit_price} onChange={(e) => updateLine(i, "unit_price", e.target.value)} className="text-right" /></td>
                                        <td className="p-1"><Input type="number" step="0.01" value={ln.discount} onChange={(e) => updateLine(i, "discount", e.target.value)} className="text-right" /></td>
                                        <td className="p-1"><Input type="number" step="0.5" value={ln.tax_rate} onChange={(e) => updateLine(i, "tax_rate", e.target.value)} className="text-right" /></td>
                                        <td className="p-1 text-right tabular-nums text-xs">{fmtCurrency(total)}</td>
                                        <td className="p-1 text-right">
                                            {form.lines.length > 1 && <button className="text-slate-400 hover:text-rose-600 p-1" onClick={() => removeLine(i)}><Trash2 className="w-4 h-4" /></button>}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
                <Button size="sm" variant="outline" onClick={addLine}><Plus className="w-3 h-3" /> Add line</Button>

                <div className="mt-4 flex justify-end gap-6 text-sm">
                    <div className="text-right"><div className="text-xs text-slate-500">Subtotal</div><div className="font-semibold tabular-nums">{fmtCurrency(totals.sub)}</div></div>
                    <div className="text-right"><div className="text-xs text-slate-500">Tax</div><div className="font-semibold tabular-nums">{fmtCurrency(totals.tax)}</div></div>
                    <div className="text-right"><div className="text-xs text-slate-500">Total</div><div className="font-heading font-bold text-xl text-forest-700 tabular-nums">{fmtCurrency(totals.total)}</div></div>
                </div>

                <div className="mt-3"><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>

                {create.isError && <div className="mt-3 text-sm text-rose-700">{create.error?.response?.data?.detail}</div>}

                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="so-submit" onClick={() => create.mutate()}
                        disabled={!form.customer_id || !form.warehouse_id || form.lines.some((l) => !l.product_id) || create.isPending}>
                        {create.isPending ? "Creating..." : "Confirm order"}
                    </Button>
                </div>
            </Modal>

            {/* Detail */}
            <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`Sales order • ${selected?.so_number}`} size="xl">
                {selected && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-4 gap-3 text-sm">
                            <div><div className="text-[10px] uppercase text-slate-500">Customer</div><div className="font-medium">{selected.customer_name}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Warehouse</div><div>{selected.warehouse_name}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Channel</div><div>{selected.source_channel}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Status</div><StatusBadge status={selected.status} /></div>
                        </div>
                        {(selected.utm_source || selected.utm_campaign) && (
                            <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-xs">
                                <strong>Attribution:</strong> {selected.utm_source || "—"} / {selected.utm_campaign || "—"}
                            </div>
                        )}
                        <table className="min-w-full text-sm border border-slate-200 rounded-md">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="text-left px-3 py-2 text-xs uppercase text-slate-500">Product</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Qty</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Dispatched</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Unit</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Total</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {selected.lines.map((l) => (
                                    <tr key={l.id}>
                                        <td className="px-3 py-2"><div className="font-medium">{l.product_name}</div><div className="text-[10px] font-mono text-slate-500">{l.product_sku}</div>{l.allocated_batch_id && <div className="text-[10px] text-forest-700 mt-0.5">Allocated batch #{l.allocated_batch_id.slice(0, 8)}</div>}</td>
                                        <td className="px-3 py-2 text-right tabular-nums">{fmtNumber(l.quantity)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums text-emerald-700">{fmtNumber(l.dispatched_quantity)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums">{fmtCurrency(l.unit_price)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums font-semibold">{fmtCurrency(l.line_total)}</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-slate-50">
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-slate-500">Subtotal</td><td className="text-right px-3 py-2 tabular-nums">{fmtCurrency(selected.subtotal)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-slate-500">Tax</td><td className="text-right px-3 py-2 tabular-nums">{fmtCurrency(selected.tax_amount)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 font-semibold">Total</td><td className="text-right px-3 py-2 tabular-nums font-heading font-bold text-forest-700">{fmtCurrency(selected.total)}</td></tr>
                            </tfoot>
                        </table>
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default SalesOrders;
