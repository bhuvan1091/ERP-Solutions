import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { statusColor } from "../lib/format";

export const PageHeader = ({ title, description, actions, breadcrumbs = [] }) => (
    <div className="mb-6">
        {breadcrumbs.length > 0 && (
            <nav className="flex items-center text-xs text-slate-500 mb-2" aria-label="Breadcrumb">
                {breadcrumbs.map((b, i) => (
                    <React.Fragment key={i}>
                        {i > 0 && <ChevronRight className="w-3 h-3 mx-1 text-slate-300" />}
                        {b.to ? (
                            <Link to={b.to} className="hover:text-forest-700 transition-colors">{b.label}</Link>
                        ) : (
                            <span className="text-slate-700">{b.label}</span>
                        )}
                    </React.Fragment>
                ))}
            </nav>
        )}
        <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
                <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
                {description && <p className="text-sm text-slate-500 mt-1 max-w-2xl">{description}</p>}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    </div>
);

export const StatusBadge = ({ status, children }) => (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${statusColor(status)}`}>
        {children || status?.replace(/_/g, " ")}
    </span>
);

export const Card = ({ children, className = "" }) => (
    <div className={`bg-white rounded-md border border-slate-200 shadow-sm ${className}`}>{children}</div>
);

export const CardHeader = ({ title, action, description }) => (
    <div className="flex items-start justify-between gap-2 px-4 py-3 border-b border-slate-100">
        <div>
            <h3 className="font-heading text-sm font-semibold text-slate-900">{title}</h3>
            {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
        </div>
        {action}
    </div>
);

export const Button = React.forwardRef(({
    variant = "primary", size = "md", children, className = "", ...props
}, ref) => {
    const base = "inline-flex items-center justify-center gap-1.5 font-medium transition-colors focus-ring disabled:opacity-50 disabled:pointer-events-none rounded-md";
    const sizes = { sm: "h-8 px-3 text-xs", md: "h-9 px-4 text-sm", lg: "h-10 px-5 text-sm" };
    const variants = {
        primary: "bg-forest-700 text-white hover:bg-forest-800",
        secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
        outline: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
        danger: "bg-rose-600 text-white hover:bg-rose-700",
        success: "bg-emerald-600 text-white hover:bg-emerald-700",
    };
    return (
        <button ref={ref} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    );
});

export const Input = React.forwardRef(({ className = "", ...props }, ref) => (
    <input
        ref={ref}
        className={`h-9 w-full px-3 text-sm bg-white border border-slate-200 rounded-md focus-ring placeholder:text-slate-400 ${className}`}
        {...props}
    />
));

export const Textarea = React.forwardRef(({ className = "", ...props }, ref) => (
    <textarea
        ref={ref}
        className={`w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md focus-ring placeholder:text-slate-400 ${className}`}
        {...props}
    />
));

export const Select = React.forwardRef(({ className = "", children, ...props }, ref) => (
    <select
        ref={ref}
        className={`h-9 w-full px-3 text-sm bg-white border border-slate-200 rounded-md focus-ring ${className}`}
        {...props}
    >
        {children}
    </select>
));

export const Label = ({ children, required, className = "", ...props }) => (
    <label className={`block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1 ${className}`} {...props}>
        {children}{required && <span className="text-rose-500 ml-1">*</span>}
    </label>
);

export const EmptyState = ({ title, description, icon: Icon, action }) => (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6 text-slate-500">
        {Icon && <Icon className="w-10 h-10 text-slate-300 mb-3" />}
        <div className="font-heading font-semibold text-slate-700 text-base mb-1">{title}</div>
        {description && <p className="text-sm max-w-md mb-4">{description}</p>}
        {action}
    </div>
);

export const TableSkeleton = ({ cols = 5, rows = 6 }) => (
    <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="grid gap-4 px-4 py-3" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0,1fr))` }}>
                {Array.from({ length: cols }).map((__, j) => (
                    <div key={j} className="h-4 shimmer rounded"></div>
                ))}
            </div>
        ))}
    </div>
);

export const Modal = ({ open, onClose, title, children, size = "md" }) => {
    if (!open) return null;
    const sizes = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" };
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 animate-fade-in" data-testid="modal-backdrop" onClick={onClose}>
            <div
                className={`bg-white rounded-md border border-slate-200 shadow-xl w-full ${sizes[size]} max-h-[90vh] flex flex-col`}
                onClick={(e) => e.stopPropagation()}
                data-testid="modal"
            >
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
                    <h3 className="font-heading font-semibold text-slate-900">{title}</h3>
                    <button data-testid="modal-close" onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl leading-none">×</button>
                </div>
                <div className="flex-1 overflow-y-auto erp-scroll p-5">{children}</div>
            </div>
        </div>
    );
};

/** Simple data table shell: pass `columns=[{key,label,render,sortable}]` and `rows` */
export const DataTable = ({ columns, rows, loading, empty, rowKey = "id", testId = "data-table" }) => {
    if (loading) return <TableSkeleton cols={columns.length} />;
    if (!rows || rows.length === 0) return empty || <EmptyState title="No records" />;
    return (
        <div className="overflow-x-auto erp-scroll">
            <table className="min-w-full text-sm" data-testid={testId}>
                <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/60">
                        {columns.map((c) => (
                            <th key={c.key} className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500 whitespace-nowrap">
                                {c.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                    {rows.map((r) => (
                        <tr key={r[rowKey]} className="hover:bg-slate-50/60 transition-colors">
                            {columns.map((c) => (
                                <td key={c.key} className="px-4 py-3 text-slate-700 align-middle">
                                    {c.render ? c.render(r) : r[c.key]}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
