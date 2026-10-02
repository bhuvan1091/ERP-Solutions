import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Receipt, FilePlus2, Wallet, Ban, FileDown, Eye } from "lucide-react";
import { PageHeader, Card, CardHeader, DataTable, StatusBadge, EmptyState, Select, Label, Button, Modal, Input, Textarea } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtDate, fmtDateTime, fmtNumber } from "../lib/format";
import { useAuth } from "../lib/auth";

const Invoices = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [tab, setTab] = useState("CUSTOMER");
    const [status, setStatus] = useState("");
    const [detail, setDetail] = useState(null);
    const [payOpen, setPayOpen] = useState(false);
    const [payForm, setPayForm] = useState({ amount: "", method: "BANK", reference: "", payment_date: new Date().toISOString().slice(0, 10) });

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["invoices", tab, status],
        queryFn: async () => (await endpoints.finance.invoices({ invoice_type: tab, status: status || undefined })).data,
    });

    const cancelInv = useMutation({
        mutationFn: (id) => endpoints.finance.cancelInvoice(id),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["invoices"] }); setDetail(null); },
    });

    const createPayment = useMutation({
        mutationFn: () => endpoints.finance.createPayment({
            direction: tab === "CUSTOMER" ? "RECEIPT" : "PAYMENT",
            invoice_id: detail.id,
            amount: Number(payForm.amount),
            method: payForm.method,
            reference: payForm.reference || null,
            payment_date: payForm.payment_date,
        }),
        onSuccess: async () => {
            qc.invalidateQueries({ queryKey: ["invoices"] });
            qc.invalidateQueries({ queryKey: ["payments"] });
            const { data } = await endpoints.finance.getInvoice(detail.id);
            setDetail(data);
            setPayOpen(false);
            setPayForm({ amount: "", method: "BANK", reference: "", payment_date: new Date().toISOString().slice(0, 10) });
        },
    });

    const openDetail = async (id) => {
        const { data } = await endpoints.finance.getInvoice(id);
        setDetail(data);
    };

    const columns = [
        { key: "invoice_number", label: "Invoice#", render: (r) => <button onClick={() => openDetail(r.id)} data-testid={`view-inv-${r.id}`} className="font-mono text-xs text-forest-700 hover:underline">{r.invoice_number}</button> },
        { key: "party", label: tab === "CUSTOMER" ? "Customer" : "Supplier", render: (r) => <span className="text-sm font-medium text-slate-900">{r.customer_name || r.supplier_name}</span> },
        { key: "source", label: "Source", render: (r) => <span className="font-mono text-[11px] text-slate-500">{r.sales_order_number || r.grn_number || r.supplier_bill_reference || "—"}</span> },
        { key: "date", label: "Date", render: (r) => <div className="text-xs"><div>{fmtDate(r.invoice_date)}</div><div className="text-slate-400">Due {fmtDate(r.due_date)}</div></div> },
        { key: "total", label: "Total", render: (r) => <span className="tabular-nums font-semibold text-sm">{fmtCurrency(r.total)}</span> },
        { key: "paid", label: "Paid / Due", render: (r) => <div className="text-xs tabular-nums"><div className="text-emerald-700">{fmtCurrency(r.amount_paid)}</div><div className="text-rose-700">{fmtCurrency(r.amount_due)}</div></div> },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
    ];

    return (
        <div data-testid="invoices-page">
            <PageHeader
                title="Invoices"
                description={tab === "CUSTOMER" ? "Customer invoices (Accounts Receivable). Each posts a double-entry journal and books COGS automatically." : "Supplier bills (Accounts Payable). Created from Goods Receipts; posts Inventory + GST Input against AP."}
                breadcrumbs={[{ label: "Finance" }, { label: "Invoices" }]}
            />

            <div className="flex items-center gap-2 mb-4 border-b border-slate-200">
                <button data-testid="tab-CUSTOMER" onClick={() => setTab("CUSTOMER")} className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 ${tab === "CUSTOMER" ? "border-forest-700 text-forest-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}>Customer Invoices (AR)</button>
                <button data-testid="tab-SUPPLIER" onClick={() => setTab("SUPPLIER")} className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 ${tab === "SUPPLIER" ? "border-forest-700 text-forest-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}>Supplier Bills (AP)</button>
            </div>

            <Card className="mb-4"><div className="p-4 flex gap-3 items-end">
                <div className="w-56"><Label>Status</Label>
                    <Select value={status} onChange={(e) => setStatus(e.target.value)}>
                        <option value="">All</option>
                        <option value="POSTED">Posted</option>
                        <option value="PARTIALLY_PAID">Partially paid</option>
                        <option value="PAID">Paid</option>
                        <option value="CANCELLED">Cancelled</option>
                    </Select></div>
                <div className="text-xs text-slate-500 ml-auto">
                    Tip: Create new invoices from <strong>Sales Orders</strong> (dispatched) or <strong>Goods Receipts</strong>.
                </div>
            </div></Card>

            <Card>
                <DataTable testId="invoices-table" columns={columns} rows={rows} loading={isLoading}
                    empty={<EmptyState icon={Receipt} title={`No ${tab === "CUSTOMER" ? "customer invoices" : "supplier bills"} yet`} description="Generate the first one from the Sales Orders or Goods Receipts page." />} />
            </Card>

            {/* Detail */}
            <Modal open={!!detail} onClose={() => setDetail(null)} title={`Invoice • ${detail?.invoice_number}`} size="xl">
                {detail && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-4 gap-3 text-sm">
                            <div><div className="text-[10px] uppercase text-slate-500">{detail.invoice_type === "CUSTOMER" ? "Customer" : "Supplier"}</div><div className="font-medium">{detail.customer_name || detail.supplier_name}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Source</div><div className="font-mono text-xs">{detail.sales_order_number || detail.grn_number || "—"}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Dates</div><div className="text-xs">{fmtDate(detail.invoice_date)} → due {fmtDate(detail.due_date)}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Status</div><StatusBadge status={detail.status} /></div>
                        </div>

                        <table className="min-w-full text-sm border border-slate-200 rounded-md">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="text-left px-3 py-2 text-[11px] uppercase text-slate-500">Item</th>
                                    <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500">Qty</th>
                                    <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500">Unit</th>
                                    <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500">Tax %</th>
                                    <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500">Line total</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {detail.lines.map((l) => (
                                    <tr key={l.id}>
                                        <td className="px-3 py-2"><div className="font-medium">{l.product_name || l.description}</div><div className="text-[10px] font-mono text-slate-500">{l.product_sku}</div></td>
                                        <td className="px-3 py-2 text-right tabular-nums">{fmtNumber(l.quantity)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums">{fmtCurrency(l.unit_price)}</td>
                                        <td className="px-3 py-2 text-right tabular-nums">{l.tax_rate}%</td>
                                        <td className="px-3 py-2 text-right tabular-nums font-semibold">{fmtCurrency(l.line_total)}</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-slate-50">
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-slate-500">Subtotal</td><td className="text-right px-3 py-2 tabular-nums">{fmtCurrency(detail.subtotal)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-slate-500">Tax</td><td className="text-right px-3 py-2 tabular-nums">{fmtCurrency(detail.tax_amount)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 font-semibold">Total</td><td className="text-right px-3 py-2 tabular-nums font-heading font-bold text-forest-700">{fmtCurrency(detail.total)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-emerald-700">Paid</td><td className="text-right px-3 py-2 tabular-nums text-emerald-700">{fmtCurrency(detail.amount_paid)}</td></tr>
                                <tr><td colSpan={4} className="text-right px-3 py-2 text-xs text-rose-700">Outstanding</td><td className="text-right px-3 py-2 tabular-nums font-semibold text-rose-700">{fmtCurrency(detail.amount_due)}</td></tr>
                            </tfoot>
                        </table>

                        <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-xs flex items-center justify-between">
                            <div>
                                <strong className="text-slate-900">Journal entry:</strong> {detail.journal_entry_id ? <span className="font-mono text-slate-600">{detail.journal_entry_id.slice(0, 8)}...</span> : "—"}
                                {detail.cogs_amount > 0 && <> • <strong>COGS:</strong> <span className="tabular-nums">{fmtCurrency(detail.cogs_amount)}</span></>}
                            </div>
                            <div className="flex gap-2">
                                {detail.status !== "CANCELLED" && detail.status !== "PAID" && hasPermission("finance:write") && (
                                    <Button data-testid="record-payment-btn" size="sm" onClick={() => { setPayForm({ ...payForm, amount: detail.amount_due }); setPayOpen(true); }}>
                                        <Wallet className="w-3.5 h-3.5" /> Record {detail.invoice_type === "CUSTOMER" ? "receipt" : "payment"}
                                    </Button>
                                )}
                                {detail.status === "POSTED" && Number(detail.amount_paid) === 0 && hasPermission("finance:write") && (
                                    <Button variant="danger" size="sm" onClick={() => cancelInv.mutate(detail.id)}>
                                        <Ban className="w-3.5 h-3.5" /> Cancel & reverse
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Payment modal */}
            <Modal open={payOpen} onClose={() => setPayOpen(false)} title={`${tab === "CUSTOMER" ? "Record receipt" : "Record payment"} • ${detail?.invoice_number}`}>
                <div className="space-y-3">
                    <div className="bg-slate-50 rounded-md p-3 text-xs">
                        <div>Invoice total: <strong className="tabular-nums">{fmtCurrency(detail?.total)}</strong></div>
                        <div>Already paid: <strong className="tabular-nums text-emerald-700">{fmtCurrency(detail?.amount_paid)}</strong></div>
                        <div>Outstanding: <strong className="tabular-nums text-rose-700">{fmtCurrency(detail?.amount_due)}</strong></div>
                    </div>
                    <div><Label required>Amount</Label><Input data-testid="payment-amount" type="number" step="0.01" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} /></div>
                    <div><Label required>Method</Label>
                        <Select value={payForm.method} onChange={(e) => setPayForm({ ...payForm, method: e.target.value })}>
                            <option value="BANK">Bank transfer</option><option value="CASH">Cash</option>
                            <option value="UPI">UPI</option><option value="CHEQUE">Cheque</option>
                            <option value="CARD">Card</option>
                        </Select></div>
                    <div><Label>Payment date</Label><Input type="date" value={payForm.payment_date} onChange={(e) => setPayForm({ ...payForm, payment_date: e.target.value })} /></div>
                    <div><Label>Reference (UTR / cheque #)</Label><Input value={payForm.reference} onChange={(e) => setPayForm({ ...payForm, reference: e.target.value })} /></div>
                    {createPayment.isError && <div className="text-sm text-rose-700">{createPayment.error?.response?.data?.detail}</div>}
                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setPayOpen(false)}>Cancel</Button>
                        <Button data-testid="payment-submit" onClick={() => createPayment.mutate()} disabled={!payForm.amount || Number(payForm.amount) <= 0 || createPayment.isPending}>
                            {createPayment.isPending ? "Posting..." : "Post payment"}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
};

export default Invoices;
