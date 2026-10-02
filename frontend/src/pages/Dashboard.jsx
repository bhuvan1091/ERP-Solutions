import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Cell,
} from "recharts";
import {
    TrendingUp, AlertTriangle, Package, CheckCircle2, Clock,
    ArrowUpRight, ChevronRight,
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

const KpiCard = ({ k }) => {
    const Icon = KPI_ICON[k.label] || TrendingUp;
    const isCurrency = ["Revenue (30d)", "Inventory Valuation", "Ad Spend (All)"].includes(k.label);
    const isWarn = ["Near-Expiry Batches", "Expired Batches"].includes(k.label) && Number(k.value) > 0;
    return (
        <div className={`bg-white border rounded-md p-4 ${isWarn ? "border-amber-200" : "border-slate-200"}`} data-testid={`kpi-${k.label.replace(/\s/g, "-")}`}>
            <div className="flex items-start justify-between">
                <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">{k.label}</div>
                <Icon className={`w-4 h-4 ${isWarn ? "text-amber-500" : "text-forest-600"}`} />
            </div>
            <div className="mt-2 font-heading text-2xl font-bold text-slate-900 tabular-nums">
                {isCurrency ? fmtCurrency(k.value) : fmtNumber(k.value, k.label === "Platform ROAS" ? 2 : 0)}
                {k.label === "Platform ROAS" && <span className="text-sm text-slate-400 ml-1">x</span>}
            </div>
            {k.hint && <div className="text-xs text-slate-500 mt-1">{k.hint}</div>}
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
                title={`Welcome back, ${user?.full_name?.split(" ")[0] || ""}`}
                description={`${user?.role_name || "Operator"} console • Real-time view of operations across procurement, inventory, sales and marketing.`}
            />

            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {isLoading ? (
                    Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="h-24 shimmer rounded-md"></div>
                    ))
                ) : (
                    kpis.map((k, i) => <KpiCard k={k} key={i} />)
                )}
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                <Card className="lg:col-span-2">
                    <CardHeader title="Revenue (last 14 days)" description="Confirmed sales orders by day" />
                    <div className="p-4 h-72">
                        {isLoading ? (
                            <div className="h-full shimmer rounded-md"></div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={trend} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(d) => new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })} />
                                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip
                                        formatter={(v) => fmtCurrency(v)}
                                        contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e2e8f0" }}
                                    />
                                    <Line type="monotone" dataKey="revenue" stroke="#047857" strokeWidth={2} dot={{ r: 3, fill: "#047857" }} />
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                <Card>
                    <CardHeader title="Campaign spend by platform" description="Across all connected ad accounts" />
                    <div className="p-4 h-72">
                        {isLoading ? (
                            <div className="h-full shimmer rounded-md"></div>
                        ) : campaigns.length === 0 ? (
                            <EmptyState title="No campaigns yet" />
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={campaigns} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis dataKey="platform" tick={{ fontSize: 10, fill: "#64748b" }} />
                                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }}
                                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip formatter={(v, n) => n === "spend" ? fmtCurrency(v) : v}
                                        contentStyle={{ fontSize: 12, borderRadius: 6 }} />
                                    <Bar dataKey="spend" radius={[4, 4, 0, 0]}>
                                        {campaigns.map((c, i) => (
                                            <Cell key={i} fill={["#047857", "#0ea5e9", "#8b5cf6", "#f59e0b", "#f43f5e"][i % 5]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>
            </div>

            {/* Approvals + Near Expiry + Low Stock */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                <Card>
                    <CardHeader title="Pending approvals" description="Purchase orders awaiting your decision"
                        action={<Link to="/purchase-orders?status=PENDING_APPROVAL" className="text-xs text-forest-700 hover:underline flex items-center">View all <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="divide-y divide-slate-100">
                        {approvals.length === 0 ? (
                            <div className="p-4 text-xs text-slate-400">No pending approvals</div>
                        ) : approvals.map((p) => (
                            <Link key={p.id} to={`/purchase-orders`} className="block p-3 hover:bg-slate-50 transition-colors">
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
                        action={<Link to="/inventory" className="text-xs text-forest-700 hover:underline flex items-center">View all <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="divide-y divide-slate-100">
                        {near.length === 0 ? (
                            <div className="p-4 text-xs text-slate-400">No batches near expiry</div>
                        ) : near.map((n) => (
                            <div key={n.id} className="p-3">
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
                        action={<Link to="/inventory" className="text-xs text-forest-700 hover:underline flex items-center">View all <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="divide-y divide-slate-100">
                        {low.length === 0 ? (
                            <div className="p-4 text-xs text-slate-400">Stock levels healthy</div>
                        ) : low.map((p) => (
                            <div key={p.id} className="p-3">
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
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <Card className="lg:col-span-2">
                    <CardHeader title="Top-selling products (30 days)" />
                    <div className="divide-y divide-slate-100">
                        {top.length === 0 ? <EmptyState title="No sales yet" /> : top.map((p, i) => (
                            <div key={p.id} className="p-3 flex justify-between items-center">
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
                        action={<Link to="/audit" className="text-xs text-forest-700 hover:underline flex items-center">View audit log <ChevronRight className="w-3 h-3" /></Link>} />
                    <div className="divide-y divide-slate-100">
                        {activity.length === 0 ? <EmptyState title="No activity yet" /> : activity.map((a) => (
                            <div key={a.id} className="p-3">
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
