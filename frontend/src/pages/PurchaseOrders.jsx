import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, CheckCircle2, XCircle, PackageCheck, ShoppingCart } from "lucide-react";
import { PageHeader, Card, Button, Input, Select, Label, Modal, DataTable, StatusBadge, EmptyState, Textarea } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtDate, fmtNumber } from "../lib/format";
import { useAuth } from "../lib/auth";

const PurchaseOrders = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [tab, setTab] = useState("POS");
    const [status, setStatus] = useState("");
    const [open, setOpen] = useState(false);
    const [grnOpen, setGrnOpen] = useState(false);
    const [selectedPo, setSelectedPo] = useState(null);
    const [detailOpen, setDetailOpen] = useState(false);
    const [form, setForm] = useState({ supplier_id: "", warehouse_id: "", expected_delivery_date: "", notes: "", lines: [{ product_id: "", quantity: 1, unit_price: 0, tax_rate: 18 }] });
    const [grnForm, setGrnForm] = useState({ received_date: new Date().toISOString().slice(0, 10), notes: "", lines: [] });

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["pos", status],
        queryFn: async () => (await endpoints.purchase.list({ status: status || undefined })).data,
    });
    const { data: grns = [], isLoading: grnLoading } = useQuery({
        queryKey: ["grns"],
        queryFn: async () => (await endpoints.purchase.grns()).data,
        enabled: tab === "GRNS",
    });
    const billFromGrn = useMutation({
        mutationFn: (grn_id) => endpoints.finance.invoiceFromGRN({ goods_receipt_id: grn_id }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["grns"] }); qc.invalidateQueries({ queryKey: ["invoices"] }); },
    });
    const { data: suppliers = [] } = useQuery({ queryKey: ["suppliers-list"], queryFn: async () => (await endpoints.suppliers.list({ is_approved: true })).data });
    const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: async () => (await endpoints.warehouses.list()).data });
    const { data: products = [] } = useQuery({ queryKey: ["products-list"], queryFn: async () => (await endpoints.products.list({ status: "ACTIVE" })).data });

    const totals = useMemo(() => {
        const sub = form.lines.reduce((a, l) => a + Number(l.quantity || 0) * Number(l.unit_price || 0), 0);
        const tax = form.lines.reduce((a, l) => a + Number(l.quantity || 0) * Number(l.unit_price || 0) * Number(l.tax_rate || 0) / 100, 0);
        return { sub, tax, total: sub + tax };
    }, [form.lines]);

    const create = useMutation({
        mutationFn: async () => {
            const payload = {
                ...form,
                expected_delivery_date: form.expected_delivery_date || null,
                lines: form.lines.map((l) => ({ product_id: l.product_id, quantity: Number(l.quantity), unit_price: Number(l.unit_price), tax_rate: Number(l.tax_rate) })),
            };
            return endpoints.purchase.create(payload);
        },
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["pos"] }); setOpen(false); setForm({ supplier_id: "", warehouse_id: "", expected_delivery_date: "", notes: "", lines: [{ product_id: "", quantity: 1, unit_price: 0, tax_rate: 18 }] }); },
    });

    const approve = useMutation({ mutationFn: (id) => endpoints.purchase.approve(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["pos"] }) });
    const cancel = useMutation({ mutationFn: (id) => endpoints.purchase.cancel(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["pos"] }) });

    const openDetail = async (po) => {
        const { data } = await endpoints.purchase.get(po.id);
        setSelectedPo(data);
        setDetailOpen(true);
    };

    const openGrn = async (po) => {
        const { data } = await endpoints.purchase.get(po.id);
        setSelectedPo(data);
        setGrnForm({
            received_date: new Date().toISOString().slice(0, 10),
            notes: "",
            lines: data.lines.filter((l) => Number(l.quantity) > Number(l.received_quantity)).map((l) => ({
                po_line_id: l.id,
                product_name: l.product_name,
                product_sku: l.product_sku,
                ordered: Number(l.quantity),
                received_already: Number(l.received_quantity),
                remaining: Number(l.quantity) - Number(l.received_quantity),
                quantity: Number(l.quantity) - Number(l.received_quantity),
                batch_number: `B${Date.now().toString().slice(-6)}${l.product_sku?.slice(-3) || ""}`,
                manufacture_date: new Date().toISOString().slice(0, 10),
                expiry_date: new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10),
                unit_cost: l.unit_price,
            })),
        });
        setGrnOpen(true);
    };

    const submitGrn = useMutation({
        mutationFn: async () => endpoints.purchase.createGrn({
            purchase_order_id: selectedPo.id,
            received_date: grnForm.received_date,
            notes: grnForm.notes,
            lines: grnForm.lines.filter((l) => Number(l.quantity) > 0).map((l) => ({
                po_line_id: l.po_line_id,
                quantity: Number(l.quantity),
                batch_number: l.batch_number,
                manufacture_date: l.manufacture_date || null,
                expiry_date: l.expiry_date || null,
                unit_cost: Number(l.unit_cost),
            })),
        }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["pos"] }); qc.invalidateQueries({ queryKey: ["batches"] }); setGrnOpen(false); },
    });

    const addLine = () => setForm({ ...form, lines: [...form.lines, { product_id: "", quantity: 1, unit_price: 0, tax_rate: 18 }] });
    const removeLine = (i) => setForm({ ...form, lines: form.lines.filter((_, idx) => idx !== i) });
    const updateLine = (i, k, v) => {
        const lines = [...form.lines];
        lines[i] = { ...lines[i], [k]: v };
        if (k === "product_id") {
            const p = products.find((x) => x.id === v);
            if (p) { lines[i].unit_price = Number(p.purchase_price || 0); lines[i].tax_rate = Number(p.tax_rate || 18); }
        }
        setForm({ ...form, lines });
    };

    const columns = [
        { key: "po_number", label: "PO#", render: (r) => <button data-testid={`view-po-${r.id}`} className="font-mono text-xs text-forest-700 hover:underline" onClick={() => openDetail(r)}>{r.po_number}</button> },
        { key: "supplier", label: "Supplier", render: (r) => <span className="text-xs font-medium text-slate-900">{r.supplier_name}</span> },
        { key: "wh", label: "Warehouse", render: (r) => <span className="text-xs">{r.warehouse_name}</span> },
        { key: "date", label: "Order date", render: (r) => <span className="text-xs">{fmtDate(r.order_date)}</span> },
        { key: "total", label: "Total", render: (r) => <span className="tabular-nums font-semibold text-sm">{fmtCurrency(r.total)}</span> },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
        {
            key: "actions", label: "", render: (r) => (
                <div className="flex gap-2 justify-end">
                    {r.status === "PENDING_APPROVAL" && hasPermission("purchase:approve") && (
                        <>
                            <button data-testid={`approve-po-${r.id}`} className="text-xs text-forest-700 hover:underline" onClick={() => approve.mutate(r.id)}>Approve</button>
                            <button data-testid={`cancel-po-${r.id}`} className="text-xs text-rose-600 hover:underline" onClick={() => cancel.mutate(r.id)}>Cancel</button>
                        </>
                    )}
                    {(r.status === "APPROVED" || r.status === "PARTIALLY_RECEIVED") && hasPermission("purchase:receive") && (
                        <button data-testid={`receive-po-${r.id}`} className="text-xs text-forest-700 hover:underline" onClick={() => openGrn(r)}>Receive (GRN)</button>
                    )}
                </div>
            )
        },
    ];

    return (
        <div data-testid="purchase-orders-page">
            <PageHeader title="Purchase orders"
                description="Requisition → approval → PO → goods receipt. Fully auditable procurement."
                breadcrumbs={[{ label: "Operations" }, { label: "Purchase orders" }]}
                actions={hasPermission("purchase:write") && <Button data-testid="new-po-btn" onClick={() => setOpen(true)}><Plus className="w-4 h-4" /> New PO</Button>} />

            <div className="flex items-center gap-2 mb-4 border-b border-slate-200">
                <button data-testid="tab-POS" onClick={() => setTab("POS")} className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 ${tab === "POS" ? "border-forest-700 text-forest-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}>Purchase Orders</button>
                <button data-testid="tab-GRNS" onClick={() => setTab("GRNS")} className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 ${tab === "GRNS" ? "border-forest-700 text-forest-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}>Goods Receipts</button>
            </div>

            {tab === "POS" ? (
            <>
            <Card className="mb-4">
                <div className="p-4 flex gap-3 items-end">
                    <div className="w-56"><Label>Status</Label>
                        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
                            <option value="">All</option>
                            <option value="PENDING_APPROVAL">Pending approval</option>
                            <option value="APPROVED">Approved</option>
                            <option value="PARTIALLY_RECEIVED">Partially received</option>
                            <option value="RECEIVED">Received</option>
                            <option value="CANCELLED">Cancelled</option>
                        </Select></div>
                </div>
            </Card>

            <Card>
                <DataTable testId="pos-table" columns={columns} rows={rows} loading={isLoading} empty={<EmptyState icon={ShoppingCart} title="No purchase orders yet" />} />
            </Card>
            </>
            ) : (
            <Card>
                <DataTable testId="grns-table"
                    columns={[
                        { key: "grn_number", label: "GRN#", render: (r) => <span className="font-mono text-xs text-slate-900">{r.grn_number}</span> },
                        { key: "po", label: "Against PO", render: (r) => <span className="font-mono text-xs">{r.po_number}</span> },
                        { key: "supplier", label: "Supplier", render: (r) => <span className="text-xs font-medium">{r.supplier_name}</span> },
                        { key: "date", label: "Received", render: (r) => <span className="text-xs">{fmtDate(r.received_date)}</span> },
                        { key: "lines", label: "Lines", render: (r) => <span className="text-xs tabular-nums">{r.line_count}</span> },
                        { key: "actions", label: "", render: (r) => hasPermission("finance:write") && (
                            <button data-testid={`bill-grn-${r.id}`} className="text-xs text-forest-700 hover:underline"
                                onClick={() => billFromGrn.mutate(r.id)}>Create supplier bill</button>
                        ) },
                    ]}
                    rows={grns} loading={grnLoading}
                    empty={<EmptyState icon={PackageCheck} title="No goods receipts yet" description="Receive items against an approved PO to create a GRN." />} />
                {billFromGrn.isError && <div className="p-3 text-xs text-rose-700">{billFromGrn.error?.response?.data?.detail}</div>}
            </Card>
            )}

            {/* Create PO modal */}
            <Modal open={open} onClose={() => setOpen(false)} title="New purchase order" size="xl">
                <div className="grid grid-cols-3 gap-3 mb-4">
                    <div><Label required>Supplier</Label>
                        <Select data-testid="po-supplier" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
                            <option value="">—</option>
                            {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </Select></div>
                    <div><Label required>Warehouse</Label>
                        <Select data-testid="po-warehouse" value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}>
                            <option value="">—</option>
                            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </Select></div>
                    <div><Label>Expected delivery</Label>
                        <Input type="date" value={form.expected_delivery_date} onChange={(e) => setForm({ ...form, expected_delivery_date: e.target.value })} /></div>
                </div>

                <div className="border border-slate-200 rounded-md overflow-hidden mb-3">
                    <table className="min-w-full text-sm">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="text-left px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Product</th>
                                <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase w-24">Qty</th>
                                <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase w-28">Unit price</th>
                                <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase w-20">Tax %</th>
                                <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase w-28">Line total</th>
                                <th className="w-8"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {form.lines.map((ln, i) => {
                                const sub = Number(ln.quantity || 0) * Number(ln.unit_price || 0);
                                const total = sub + sub * Number(ln.tax_rate || 0) / 100;
                                return (
                                    <tr key={i}>
                                        <td className="p-1">
                                            <Select data-testid={`po-line-product-${i}`} value={ln.product_id} onChange={(e) => updateLine(i, "product_id", e.target.value)}>
                                                <option value="">—</option>
                                                {products.map((p) => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
                                            </Select>
                                        </td>
                                        <td className="p-1"><Input type="number" step="0.01" value={ln.quantity} onChange={(e) => updateLine(i, "quantity", e.target.value)} className="text-right" /></td>
                                        <td className="p-1"><Input type="number" step="0.01" value={ln.unit_price} onChange={(e) => updateLine(i, "unit_price", e.target.value)} className="text-right" /></td>
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
                <Button data-testid="po-add-line" size="sm" variant="outline" onClick={addLine}><Plus className="w-3 h-3" /> Add line</Button>

                <div className="mt-4 flex justify-end gap-6 text-sm">
                    <div className="text-right">
                        <div className="text-xs text-slate-500">Subtotal</div>
                        <div className="font-semibold tabular-nums">{fmtCurrency(totals.sub)}</div>
                    </div>
                    <div className="text-right">
                        <div className="text-xs text-slate-500">Tax</div>
                        <div className="font-semibold tabular-nums">{fmtCurrency(totals.tax)}</div>
                    </div>
                    <div className="text-right">
                        <div className="text-xs text-slate-500">Total</div>
                        <div className="font-heading font-bold text-xl text-forest-700 tabular-nums">{fmtCurrency(totals.total)}</div>
                    </div>
                </div>

                <div className="mt-3"><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>

                {create.isError && <div className="mt-3 text-sm text-rose-700">{create.error?.response?.data?.detail}</div>}

                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="po-submit" onClick={() => create.mutate()} disabled={!form.supplier_id || !form.warehouse_id || form.lines.some((l) => !l.product_id) || create.isPending}>
                        {create.isPending ? "Creating..." : "Submit for approval"}
                    </Button>
                </div>
            </Modal>

            {/* GRN modal */}
            <Modal open={grnOpen} onClose={() => setGrnOpen(false)} title={`Goods receipt • ${selectedPo?.po_number}`} size="xl">
                {selectedPo && (
                    <>
                        <div className="grid grid-cols-2 gap-3 mb-4">
                            <div><Label required>Received date</Label>
                                <Input type="date" value={grnForm.received_date} onChange={(e) => setGrnForm({ ...grnForm, received_date: e.target.value })} /></div>
                            <div><Label>Notes</Label>
                                <Input value={grnForm.notes} onChange={(e) => setGrnForm({ ...grnForm, notes: e.target.value })} /></div>
                        </div>
                        <div className="border border-slate-200 rounded-md overflow-hidden">
                            <table className="min-w-full text-sm">
                                <thead className="bg-slate-50">
                                    <tr>
                                        <th className="text-left px-3 py-2 text-[11px] font-semibold uppercase text-slate-500">Product</th>
                                        <th className="text-right px-3 py-2 text-[11px] font-semibold uppercase text-slate-500">Order / Done / Remain</th>
                                        <th className="text-right px-3 py-2 text-[11px] font-semibold uppercase text-slate-500">Receive now</th>
                                        <th className="text-left px-3 py-2 text-[11px] font-semibold uppercase text-slate-500">Batch#</th>
                                        <th className="text-left px-3 py-2 text-[11px] font-semibold uppercase text-slate-500">Mfg</th>
                                        <th className="text-left px-3 py-2 text-[11px] font-semibold uppercase text-slate-500">Expiry</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {grnForm.lines.map((ln, i) => (
                                        <tr key={i}>
                                            <td className="px-3 py-2"><div className="text-xs font-medium">{ln.product_name}</div><div className="text-[10px] text-slate-500 font-mono">{ln.product_sku}</div></td>
                                            <td className="px-3 py-2 text-right text-xs tabular-nums">{fmtNumber(ln.ordered)} / {fmtNumber(ln.received_already)} / <strong>{fmtNumber(ln.remaining)}</strong></td>
                                            <td className="p-1"><Input type="number" step="0.01" value={ln.quantity} onChange={(e) => { const l = [...grnForm.lines]; l[i].quantity = e.target.value; setGrnForm({ ...grnForm, lines: l }); }} className="text-right" /></td>
                                            <td className="p-1"><Input value={ln.batch_number} onChange={(e) => { const l = [...grnForm.lines]; l[i].batch_number = e.target.value; setGrnForm({ ...grnForm, lines: l }); }} /></td>
                                            <td className="p-1"><Input type="date" value={ln.manufacture_date} onChange={(e) => { const l = [...grnForm.lines]; l[i].manufacture_date = e.target.value; setGrnForm({ ...grnForm, lines: l }); }} /></td>
                                            <td className="p-1"><Input type="date" value={ln.expiry_date} onChange={(e) => { const l = [...grnForm.lines]; l[i].expiry_date = e.target.value; setGrnForm({ ...grnForm, lines: l }); }} /></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {submitGrn.isError && <div className="mt-3 text-sm text-rose-700">{submitGrn.error?.response?.data?.detail}</div>}
                        <div className="mt-5 flex justify-end gap-2">
                            <Button variant="outline" onClick={() => setGrnOpen(false)}>Cancel</Button>
                            <Button data-testid="grn-submit" onClick={() => submitGrn.mutate()} disabled={submitGrn.isPending}>
                                {submitGrn.isPending ? "Receiving..." : "Confirm goods receipt"}
                            </Button>
                        </div>
                    </>
                )}
            </Modal>

            {/* Detail modal */}
            <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`Purchase order • ${selectedPo?.po_number}`} size="xl">
                {selectedPo && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-4 gap-3 text-sm">
                            <div><div className="text-[10px] uppercase text-slate-500">Supplier</div><div className="font-medium">{selectedPo.supplier_name}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Warehouse</div><div>{selectedPo.warehouse_name}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Order date</div><div>{fmtDate(selectedPo.order_date)}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Status</div><StatusBadge status={selectedPo.status} /></div>
                        </div>
                        <table className="min-w-full text-sm border border-slate-200 rounded-md">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="text-left px-3 py-2 text-xs uppercase text-slate-500">Product</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Qty</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Received</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Unit</th>
                                    <th className="text-right px-3 py-2 text-xs uppercase text-slate-500">Total</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {selectedPo.lines.map((l) => (
                                    <tr key={l.id}>
                                        <td className="px-3 py-2"><div className="font-medium">{l.product_name}</div><div className="text-[10px] text-slate-500 font-mono">{l.product_sku}</div></td>
                                        <td className="px-3 py-2 text-right tabular-nums">{fmtNumber(l.quantity)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums text-emerald-700">{fmtNumber(l.received_quantity)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums">{fmtCurrency(l.unit_price)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums font-semibold">{fmtCurrency(l.line_total)}</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-slate-50">
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-slate-500">Subtotal</td><td className="text-right px-3 py-2 tabular-nums">{fmtCurrency(selectedPo.subtotal)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-slate-500">Tax</td><td className="text-right px-3 py-2 tabular-nums">{fmtCurrency(selectedPo.tax_amount)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 font-semibold">Total</td><td className="text-right px-3 py-2 tabular-nums font-heading font-bold text-forest-700">{fmtCurrency(selectedPo.total)}</td></tr>
                            </tfoot>
                        </table>
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default PurchaseOrders;
