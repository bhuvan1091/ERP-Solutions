import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Megaphone, Link2, CheckCircle2, AlertTriangle } from "lucide-react";
import { PageHeader, Card, CardHeader, DataTable, StatusBadge, EmptyState, Select, Label } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtNumber, fmtDate, fmtDateTime } from "../lib/format";

const platformColor = {
    META: "bg-blue-100 text-blue-800",
    GOOGLE_ADS: "bg-amber-100 text-amber-800",
    LINKEDIN: "bg-sky-100 text-sky-800",
    TIKTOK: "bg-rose-100 text-rose-800",
    AMAZON: "bg-orange-100 text-orange-800",
};

const Advertising = () => {
    const [platform, setPlatform] = useState("");

    const { data: campaigns = [], isLoading } = useQuery({
        queryKey: ["campaigns", platform],
        queryFn: async () => (await endpoints.advertising.campaigns({ platform: platform || undefined })).data,
    });
    const { data: connections = [] } = useQuery({ queryKey: ["ad-conn"], queryFn: async () => (await endpoints.advertising.connections()).data });
    const { data: summary } = useQuery({ queryKey: ["ad-summary"], queryFn: async () => (await endpoints.advertising.summary()).data });

    const columns = [
        {
            key: "name", label: "Campaign", render: (r) => (
                <div>
                    <div className="font-medium text-sm text-slate-900">{r.name}</div>
                    <div className="text-[10px] text-slate-500">{r.objective} • {r.product_name || "No product"}</div>
                </div>
            )
        },
        { key: "platform", label: "Platform", render: (r) => <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${platformColor[r.platform] || "bg-slate-100 text-slate-700"}`}>{r.platform}</span> },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
        { key: "spend", label: "Spend", render: (r) => <span className="tabular-nums text-sm font-semibold">{fmtCurrency(r.spend_to_date)}</span> },
        { key: "imp", label: "Impr. / Clicks", render: (r) => <div className="text-xs tabular-nums"><div>{fmtNumber(r.impressions)}</div><div className="text-slate-400">{fmtNumber(r.clicks)} clicks</div></div> },
        { key: "ctr", label: "CTR", render: (r) => <span className="text-xs tabular-nums">{r.ctr}%</span> },
        { key: "cpc", label: "CPC", render: (r) => <span className="text-xs tabular-nums">{fmtCurrency(r.cpc)}</span> },
        { key: "conv", label: "Conv / CPA", render: (r) => <div className="text-xs tabular-nums"><div>{fmtNumber(r.conversions)}</div><div className="text-slate-400">{fmtCurrency(r.cpa)}</div></div> },
        { key: "roas", label: "ROAS", render: (r) => <span className={`text-sm font-semibold tabular-nums ${r.roas >= 3 ? "text-emerald-700" : r.roas >= 1 ? "text-amber-700" : "text-rose-700"}`}>{r.roas}x</span> },
    ];

    return (
        <div data-testid="advertising-page">
            <PageHeader title="Advertising"
                description="Campaign performance across your marketing channels."
                breadcrumbs={[{ label: "Marketing" }, { label: "Advertising" }]} />

            {/* Connected accounts */}
            <section className="mb-8">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <h2 className="erp-section-title">Advertising accounts</h2>
                    <span data-testid="advertising-demo-notice" className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800"><AlertTriangle className="w-3.5 h-3.5" /> Demo data · Not live</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-5 gap-3">
                    {connections.length === 0 ? <EmptyState icon={Link2} title="No ad accounts connected" /> : connections.map((c) => (
                        <Card key={c.id} className="p-4" data-testid={`ad-connection-${c.platform}`}>
                            <div className="flex items-start gap-3 mb-4">
                                <span className={`w-9 h-9 rounded-lg shrink-0 flex items-center justify-center text-base font-bold ${platformColor[c.platform] || "bg-slate-100"}`}>{({META: "m", GOOGLE_ADS: "G", LINKEDIN: "in", TIKTOK: "t", AMAZON: "a"})[c.platform] || c.platform[0]}</span>
                                <div className="min-w-0">
                                    <div className="text-sm font-bold text-slate-900 break-words">{c.account_name}</div>
                                    <div className="text-[10px] text-slate-500 break-all mt-1">{c.account_id}</div>
                                </div>
                            </div>
                            <div className="border-t border-slate-100 pt-3">
                                <div>
                                    <StatusBadge status={c.status} />
                                    <div className="text-[10px] text-slate-400 mt-0.5">Last synced {fmtDateTime(c.last_sync_at)}</div>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            </section>

            {/* Platform summary */}
            {summary && (
                <div className="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-5 gap-4 mb-8">
                    {(summary.platforms || []).map((p) => (
                        <Card key={p.platform} className="p-4" data-testid={`platform-summary-${p.platform}`}>
                            <div className="flex flex-wrap gap-2 items-center justify-between mb-4">
                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${platformColor[p.platform] || "bg-slate-100"}`}>{p.platform}</span>
                                <span className="text-[10px] text-slate-500">{p.campaigns} campaigns</span>
                            </div>
                            <div className="text-xs text-slate-500">Spend</div>
                            <div className="font-heading font-bold text-2xl tabular-nums text-slate-900">{fmtCurrency(p.spend)}</div>
                            <div className="mt-3 flex flex-wrap gap-2 justify-between text-[11px]">
                                <span className="text-slate-500">ROAS <strong className={p.roas >= 3 ? "text-emerald-700" : "text-slate-700"}>{p.roas}x</strong></span>
                                <span className="text-slate-500">Rev {fmtCurrency(p.revenue)}</span>
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            <Card className="mb-4"><div className="p-4 flex gap-3 items-end">
                <div className="w-56"><Label>Platform</Label>
                    <Select data-testid="advertising-platform-filter" aria-label="Filter by platform" value={platform} onChange={(e) => setPlatform(e.target.value)}>
                        <option value="">All</option>
                        <option value="META">Meta (Facebook / Instagram)</option>
                        <option value="GOOGLE_ADS">Google Ads</option>
                        <option value="LINKEDIN">LinkedIn</option>
                        <option value="TIKTOK">TikTok</option>
                        <option value="AMAZON">Amazon Ads</option>
                    </Select></div>
            </div></Card>

            <Card>
                <CardHeader title="Campaigns" description={`Platform-reported performance • ERP-attributed revenue: ${fmtCurrency(summary?.erp_attributed_revenue || 0)}`} />
                <DataTable testId="campaigns-table" columns={columns} rows={campaigns} loading={isLoading}
                    empty={<EmptyState icon={Megaphone} title="No campaigns" />} />
            </Card>

            <div className="mt-5 py-3 border-t border-slate-200" data-testid="advertising-data-note">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                    <div className="text-xs text-slate-600 leading-relaxed">
                        <strong className="text-slate-900">Demo campaign metrics.</strong> Advertising accounts and platform performance are sample data, not live API results. ERP-attributed revenue reflects tagged sales orders.
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Advertising;
