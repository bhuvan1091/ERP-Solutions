import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Scale, TrendingUp, TrendingDown, Clock } from "lucide-react";
import { PageHeader, Card, CardHeader, Button, Input, Label, EmptyState } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtDate } from "../lib/format";

const FinanceReports = () => {
    const [tab, setTab] = useState("TRIAL_BALANCE");
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10);
    const [asOf, setAsOf] = useState(today);
    const [fromDate, setFromDate] = useState(firstDay);
    const [toDate, setToDate] = useState(today);

    const tbQuery = useQuery({ queryKey: ["tb", asOf, tab], queryFn: async () => (await endpoints.finance.trialBalance({ as_of: asOf })).data, enabled: tab === "TRIAL_BALANCE" });
    const arQuery = useQuery({ queryKey: ["ar", asOf, tab], queryFn: async () => (await endpoints.finance.arAging({ as_of: asOf })).data, enabled: tab === "AR_AGING" });
    const apQuery = useQuery({ queryKey: ["ap", asOf, tab], queryFn: async () => (await endpoints.finance.apAging({ as_of: asOf })).data, enabled: tab === "AP_AGING" });
    const plQuery = useQuery({ queryKey: ["pl", fromDate, toDate, tab], queryFn: async () => (await endpoints.finance.profitLoss({ from_date: fromDate, to_date: toDate })).data, enabled: tab === "PNL" });

    const tabs = [
        { k: "TRIAL_BALANCE", label: "Trial Balance", icon: Scale },
        { k: "PNL", label: "Profit & Loss", icon: TrendingUp },
        { k: "AR_AGING", label: "AR Aging", icon: Clock },
        { k: "AP_AGING", label: "AP Aging", icon: Clock },
    ];

    return (
        <div data-testid="finance-reports-page">
            <PageHeader title="Finance reports"
                description="Reports derived directly from posted journal entries. Every number is traceable to a journal line."
                breadcrumbs={[{ label: "Finance" }, { label: "Reports" }]} />

            <div className="flex items-center gap-2 mb-4 border-b border-slate-200">
                {tabs.map((t) => {
                    const Icon = t.icon;
                    return (
                        <button key={t.k} data-testid={`fr-tab-${t.k}`} onClick={() => setTab(t.k)}
                            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium -mb-px border-b-2 ${tab === t.k ? "border-forest-700 text-forest-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}>
                            <Icon className="w-4 h-4" /> {t.label}
                        </button>
                    );
                })}
            </div>

            <Card className="mb-4"><div className="p-4 flex gap-3 items-end flex-wrap">
                {tab !== "PNL" && (
                    <div className="w-56"><Label>As of</Label><Input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></div>
                )}
                {tab === "PNL" && (
                    <>
                        <div className="w-48"><Label>From</Label><Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></div>
                        <div className="w-48"><Label>To</Label><Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} /></div>
                    </>
                )}
            </div></Card>

            {tab === "TRIAL_BALANCE" && (
                <Card>
                    <CardHeader title="Trial Balance" description={`As of ${fmtDate(asOf)}`}
                        action={tbQuery.data && (
                            <span className={`text-xs font-semibold ${tbQuery.data.is_balanced ? "text-emerald-700" : "text-rose-700"}`}>
                                {tbQuery.data.is_balanced ? "Balanced" : "Out of balance"}
                            </span>
                        )} />
                    <div className="overflow-x-auto erp-scroll">
                        <table className="min-w-full text-sm" data-testid="tb-table">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="text-left px-4 py-2 text-[11px] uppercase text-slate-500">Account</th>
                                    <th className="text-left px-4 py-2 text-[11px] uppercase text-slate-500">Type</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">Debit</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">Credit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {tbQuery.data?.rows.map((r) => (
                                    <tr key={r.account_code}>
                                        <td className="px-4 py-2"><span className="font-mono text-xs text-slate-500">{r.account_code}</span> {r.account_name}</td>
                                        <td className="px-4 py-2 text-xs">{r.account_type}</td>
                                        <td className="px-4 py-2 text-right tabular-nums">{Number(r.debit) > 0 ? fmtCurrency(r.debit) : <span className="text-slate-300">—</span>}</td>
                                        <td className="px-4 py-2 text-right tabular-nums">{Number(r.credit) > 0 ? fmtCurrency(r.credit) : <span className="text-slate-300">—</span>}</td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-slate-50 font-semibold">
                                <tr>
                                    <td colSpan={2} className="px-4 py-2 text-right">Totals</td>
                                    <td className="px-4 py-2 text-right tabular-nums">{fmtCurrency(tbQuery.data?.total_debit)}</td>
                                    <td className="px-4 py-2 text-right tabular-nums">{fmtCurrency(tbQuery.data?.total_credit)}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </Card>
            )}

            {tab === "PNL" && plQuery.data && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Card>
                        <CardHeader title="Income" />
                        <table className="min-w-full text-sm">
                            <tbody className="divide-y divide-slate-100">
                                {plQuery.data.income.accounts.length === 0 ? (
                                    <tr><td className="p-4 text-center text-xs text-slate-400">No income in period</td></tr>
                                ) : plQuery.data.income.accounts.map((a) => (
                                    <tr key={a.code}><td className="px-4 py-2"><span className="font-mono text-xs text-slate-500">{a.code}</span> {a.name}</td><td className="px-4 py-2 text-right tabular-nums">{fmtCurrency(a.amount)}</td></tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-emerald-50 font-semibold"><tr><td className="px-4 py-2">Total income</td><td className="px-4 py-2 text-right tabular-nums text-emerald-700">{fmtCurrency(plQuery.data.income.total)}</td></tr></tfoot>
                        </table>
                    </Card>
                    <Card>
                        <CardHeader title="Expenses" />
                        <table className="min-w-full text-sm">
                            <tbody className="divide-y divide-slate-100">
                                {plQuery.data.expenses.accounts.length === 0 ? (
                                    <tr><td className="p-4 text-center text-xs text-slate-400">No expenses in period</td></tr>
                                ) : plQuery.data.expenses.accounts.map((a) => (
                                    <tr key={a.code}><td className="px-4 py-2"><span className="font-mono text-xs text-slate-500">{a.code}</span> {a.name}</td><td className="px-4 py-2 text-right tabular-nums">{fmtCurrency(a.amount)}</td></tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-rose-50 font-semibold"><tr><td className="px-4 py-2">Total expenses</td><td className="px-4 py-2 text-right tabular-nums text-rose-700">{fmtCurrency(plQuery.data.expenses.total)}</td></tr></tfoot>
                        </table>
                    </Card>
                    <Card className="p-6 flex flex-col justify-center">
                        <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Net profit</div>
                        <div className={`font-heading font-bold text-3xl tabular-nums ${Number(plQuery.data.net_profit) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{fmtCurrency(plQuery.data.net_profit)}</div>
                        <div className="text-xs text-slate-500 mt-2">{fmtDate(plQuery.data.from_date)} → {fmtDate(plQuery.data.to_date)}</div>
                        <div className="mt-6 flex items-center gap-2 text-xs">
                            {Number(plQuery.data.net_profit) >= 0 ? <TrendingUp className="w-4 h-4 text-emerald-600" /> : <TrendingDown className="w-4 h-4 text-rose-600" />}
                            <span className="text-slate-600">Income - Expenses = Net profit</span>
                        </div>
                    </Card>
                </div>
            )}

            {(tab === "AR_AGING" || tab === "AP_AGING") && (
                <Card>
                    <CardHeader title={tab === "AR_AGING" ? "Accounts Receivable aging" : "Accounts Payable aging"}
                        description={`As of ${fmtDate(asOf)} • Outstanding invoices by bucket`} />
                    <div className="overflow-x-auto erp-scroll">
                        <table className="min-w-full text-sm" data-testid={`${tab.toLowerCase()}-table`}>
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="text-left px-4 py-2 text-[11px] uppercase text-slate-500">{tab === "AR_AGING" ? "Customer" : "Supplier"}</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">Current</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">1-30d</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">31-60d</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">61-90d</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">&gt; 90d</th>
                                    <th className="text-right px-4 py-2 text-[11px] uppercase text-slate-500">Total</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {(tab === "AR_AGING" ? arQuery.data : apQuery.data)?.rows.length === 0 ? (
                                    <tr><td colSpan={7} className="p-10 text-center text-slate-400 text-sm">No outstanding balances. 🎉</td></tr>
                                ) : (tab === "AR_AGING" ? arQuery.data : apQuery.data)?.rows.map((r) => (
                                    <tr key={r.counterparty_id}>
                                        <td className="px-4 py-2 font-medium">{r.counterparty_name}</td>
                                        <td className="px-4 py-2 text-right tabular-nums">{fmtCurrency(r.current)}</td>
                                        <td className="px-4 py-2 text-right tabular-nums">{fmtCurrency(r.d_1_30)}</td>
                                        <td className="px-4 py-2 text-right tabular-nums text-amber-700">{fmtCurrency(r.d_31_60)}</td>
                                        <td className="px-4 py-2 text-right tabular-nums text-amber-700">{fmtCurrency(r.d_61_90)}</td>
                                        <td className="px-4 py-2 text-right tabular-nums text-rose-700">{fmtCurrency(r.d_over_90)}</td>
                                        <td className="px-4 py-2 text-right tabular-nums font-semibold">{fmtCurrency(r.total_outstanding)}</td>
                                    </tr>
                                ))}
                            </tbody>
                            {(tab === "AR_AGING" ? arQuery.data : apQuery.data)?.totals && (
                                <tfoot className="bg-slate-50 font-semibold">
                                    <tr>
                                        <td className="px-4 py-2">Totals</td>
                                        {["current", "d_1_30", "d_31_60", "d_61_90", "d_over_90", "total_outstanding"].map((k) => (
                                            <td key={k} className="px-4 py-2 text-right tabular-nums">{fmtCurrency((tab === "AR_AGING" ? arQuery.data : apQuery.data).totals[k])}</td>
                                        ))}
                                    </tr>
                                </tfoot>
                            )}
                        </table>
                    </div>
                </Card>
            )}
        </div>
    );
};

export default FinanceReports;
