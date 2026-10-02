import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { statusColor } from "../lib/format";
import { Dialog, DialogContent, DialogTitle } from "./ui/dialog";

const slug = (value) => String(value || "item").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const useTestId = (name) => `${slug(name)}-${React.useId().replace(/[^a-z0-9]/gi, "").toLowerCase()}`;

export const PageHeader = ({ title, description, actions, breadcrumbs = [] }) => (
    <div className="mb-8" data-testid={`page-header-${slug(title)}`}>
        {breadcrumbs.length > 0 && (
            <nav className="flex flex-wrap items-center text-xs text-slate-500 mb-3" aria-label="Breadcrumb">
                {breadcrumbs.map((b, i) => (
                    <React.Fragment key={i}>
                        {i > 0 && <ChevronRight className="w-3 h-3 mx-1 text-slate-300" />}
                        {b.to ? (
                            <Link data-testid={`breadcrumb-${slug(b.label)}`} to={b.to} className="hover:text-forest-700 transition-colors">{b.label}</Link>
                        ) : (
                            <span className="text-slate-700">{b.label}</span>
                        )}
                    </React.Fragment>
                ))}
            </nav>
        )}
        <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0">
                <h1 data-testid="page-title" className="font-heading text-4xl font-bold leading-tight text-[#192b25] break-words">{title}</h1>
                {description && <p data-testid="page-description" className="text-sm text-slate-500 mt-2 max-w-2xl leading-relaxed">{description}</p>}
            </div>
            {actions && <div className="flex items-center flex-wrap gap-2 pt-1">{actions}</div>}
        </div>
    </div>
);

export const StatusBadge = ({ status, children, ...props }) => (
    <span data-testid={useTestId(`status-${status}`)} className={`erp-status inline-flex items-center gap-1.5 rounded-full font-bold ${statusColor(status)}`} {...props}>
        {children || status?.replace(/_/g, " ")}
    </span>
);

export const Card = ({ children, className = "", ...props }) => (
    <div className={`erp-surface ${className}`} {...props}>{children}</div>
);

export const CardHeader = ({ title, action, description }) => (
    <div className="erp-panel-header flex items-start justify-between gap-3">
        <div className="min-w-0">
            <h3 data-testid={useTestId(`section-${title}`)} className="font-heading text-base font-bold text-[#192b25]">{title}</h3>
            {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
        </div>
        {action}
    </div>
);

export const Button = React.forwardRef(({
    variant = "primary", size = "md", children, className = "", ...props
}, ref) => {
    const testId = useTestId(`button-${typeof children === "string" ? children : variant}`);
    const base = "erp-button inline-flex items-center justify-center gap-2 font-bold transition-colors focus-ring disabled:opacity-50 disabled:pointer-events-none rounded-md";
    const sizes = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2 text-sm", lg: "px-5 py-3 text-sm" };
    const variants = {
        primary: "bg-forest-700 text-white hover:bg-forest-800",
        secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
        outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300",
        ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
        danger: "bg-rose-600 text-white hover:bg-rose-700",
        success: "bg-emerald-600 text-white hover:bg-emerald-700",
    };
    return (
        <button ref={ref} data-testid={testId} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    );
});

export const Input = React.forwardRef(({ className = "", ...props }, ref) => (
    <input
        ref={ref}
        data-testid={useTestId(`input-${props.name || props.type || "text"}`)}
        className={`erp-control h-10 w-full px-3 text-sm bg-white border border-slate-200 rounded-md focus-ring placeholder:text-slate-400 ${className}`}
        {...props}
    />
));

export const Textarea = React.forwardRef(({ className = "", ...props }, ref) => (
    <textarea
        ref={ref}
        data-testid={useTestId(`textarea-${props.name || "text"}`)}
        className={`erp-control w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md focus-ring placeholder:text-slate-400 ${className}`}
        {...props}
    />
));

export const Select = React.forwardRef(({ className = "", children, ...props }, ref) => (
    <select
        ref={ref}
        data-testid={useTestId(`select-${props.name || "option"}`)}
        className={`erp-control h-10 w-full px-3 text-sm bg-white border border-slate-200 rounded-md focus-ring ${className}`}
        {...props}
    >
        {children}
    </select>
));

export const Label = ({ children, required, className = "", ...props }) => (
    <label className={`block text-xs font-bold text-slate-600 mb-2 ${className}`} {...props}>
        {children}{required && <span className="text-rose-500 ml-1">*</span>}
    </label>
);

export const EmptyState = ({ title, description, icon: Icon, action }) => (
    <div data-testid={useTestId(`empty-${title}`)} className="flex flex-col items-center justify-center text-center py-14 px-6 text-slate-500">
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
    const sizes = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" };
    return (
        <Dialog open={open} onOpenChange={(value) => { if (!value) onClose(); }}>
            <DialogContent data-testid="modal" aria-describedby={undefined}
                className={`flex flex-col gap-0 p-0 w-[calc(100%-2rem)] ${sizes[size]} max-h-[90dvh] rounded-lg border-slate-200`}>
                <div className="px-6 py-5 pr-14 border-b border-slate-200">
                    <DialogTitle data-testid="modal-title" className="font-heading font-bold text-lg leading-snug text-[#192b25]">{title}</DialogTitle>
                </div>
                <div className="erp-dialog-body flex-1 min-h-0 overflow-y-auto erp-scroll p-5 sm:p-6">{children}</div>
            </DialogContent>
        </Dialog>
    );
};

/** Simple data table shell: pass `columns=[{key,label,render,sortable}]` and `rows` */
export const DataTable = ({ columns, rows, loading, empty, rowKey = "id", testId = "data-table" }) => {
    if (loading) return <TableSkeleton cols={columns.length} />;
    if (!rows || rows.length === 0) return empty || <EmptyState title="No records" />;
    return (
        <div className="erp-table-scroll overflow-x-auto erp-scroll" role="region" aria-label="Data table" tabIndex={0} data-testid={`${testId}-scroll`}>
            <table className="erp-table min-w-full text-sm" data-testid={testId}>
                <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/60">
                        {columns.map((c) => (
                            <th key={c.key} scope="col" data-testid={`${testId}-header-${c.key}`} className="text-left text-[11px] font-semibold text-slate-500 whitespace-nowrap">
                                {c.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                    {rows.map((r) => (
                        <tr key={r[rowKey]} className="hover:bg-slate-50/60 transition-colors">
                            {columns.map((c) => (
                                <td key={c.key} data-testid={`${testId}-${r[rowKey]}-${c.key}`} className="text-slate-700 align-middle">
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
