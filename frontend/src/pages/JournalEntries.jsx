import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Scale } from "lucide-react";
import { PageHeader, Card, DataTable, StatusBadge, EmptyState, Select, Label, Modal } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtDate } from "../lib/format";

const JournalEntries = () => {
    const [refType, setRefType] = useState("");
    const [detail, setDetail] = useState(null);

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["journal", refType],
        queryFn: async () => (await endpoints.finance.journalEntries({ reference_type: refType || undefined, limit: 200 })).data,
    });

    const columns = [
        { key: "entry_number", label: "JE#", render: (r) => <button onClick={() => setDetail(r)} className="font-mono text-xs text-forest-700 hover:underline">{r.entry_number}</button> },
        { key: "date", label: "Date", render: (r) => <span className="text-xs">{fmtDate(r.entry_date)}</span> },
        { key: "ref", label: "Reference", render: (r) => <div className="text-xs"><div>{r.reference_type}</div><div className="font-mono text-slate-500">{r.reference_number || "—"}</div></div> },
        { key: "narration", label: "Narration", render: (r) => <span className="text-xs text-slate-700 line-clamp-1">{r.narration}</span> },
        { key: "dr", label: "Debit", render: (r) => <span className="tabular-nums text-sm">{fmtCurrency(r.total_debit)}</span> },
        { key: "cr", label: "Credit", render: (r) => <span className="tabular-nums text-sm">{fmtCurrency(r.total_credit)}</span> },
        {
            key: "status", label: "Status",
            render: (r) => (
                <div className="flex items-center gap-1">
                    <Scale className={`w-3.5 h-3.5 ${Math.abs(Number(r.total_debit) - Number(r.total_credit)) < 0.01 ? "text-emerald-600" : "text-rose-600"}`} />
                    {r.is_reversed && <StatusBadge status="CANCELLED">Reversed</StatusBadge>}
                </div>
            )
        },
    ];

    return (
        <div data-testid="journal-page">
            <PageHeader title="Journal entries"
                description="Immutable ledger of every balanced posting across the ERP."
                breadcrumbs={[{ label: "Finance" }, { label: "Journal entries" }]} />
            <Card className="mb-4"><div className="p-4 flex gap-3 items-end">
                <div className="w-56"><Label>Source</Label>
                    <Select value={refType} onChange={(e) => setRefType(e.target.value)}>
                        <option value="">All</option>
                        <option value="INVOICE">Invoice</option>
                        <option value="PAYMENT">Payment</option>
                        <option value="MANUAL">Manual</option>
                        <option value="REVERSAL">Reversal</option>
                    </Select></div>
            </div></Card>
            <Card>
                <DataTable testId="journal-table" columns={columns} rows={rows} loading={isLoading}
                    empty={<EmptyState icon={BookOpen} title="No journal entries yet" />} />
            </Card>

            <Modal open={!!detail} onClose={() => setDetail(null)} title={`Journal entry • ${detail?.entry_number}`} size="lg">
                {detail && (
                    <div>
                        <div className="grid grid-cols-3 gap-3 text-sm mb-4">
                            <div><div className="text-[10px] uppercase text-slate-500">Date</div><div>{fmtDate(detail.entry_date)}</div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Source</div><div className="text-xs">{detail.reference_type} <span className="font-mono text-slate-500">{detail.reference_number}</span></div></div>
                            <div><div className="text-[10px] uppercase text-slate-500">Posted by</div><div className="text-xs font-mono">{detail.posted_by_email || "—"}</div></div>
                        </div>
                        <div className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-md p-3 mb-4">{detail.narration}</div>
                        <table className="min-w-full text-sm border border-slate-200 rounded-md">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="text-left px-3 py-2 text-[11px] uppercase text-slate-500">Account</th>
                                    <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500">Debit</th>
                                    <th className="text-right px-3 py-2 text-[11px] uppercase text-slate-500">Credit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {detail.lines.map((l) => (
                                    <tr key={l.id}>
                                        <td className="px-3 py-2"><div className="font-mono text-xs text-slate-600">{l.account_code}</div><div className="text-sm">{l.account_name}</div>{l.notes && <div className="text-[10px] text-slate-400">{l.notes}</div>}</td>
                                        <td className="px-3 py-2 text-right tabular-nums text-sm">{Number(l.debit) > 0 ? fmtCurrency(l.debit) : <span className="text-slate-300">—</span>}</td>
                                        <td className="px-3 py-2 text-right tabular-nums text-sm">{Number(l.credit) > 0 ? fmtCurrency(l.credit) : <span className="text-slate-300">—</span>}</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-slate-50 font-semibold">
                                <tr>
                                    <td className="px-3 py-2 text-right">Totals</td>
                                    <td className="px-3 py-2 text-right tabular-nums">{fmtCurrency(detail.total_debit)}</td>
                                    <td className="px-3 py-2 text-right tabular-nums">{fmtCurrency(detail.total_credit)}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default JournalEntries;
