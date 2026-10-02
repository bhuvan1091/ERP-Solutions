import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Cell,
} from "recharts";
import {
    TrendingUp, AlertTriangle, Package, CheckCircle2, Clock,
    ArrowUpRight, ChevronRight, CalendarDays,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency, fmtNumber, fmtDateTime, fmtDate } from "../lib/format";
import { useAuth } from "../lib/auth";

const KPI_ICON = {
    "Revenue (30d)": TrendingUp,
    "Inventory Valuation": Package,
    "Pending POs": Clock,
    "Open Sales Orders": CheckCircle2,
    "Near-Expiry Batches": AlertTriangle,
    "Expired Batches": AlertTriangle,
    "Ad Spend (All)": TrendingUp,
    "Platform ROAS": ArrowUpRight,
};

const KpiCard = ({ k, index }) => {
    const Icon = KPI_ICON[k.label] || TrendingUp;
    const isCurrency = ["Revenue (30d)", "Inventory Valuation", "Ad Spend (All)"].includes(k.label);
    const isWarn = ["Near-Expiry Batches", "Expired Batches"].includes(k.label) && Number(k.value) > 0;
    return (
        <div className={`kpi-card ${index === 0 ? "kpi-card-primary" : ""} ${index > 3 ? "!py-4" : ""}`} data-testid={`kpi-${k.label.replace(/\s/g, "-")}`}>
            <div className="flex items-center justify-between gap-2">
                <div className="kpi-label text-xs font-bold text-slate-500">{k.label}</div>
                <div className={`kpi-icon ${isWarn ? "bg-amber-50 text-amber-700" : ["", "bg-sky-50 text-sky-700", "bg-amber-50 text-amber-700", "bg-forest-50 text-forest-700"][index % 4] || "bg-forest-50 text-forest-700"}`}><Icon className="w-[18px] h-[18px]" strokeWidth={1.7} /></div>
            </div>
            <div className={`kpi-value mt-3 text-[#192b25] tabular-nums ${index > 3 ? "!text-2xl" : ""}`}>
                {isCurrency ? fmtCurrency(k.value) : fmtNumber(k.value, k.label === "Platform ROAS" ? 2 : 0)}
                {k.label === "Platform ROAS" && <span className="text-sm text-slate-400 ml-1">x</span>}
            </div>
            {k.hint && <div className="kpi-hint text-[11px] text-slate-500 mt-2">{k.hint}</div>}
        </div>
    );
};

