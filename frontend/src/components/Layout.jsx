import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
    LayoutDashboard, Package, Users, Truck, Warehouse as WhIcon,
    ShoppingCart, ClipboardList, Megaphone, Shield, Settings,
    LogOut, Search, Bell, ChevronDown, ChevronRight, ChevronLeft,
    Menu, PanelLeftClose, Factory, FlaskConical, Wallet, BarChart3,
    Boxes, Receipt, FileText, BookOpen,
} from "lucide-react";
import { useAuth } from "../lib/auth";

const NAV = [
    {
        group: "Overview",
        items: [
            { to: "/", label: "Dashboard", icon: LayoutDashboard, perm: "dashboard:read" },
        ],
    },
    {
        group: "Catalog",
        items: [
            { to: "/products", label: "Products", icon: Package, perm: "product:read" },
            { to: "/suppliers", label: "Suppliers", icon: Truck, perm: "supplier:read" },
            { to: "/customers", label: "Customers", icon: Users, perm: "customer:read" },
        ],
    },
    {
        group: "Inventory",
        items: [
            { to: "/warehouses", label: "Warehouses", icon: WhIcon, perm: "warehouse:read" },
            { to: "/inventory", label: "Stock & Batches", icon: Boxes, perm: "inventory:read" },
        ],
    },
    {
        group: "Operations",
        items: [
            { to: "/purchase-orders", label: "Purchase Orders", icon: ShoppingCart, perm: "purchase:read" },
            { to: "/sales-orders", label: "Sales Orders", icon: ClipboardList, perm: "sales:read" },
        ],
    },
    {
        group: "Finance",
        items: [
            { to: "/invoices", label: "Invoices", icon: Receipt, perm: "finance:read" },
            { to: "/payments", label: "Payments", icon: Wallet, perm: "finance:read" },
            { to: "/journal", label: "Journal Entries", icon: BookOpen, perm: "finance:read" },
            { to: "/finance-reports", label: "Finance Reports", icon: BarChart3, perm: "finance:read" },
        ],
    },
    {
        group: "Marketing",
        items: [
            { to: "/advertising", label: "Advertising", icon: Megaphone, perm: "advertising:read" },
        ],
    },
    {
        group: "Admin",
        items: [
            { to: "/users", label: "Users & Roles", icon: Shield, perm: "admin:read" },
            { to: "/audit", label: "Audit Log", icon: FileText, perm: "audit:read" },
        ],
    },
];

const Sidebar = ({ collapsed, setCollapsed }) => {
    const loc = useLocation();
    const { user, hasPermission } = useAuth();

    return (
        <aside
            data-testid="sidebar"
            className={`sidebar-transition bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0 ${collapsed ? "w-20" : "w-64"}`}
        >
            <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200">
                {!collapsed && (
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-md bg-forest-700 text-white flex items-center justify-center font-heading font-bold">G</div>
                        <div className="leading-tight">
                            <div className="font-heading font-semibold text-slate-900 text-sm">GreenPeak</div>
                            <div className="text-[10px] uppercase tracking-wider text-slate-500">Nutrition ERP</div>
                        </div>
                    </div>
                )}
                {collapsed && (
                    <div className="w-8 h-8 rounded-md bg-forest-700 text-white flex items-center justify-center font-heading font-bold">G</div>
                )}
                <button
                    data-testid="sidebar-toggle"
                    onClick={() => setCollapsed(!collapsed)}
                    className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 focus-ring"
                    aria-label="Toggle sidebar"
                >
                    {collapsed ? <ChevronRight className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
                </button>
            </div>

            <nav className="flex-1 overflow-y-auto erp-scroll py-4 px-2">
                {NAV.map((group) => {
                    const visibleItems = group.items.filter((i) => !i.perm || hasPermission(i.perm));
                    if (!visibleItems.length) return null;
                    return (
                        <div key={group.group} className="mb-5">
                            {!collapsed && (
                                <div className="px-3 mb-2 text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                                    {group.group}
                                </div>
                            )}
                            <ul className="space-y-0.5">
                                {visibleItems.map((item) => {
                                    const Icon = item.icon;
                                    const active = loc.pathname === item.to || (item.to !== "/" && loc.pathname.startsWith(item.to));
                                    return (
                                        <li key={item.to}>
                                            <Link
                                                to={item.to}
                                                data-testid={`nav-${item.to.replace(/\//g, "-") || "home"}`}
                                                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors
                                                    ${active ? "bg-forest-50 text-forest-700 font-medium" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}
                                                `}
                                                title={collapsed ? item.label : undefined}
                                            >
                                                <Icon className={`w-4 h-4 ${active ? "text-forest-700" : "text-slate-400"} shrink-0`} />
                                                {!collapsed && <span className="truncate">{item.label}</span>}
                                            </Link>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    );
                })}
            </nav>

            {!collapsed && user && (
                <div className="border-t border-slate-200 p-3">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-forest-100 text-forest-700 flex items-center justify-center font-semibold text-xs">
                            {user.full_name?.[0]?.toUpperCase() || "U"}
                        </div>
                        <div className="flex-1 min-w-0 leading-tight">
                            <div className="text-xs font-medium text-slate-900 truncate">{user.full_name}</div>
                            <div className="text-[10px] text-slate-500 truncate">{user.role_name}</div>
                        </div>
                    </div>
                </div>
            )}
        </aside>
    );
};

const Topbar = () => {
    const { user, logout } = useAuth();
    const nav = useNavigate();
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-20 flex items-center px-6 gap-4">
            <div className="flex-1 max-w-xl">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                        data-testid="global-search"
                        type="search"
                        placeholder="Search products, orders, customers..."
                        className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-md text-sm focus-ring focus:bg-white"
                    />
                </div>
            </div>

            <button
                data-testid="topbar-notifications"
                className="p-2 rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 relative focus-ring"
                aria-label="Notifications"
            >
                <Bell className="w-5 h-5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500"></span>
            </button>

            <div className="relative">
                <button
                    data-testid="topbar-profile"
                    onClick={() => setMenuOpen((v) => !v)}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 focus-ring"
                >
                    <div className="w-8 h-8 rounded-full bg-forest-700 text-white flex items-center justify-center text-xs font-semibold">
                        {user?.full_name?.[0]?.toUpperCase() || "U"}
                    </div>
                    <div className="hidden sm:block leading-tight text-left">
                        <div className="text-xs font-medium text-slate-900">{user?.full_name}</div>
                        <div className="text-[10px] text-slate-500">{user?.role_name}</div>
                    </div>
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                </button>
                {menuOpen && (
                    <>
                        <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)}></div>
                        <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-slate-200 rounded-md shadow-lg py-1 z-20">
                            <div className="px-3 py-2 border-b border-slate-100">
                                <div className="text-xs font-medium text-slate-900">{user?.email}</div>
                                <div className="text-[10px] text-slate-500">{user?.role_name}</div>
                            </div>
                            <button
                                onClick={async () => { await logout(); nav("/login"); }}
                                data-testid="logout-button"
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                            >
                                <LogOut className="w-4 h-4" /> Sign out
                            </button>
                        </div>
                    </>
                )}
            </div>
        </header>
    );
};

const Layout = ({ children }) => {
    const [collapsed, setCollapsed] = useState(false);
    return (
        <div className="flex min-h-screen bg-slate-50">
            <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
            <div className="flex-1 flex flex-col min-w-0">
                <Topbar />
                <main className="flex-1 p-6 lg:p-8 animate-fade-in">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;
