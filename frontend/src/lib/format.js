export const fmtCurrency = (v, currency = "INR") => {
    const n = Number(v || 0);
    try {
        return new Intl.NumberFormat("en-IN", {
            style: "currency", currency, maximumFractionDigits: 0,
        }).format(n);
    } catch {
        return `₹${n.toLocaleString("en-IN")}`;
    }
};

export const fmtNumber = (v, digits = 0) => Number(v || 0).toLocaleString("en-IN", {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
});

export const fmtDate = (d) => {
    if (!d) return "—";
    const date = typeof d === "string" ? new Date(d) : d;
    return date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "2-digit" });
};

export const fmtDateTime = (d) => {
    if (!d) return "—";
    const date = typeof d === "string" ? new Date(d) : d;
    return date.toLocaleString("en-IN", { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
};

export const statusColor = (s) => {
    const map = {
        ACTIVE: "bg-emerald-100 text-emerald-800",
        DRAFT: "bg-slate-100 text-slate-700",
        DISCONTINUED: "bg-slate-200 text-slate-600",
        PENDING_APPROVAL: "bg-amber-100 text-amber-800",
        APPROVED: "bg-emerald-100 text-emerald-800",
        PARTIALLY_RECEIVED: "bg-blue-100 text-blue-800",
        RECEIVED: "bg-emerald-100 text-emerald-800",
        CANCELLED: "bg-rose-100 text-rose-800",
        CONFIRMED: "bg-blue-100 text-blue-800",
        ALLOCATED: "bg-indigo-100 text-indigo-800",
        PARTIALLY_DISPATCHED: "bg-sky-100 text-sky-800",
        DISPATCHED: "bg-emerald-100 text-emerald-800",
        INVOICED: "bg-emerald-100 text-emerald-800",
        QUARANTINE: "bg-amber-100 text-amber-800",
        RELEASED: "bg-emerald-100 text-emerald-800",
        HOLD: "bg-orange-100 text-orange-800",
        REJECTED: "bg-rose-100 text-rose-800",
        EXPIRED: "bg-rose-100 text-rose-800",
        PAUSED: "bg-amber-100 text-amber-800",
        ENDED: "bg-slate-200 text-slate-700",
        CONNECTED: "bg-emerald-100 text-emerald-800",
    };
    return map[s] || "bg-slate-100 text-slate-700";
};
