import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { PageHeader, Card, DataTable, StatusBadge, EmptyState, Select, Label } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtDateTime } from "../lib/format";

const Audit = () => {
    const [action, setAction] = useState("");
    const [entity, setEntity] = useState("");

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["audit", action, entity],
        queryFn: async () => (await endpoints.audit({ action: action || undefined, entity_type: entity || undefined, limit: 200 })).data,
    });

    const columns = [
        { key: "when", label: "When", render: (r) => <span className="text-xs text-slate-500">{fmtDateTime(r.created_at)}</span> },
        { key: "action", label: "Action", render: (r) => <StatusBadge status={r.action} /> },
        { key: "entity", label: "Entity", render: (r) => <span className="text-xs"><strong>{r.entity_type}</strong>{r.entity_id ? <span className="font-mono text-slate-400 ml-1">{r.entity_id.slice(0, 8)}</span> : null}</span> },
        { key: "user", label: "User", render: (r) => <span className="text-xs font-mono">{r.user_email || "—"}</span> },
        { key: "details", label: "Details", render: (r) => <span className="text-xs text-slate-500 line-clamp-1">{JSON.stringify(r.details || {})}</span> },
    ];

    return (
        <div data-testid="audit-page">
            <PageHeader title="Audit log" description="Immutable record of every business action across the ERP."
                breadcrumbs={[{ label: "Admin" }, { label: "Audit log" }]} />

            <Card className="mb-4"><div className="p-4 flex gap-3 items-end flex-wrap">
                <div className="w-44"><Label>Action</Label>
                    <Select value={action} onChange={(e) => setAction(e.target.value)}>
                        <option value="">All</option>
                        {["CREATE", "UPDATE", "DELETE", "APPROVE", "LOGIN", "LOGOUT"].map((a) => <option key={a} value={a}>{a}</option>)}
                    </Select></div>
                <div className="w-56"><Label>Entity</Label>
                    <Select value={entity} onChange={(e) => setEntity(e.target.value)}>
                        <option value="">All</option>
                        {["Product", "Supplier", "Customer", "PurchaseOrder", "SalesOrder", "GoodsReceipt", "InventoryBatch", "User", "Warehouse"].map((a) => <option key={a} value={a}>{a}</option>)}
                    </Select></div>
            </div></Card>

            <Card>
                <DataTable testId="audit-table" columns={columns} rows={rows} loading={isLoading} empty={<EmptyState icon={FileText} title="No audit entries" />} />
            </Card>
        </div>
    );
};

export default Audit;