const Dashboard = () => {
    const { user } = useAuth();
    const { data, isLoading } = useQuery({
        queryKey: ["dashboard"],
        queryFn: async () => (await endpoints.dashboard()).data,
    });

    const kpis = data?.kpis || [];
    const trend = data?.revenue_trend || [];
    const low = data?.low_stock || [];
    const near = data?.near_expiry || [];
    const approvals = data?.pending_approvals || [];
    const top = data?.top_products || [];
    const campaigns = data?.campaign_summary || [];
    const activity = data?.recent_activity || [];

    return (
        <div data-testid="dashboard-page">
            <PageHeader
                title="Business overview"
                description={`Welcome back, ${user?.full_name?.split(" ")[0] || "there"}. Here’s where your business stands today.`}
                actions={<div data-testid="dashboard-date" className="flex items-center gap-2.5 text-xs text-slate-600 px-3 py-2.5 border border-slate-200 rounded-md bg-white"><CalendarDays className="w-4 h-4 text-slate-400" />{new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</div>}
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 min-[420px]:grid-cols-2 xl:grid-cols-4 gap-4 mb-7">
                {isLoading ? (
                    Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="h-24 shimmer rounded-md"></div>
                    ))
                ) : (
                    kpis.map((k, i) => <KpiCard k={k} index={i} key={i} />)
                )}
            </div>

            {/* Charts row */}
            <div className="dashboard-chart grid grid-cols-1 xl:grid-cols-3 gap-5 mb-8">
                <Card className="xl:col-span-2">
                    <CardHeader title="Revenue trend" description="Confirmed sales · Last 14 days" action={<span data-testid="revenue-chart-legend" className="flex items-center gap-1.5 text-[11px] text-slate-500 shrink-0 pt-1"><span className="w-2 h-2 rounded-full bg-forest-600" /> Revenue</span>} />
                    <div className="p-3 sm:p-5 h-72" data-testid="revenue-chart">
                        {isLoading ? (
                            <div className="h-full shimmer rounded-md"></div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={trend} margin={{ left: -12, right: 12, top: 8, bottom: 8 }}>
                                    <defs><linearGradient id="revenue-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#417b5e" stopOpacity={0.16} /><stop offset="95%" stopColor="#417b5e" stopOpacity={0.01} /></linearGradient></defs>
                                    <CartesianGrid strokeDasharray="4 4" stroke="#e8ede9" vertical={false} />
                                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(d) => new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })} />
                                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip
                                        formatter={(v) => fmtCurrency(v)}
                                        contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e2e8f0" }}
                                    />
                                    <Area type="monotone" dataKey="revenue" stroke="#2e664d" fill="url(#revenue-fill)" strokeWidth={2.5} activeDot={{ r: 5, strokeWidth: 3, stroke: "white" }} />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                <Card>
                    <CardHeader title="Advertising spend" description="By platform · Demo data" />
                    <div className="p-3 sm:p-5 h-72" data-testid="advertising-spend-chart">
                        {isLoading ? (
                            <div className="h-full shimmer rounded-md"></div>
                        ) : campaigns.length === 0 ? (
                            <EmptyState title="No campaigns yet" />
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={campaigns} margin={{ left: -14, right: 4, top: 8, bottom: 8 }} barSize={30}>
                                    <CartesianGrid strokeDasharray="4 4" stroke="#e8ede9" vertical={false} />
                                    <XAxis dataKey="platform" tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v) => ({ META: "Meta", GOOGLE_ADS: "Google", LINKEDIN: "LinkedIn", TIKTOK: "TikTok", AMAZON: "Amazon" }[v] || v)} />
                                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip formatter={(v, n) => n === "spend" ? fmtCurrency(v) : v}
                                        contentStyle={{ fontSize: 12, borderRadius: 6 }} />
                                    <Bar dataKey="spend" radius={[4, 4, 0, 0]}>
                                        {campaigns.map((c, i) => (
                                            <Cell key={i} fill={["#417b5e", "#78a6bb", "#d9b66b", "#849eaa", "#c48b7b"][i % 5]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>
            </div>

            {/* Approvals + Near Expiry + Low Stock */}
            <div className="flex items-center gap-3 mb-4"><h2 className="erp-section-title">Needs your attention</h2><div className="flex-1 h-px bg-slate-200" /></div>
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-8">
                <Card>
                    <CardHeader title="Pending approvals" description="Purchase orders awaiting your decision"
                        action={<Link data-testid="dashboard-view-approvals" to="/purchase-orders?status=PENDING_APPROVAL" className="text-xs text-forest-700 hover:underline flex items-center shrink-0">View all <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="dashboard-list divide-y divide-slate-100">
                        {approvals.length === 0 ? (
                            <div className="p-4 text-xs text-slate-400">No pending approvals</div>
                        ) : approvals.map((p) => (
                            <Link key={p.id} data-testid={`dashboard-approval-${p.id}`} to={`/purchase-orders`} className="block p-3 hover:bg-slate-50 transition-colors">
                                <div className="flex justify-between items-start">
                                    <div className="min-w-0">
                                        <div className="font-mono text-xs text-slate-900">{p.po_number}</div>
                                        <div className="text-xs text-slate-500 truncate">{p.supplier_name}</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-semibold text-sm text-slate-900">{fmtCurrency(p.total)}</div>
                                        <div className="text-[10px] text-slate-400">{fmtDate(p.created_at)}</div>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                </Card>

                <Card>
                    <CardHeader title="Near expiry (≤ 60 days)" description="FEFO-prioritised batches"
                        action={<Link data-testid="dashboard-view-expiry" to="/inventory" className="text-xs text-forest-700 hover:underline flex items-center shrink-0">View all <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="dashboard-list divide-y divide-slate-100">
                        {near.length === 0 ? (
                            <div className="p-4 text-xs text-slate-400">No batches near expiry</div>
                        ) : near.map((n) => (
                            <div key={n.id} className="p-3" data-testid={`dashboard-expiry-${n.id}`}>
                                <div className="flex justify-between items-start">
                                    <div className="min-w-0">
                                        <div className="text-xs font-medium text-slate-900 truncate">{n.product_name}</div>
                                        <div className="text-[10px] text-slate-500">Batch {n.batch_number} • {n.warehouse}</div>
                                    </div>
                                    <div className="text-right">
                                        <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${n.days_to_expiry <= 15 ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-800"}`}>
                                            {n.days_to_expiry}d left
                                        </span>
                                        <div className="text-[10px] text-slate-400 mt-1">Qty {fmtNumber(n.quantity, 0)}</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>

                <Card>
                    <CardHeader title="Low stock" description="Below reorder level"
                        action={<Link data-testid="dashboard-view-stock" to="/inventory" className="text-xs text-forest-700 hover:underline flex items-center shrink-0">View all <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="dashboard-list divide-y divide-slate-100">
                        {low.length === 0 ? (
                            <div className="p-4 text-xs text-slate-400">Stock levels healthy</div>
                        ) : low.map((p) => (
                            <div key={p.id} className="p-3" data-testid={`dashboard-stock-${p.id}`}>
                                <div className="flex justify-between items-start">
                                    <div className="min-w-0">
                                        <div className="text-xs font-medium text-slate-900 truncate">{p.name}</div>
                                        <div className="text-[10px] text-slate-500 font-mono">{p.sku}</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm font-semibold text-rose-700">{fmtNumber(p.stock_on_hand)}</div>
                                        <div className="text-[10px] text-slate-400">Reorder {fmtNumber(p.reorder_level)}</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            </div>

            {/* Top products + Recent activity */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
                <Card className="xl:col-span-2">
                    <CardHeader title="Top-selling products (30 days)" />
                    <div className="dashboard-list divide-y divide-slate-100">
                        {top.length === 0 ? <EmptyState title="No sales yet" /> : top.map((p, i) => (
                            <div key={p.id} className="p-3 flex justify-between items-center gap-3" data-testid={`dashboard-top-product-${p.id}`}>
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className="w-7 h-7 rounded-md bg-forest-50 text-forest-700 flex items-center justify-center text-xs font-semibold">
                                        {i + 1}
                                    </div>
                                    <div className="min-w-0">
                                        <div className="text-sm font-medium text-slate-900 truncate">{p.name}</div>
                                        <div className="text-[11px] text-slate-500 font-mono">{p.sku}</div>
                                    </div>
                                </div>
                                <div className="font-semibold text-sm text-slate-900 tabular-nums">{fmtCurrency(p.revenue)}</div>
                            </div>
                        ))}
                    </div>
                </Card>

                <Card>
                    <CardHeader title="Recent activity"
                        action={<Link data-testid="dashboard-view-audit" to="/audit" className="text-xs text-forest-700 hover:underline flex items-center shrink-0">View audit log <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="dashboard-list divide-y divide-slate-100">
                        {activity.length === 0 ? <EmptyState title="No activity yet" /> : activity.map((a) => (
                            <div key={a.id} className="p-3" data-testid={`dashboard-activity-${a.id}`}>
                                <div className="flex items-start gap-2">
                                    <StatusBadge status={a.action}>{a.action}</StatusBadge>
                                    <div className="min-w-0 flex-1">
                                        <div className="text-xs text-slate-700 truncate">
                                            <span className="font-medium">{a.entity_type}</span>
                                            {a.user_email && <> by <span className="font-mono text-slate-500">{a.user_email}</span></>}
                                        </div>
                                        <div className="text-[10px] text-slate-400">{fmtDateTime(a.created_at)}</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default Dashboard;
