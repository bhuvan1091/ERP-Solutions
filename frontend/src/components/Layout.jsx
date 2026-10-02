import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
    LayoutDashboard, Package, Users, Truck, Warehouse as WhIcon,
    ShoppingCart, ClipboardList, Megaphone, Shield, Settings,
    LogOut, Search, Bell, ChevronDown, ChevronRight, ChevronLeft,
    Menu, PanelLeftClose, Factory, FlaskConical, Wallet, BarChart3,
    Boxes, Receipt, FileText, BookOpen, Leaf, X,
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
            { to: "/settings", label: "Company Settings", icon: Settings, perm: "admin:write" },
            { to: "/users", label: "Users & Roles", icon: Shield, perm: "admin:read" },
            { to: "/audit", label: "Audit Log", icon: FileText, perm: "audit:read" },
        ],
    },
];

const Sidebar = ({ collapsed, setCollapsed, mobileOpen, closeMobile }) => {
    const loc = useLocation();
    const { user, hasPermission } = useAuth();
    const expanded = !collapsed || mobileOpen;

    return (
        <aside
            data-testid="sidebar"
            className={`erp-sidebar sidebar-transition ${mobileOpen ? "flex fixed inset-y-0 left-0 z-40" : "hidden"} lg:flex lg:sticky lg:top-0 flex-col h-dvh shrink-0 bg-[#122c24] text-white ${expanded ? "w-[232px]" : "w-[76px]"}`}
        >
            <div className={`h-[84px] shrink-0 flex items-center ${expanded ? "justify-between px-5" : "justify-center px-3"} border-b border-white/10`}>
                {expanded && (
                    <Link to="/" onClick={closeMobile} data-testid="brand-home" className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-lg bg-[#d9ecb9] text-forest-800 flex items-center justify-center"><Leaf className="w-5 h-5" strokeWidth={1.8} /></div>
                        <div className="leading-tight">
                            <div className="font-heading font-bold text-white text-lg">GreenPeak<span className="text-[#d9ecb9]">.</span></div>
                            <div className="text-[10px] text-[#a7bdb3] mt-0.5">NUTRITION ERP</div>
                        </div>
                    </Link>
                )}
                {!expanded && (
                    <Leaf className="w-7 h-7 text-[#d9ecb9]" aria-hidden="true" />
                )}
                {mobileOpen && <button data-testid="mobile-sidebar-close" onClick={closeMobile} className="p-2 rounded-md hover:bg-white/10 lg:hidden" aria-label="Close navigation"><X className="w-4 h-4" /></button>}
            </div>

            <nav aria-label="Main navigation" className="flex-1 overflow-y-auto erp-scroll py-5 px-3">
                {NAV.map((group) => {
                    const visibleItems = group.items.filter((i) => !i.perm || hasPermission(i.perm));
                    if (!visibleItems.length) return null;
                    return (
                        <div key={group.group} className="mb-5 last:mb-0">
                            {expanded && (
                                <div className="px-3 mb-2 text-[10px] uppercase font-bold text-[#8ba99a]">
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
                                                onClick={closeMobile}
                                                aria-current={active ? "page" : undefined}
                                                data-testid={`nav-${item.to.replace(/\//g, "-") || "home"}`}
                                                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] transition-colors ${!expanded ? "justify-center" : ""}
                                                    ${active ? "bg-[#d9ecb9] text-[#173c2c] font-bold" : "text-[#c2d2c9] hover:bg-white/10 hover:text-white"}
                                                `}
                                                title={!expanded ? item.label : undefined}
                                                aria-label={!expanded ? item.label : undefined}
                                            >
                                                <Icon className="w-[17px] h-[17px] shrink-0" strokeWidth={1.7} />
                                                {expanded && <span className="truncate">{item.label}</span>}
                                            </Link>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    );
                })}
            </nav>

            <div className="border-t border-white/10 p-3 shrink-0">
                {expanded && user && <div className="flex items-center gap-2.5 px-2 py-2 mb-2" data-testid="sidebar-user">
                        <div className="w-8 h-8 rounded-md bg-white/10 text-[#d9ecb9] flex items-center justify-center font-bold text-xs shrink-0">
                            {user.full_name?.[0]?.toUpperCase() || "U"}
                        </div>
                        <div className="flex-1 min-w-0 leading-tight">
                            <div className="text-xs font-bold text-white truncate">{user.full_name}</div>
                            <div className="text-[10px] text-[#a7bdb3] truncate mt-1">{user.role_name}</div>
                        </div>
                    </div>}
                <button data-testid="sidebar-toggle" onClick={() => setCollapsed(!collapsed)}
                    className="hidden lg:flex w-full items-center justify-center gap-2 p-2 rounded-md text-[#a7bdb3] hover:text-white hover:bg-white/10 text-xs"
                    title={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
                    {collapsed ? <ChevronRight className="w-4 h-4" /> : <><PanelLeftClose className="w-4 h-4" /> Collapse menu</>}
                </button>
            </div>
        </aside>
    );
};

const Topbar = ({ openMobile }) => {
    const { user, logout } = useAuth();
    const nav = useNavigate();
    const [menuOpen, setMenuOpen] = useState(false);
    const location = useLocation();
    const page = NAV.flatMap((group) => group.items).find((item) => item.to === location.pathname);

    return (
        <header className="h-[72px] bg-white border-b border-[#e3e8e5] sticky top-0 z-20 flex items-center px-4 sm:px-6 lg:px-8 gap-3 sm:gap-5">
            <button data-testid="mobile-sidebar-open" onClick={openMobile} className="lg:hidden p-2 rounded-md text-forest-700 hover:bg-forest-50" aria-label="Open navigation"><Menu className="w-5 h-5" /></button>
            <div className="flex-1 min-w-0 flex items-center gap-2 text-xs text-slate-500" data-testid="topbar-location">
                <span className="hidden sm:inline">Workspace</span><ChevronRight className="hidden sm:block w-3 h-3 text-slate-300" />
                <span className="text-slate-800 font-bold truncate">{page?.label || "GreenPeak"}</span>
            </div>
            <div className="hidden xl:block w-64">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                        data-testid="global-search"
                        disabled
                        title="Global search is not connected yet"
                        aria-label="Global search (unavailable)"
                        type="search"
                        placeholder="Search workspace"
                        className="w-full pl-9 pr-3 py-2 bg-[#f5f7f6] border border-transparent rounded-md text-xs disabled:cursor-not-allowed"
                    />
                </div>
            </div>

            <button
                data-testid="topbar-notifications"
                disabled
                title="Notifications are not connected yet"
                className="hidden sm:block p-2 rounded-md text-slate-400 relative focus-ring"
                aria-label="Notifications (unavailable)"
            >
                <Bell className="w-5 h-5" />
            </button>

            <div className="relative">
                <button
                    data-testid="topbar-profile"
                    aria-expanded={menuOpen}
                    aria-label="Account menu"
                    onClick={() => setMenuOpen((v) => !v)}
                    className="flex items-center gap-2.5 sm:pl-5 sm:border-l border-slate-200 py-1.5 rounded-md hover:bg-slate-50 focus-ring"
                >
                    <div className="w-9 h-9 rounded-full bg-[#e9eee3] text-forest-800 flex items-center justify-center text-xs font-bold border border-[#dce3d4]">
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
                        <div data-testid="profile-menu-backdrop" className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)}></div>
                        <div data-testid="profile-menu" className="absolute right-0 top-full mt-3 w-56 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-20">
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
    const [mobileOpen, setMobileOpen] = useState(false);
    const location = useLocation();
    useEffect(() => { setMobileOpen(false); }, [location.pathname]);
    useEffect(() => {
        if (!mobileOpen) return;
        const onKey = (event) => { if (event.key === "Escape") setMobileOpen(false); };
        const oldOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        window.addEventListener("keydown", onKey);
        return () => { document.body.style.overflow = oldOverflow; window.removeEventListener("keydown", onKey); };
    }, [mobileOpen]);
    return (
        <div className="workspace flex min-h-screen">
            {mobileOpen && <button data-testid="mobile-sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" className="fixed inset-0 z-30 bg-[#102a23]/40 backdrop-blur-sm lg:hidden" />}
            <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} mobileOpen={mobileOpen} closeMobile={() => setMobileOpen(false)} />
            <div className="flex-1 flex flex-col min-w-0">
                <Topbar openMobile={() => setMobileOpen(true)} />
                <main className="workspace-main flex-1 p-4 sm:p-6 lg:p-8 animate-fade-in">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;
