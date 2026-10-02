import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Wallet, ArrowDownCircle, ArrowUpCircle } from "lucide-react";
import { PageHeader, Card, DataTable, StatusBadge, EmptyState, Select, Label } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtDate } from "../lib/format";

const Payments = () => {
    const [direction, setDirection] = useState("");
    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["payments", direction],
        queryFn: async () => (await endpoints.finance.payments({ direction: direction || undefined })).data,
    });

    const columns = [
        { key: "payment_number", label: "Payment#", render: (r) => <span className="font-mono text-xs">{r.payment_number}</span> },
        {
            key: "direction", label: "Type", render: (r) => (
                <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-semibold ${r.direction === "RECEIPT" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                    {r.direction === "RECEIPT" ? <ArrowDownCircle className="w-3 h-3" /> : <ArrowUpCircle className="w-3 h-3" />}
                    {r.direction}
                </span>
            )
        },
        { key: "party", label: "Party", render: (r) => <span className="text-sm font-medium text-slate-900">{r.customer_name || r.supplier_name}</span> },
        { key: "invoice", label: "Invoice", render: (r) => <span className="font-mono text-[11px] text-slate-500">{r.invoice_number || "—"}</span> },
        { key: "amount", label: "Amount", render: (r) => <span className="tabular-nums font-semibold text-sm">{fmtCurrency(r.amount)}</span> },
        { key: "method", label: "Method", render: (r) => <span className="text-xs">{r.method}</span> },
        { key: "ref", label: "Reference", render: (r) => <span className="font-mono text-[11px] text-slate-500">{r.reference || "—"}</span> },
        { key: "date", label: "Date", render: (r) => <span className="text-xs">{fmtDate(r.payment_date)}</span> },
    ];

    return (
        <div data-testid="payments-page">
            <PageHeader title="Payments" description="Receipts and payments against invoices. Each posts a balanced double-entry journal to Bank/Cash and AR/AP."
                breadcrumbs={[{ label: "Finance" }, { label: "Payments" }]} />
            <Card className="mb-4"><div className="p-4 flex gap-3 items-end">
                <div className="w-56"><Label>Direction</Label>
                    <Select value={direction} onChange={(e) => setDirection(e.target.value)}>
                        <option value="">All</option>
                        <option value="RECEIPT">Receipts (money in)</option>
                        <option value="PAYMENT">Payments (money out)</option>
                    </Select></div>
            </div></Card>
            <Card>
                <DataTable testId="payments-table" columns={columns} rows={rows} loading={isLoading}
                    empty={<EmptyState icon={Wallet} title="No payments yet" description="Open an invoice and click 'Record receipt / payment' to log the first one." />} />
            </Card>
        </div>
    );
};

export default Payments;
