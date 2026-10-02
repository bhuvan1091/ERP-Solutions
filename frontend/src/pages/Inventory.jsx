import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Boxes, AlertTriangle } from "lucide-react";
import { PageHeader, Card, CardHeader, Button, Input, Select, Label, Modal, DataTable, StatusBadge, EmptyState } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtDate, fmtNumber, fmtCurrency } from "../lib/format";
import { useAuth } from "../lib/auth";

const Inventory = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("");
    const [whId, setWhId] = useState("");
    const [onlyNear, setOnlyNear] = useState(false);
    const [onlyExpired, setOnlyExpired] = useState(false);
    const [adjOpen, setAdjOpen] = useState(false);
    const [adjBatch, setAdjBatch] = useState(null);
    const [adjForm, setAdjForm] = useState({ quantity_delta: 0, notes: "" });

    const { data: batches = [], isLoading } = useQuery({
        queryKey: ["batches", search, status, whId, onlyNear, onlyExpired],
        queryFn: async () => (await endpoints.inventory.batches({
            search: search || undefined,
            status: status || undefined,
            warehouse_id: whId || undefined,
            near_expiry_days: onlyNear ? 60 : undefined,
            expired_only: onlyExpired || undefined,
        })).data,
    });

    const { data: wh = [] } = useQuery({ queryKey: ["warehouses"], queryFn: async () => (await endpoints.warehouses.list()).data });
    const { data: movements = [] } = useQuery({ queryKey: ["movements"], queryFn: async () => (await endpoints.inventory.movements({ limit: 20 })).data });

    const adjust = useMutation({
        mutationFn: () => endpoints.inventory.adjust({ batch_id: adjBatch.id, quantity_delta: Number(adjForm.quantity_delta), notes: adjForm.notes }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["batches"] }); qc.invalidateQueries({ queryKey: ["movements"] }); setAdjOpen(false); setAdjForm({ quantity_delta: 0, notes: "" }); },
    });

    const release = useMutation({
        mutationFn: (id) => endpoints.inventory.releaseBatch(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["batches"] }),
    });

    const columns = [
        {
            key: "batch", label: "Batch / Product", render: (r) => (
                <div>
                    <div className="font-mono text-xs text-slate-900">{r.batch_number}</div>
                    <div className="text-xs text-slate-700 font-medium">{r.product_name}</div>
                    <div className="text-[10px] text-slate-500">{r.product_sku} • {r.warehouse_name}</div>
                </div>
            )
        },
        { key: "mfg", label: "Mfg → Exp", render: (r) => <div className="text-xs"><div>{fmtDate(r.manufacture_date)}</div><div className="text-slate-400">→ {fmtDate(r.expiry_date)}</div></div> },
        {
            key: "exp", label: "Expiry",
            render: (r) => r.days_to_expiry == null ? <span className="text-xs text-slate-400">—</span> :
                r.days_to_expiry < 0 ? <span className="text-xs text-rose-700 font-semibold">Expired {Math.abs(r.days_to_expiry)}d ago</span> :
                r.days_to_expiry <= 60 ? <span className="text-xs text-amber-700 font-semibold">{r.days_to_expiry}d left</span> :
                <span className="text-xs text-slate-600">{r.days_to_expiry}d</span>
        },
        { key: "qty", label: "On hand / Reserved", render: (r) => <div className="text-xs tabular-nums"><div className="font-semibold">{fmtNumber(r.quantity_on_hand)}</div><div className="text-slate-400">Reserved {fmtNumber(r.quantity_reserved)}</div></div> },
        { key: "avail", label: "Available", render: (r) => <span className="text-xs tabular-nums font-semibold text-forest-700">{fmtNumber(r.quantity_available)}</span> },
        { key: "cost", label: "Cost / unit", render: (r) => <span className="text-xs tabular-nums">{fmtCurrency(r.cost_per_unit)}</span> },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
        {
            key: "actions", label: "", render: (r) => (
                <div className="flex gap-1">
                    {hasPermission("inventory:adjust") && (
                        <button data-testid={`adjust-batch-${r.id}`} className="text-xs text-slate-500 hover:text-forest-700"
                            onClick={() => { setAdjBatch(r); setAdjForm({ quantity_delta: 0, notes: "" }); setAdjOpen(true); }}>Adjust</button>
                    )}
                    {r.status === "QUARANTINE" && hasPermission("quality:release") && (
                        <button data-testid={`release-batch-${r.id}`} className="text-xs text-forest-700 hover:underline"
                            onClick={() => release.mutate(r.id)}>Release</button>
                    )}
                </div>
            )
        },
    ];

    return (
        <div data-testid="inventory-page">
            <PageHeader title="Stock & batches"
                description="Every unit of stock is tied to a product × warehouse × batch. Dispatch uses FEFO (First Expiry First Out)."
                breadcrumbs={[{ label: "Inventory" }, { label: "Stock & batches" }]} />

            <Card className="mb-4">
                <div className="p-4 flex gap-3 items-end flex-wrap">
                    <div className="flex-1 min-w-56"><Label>Search</Label>
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                            <Input data-testid="batch-search" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Batch, product, SKU..." />
                        </div></div>
                    <div className="w-40"><Label>Warehouse</Label>
                        <Select value={whId} onChange={(e) => setWhId(e.target.value)}>
                            <option value="">All</option>
                            {wh.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </Select></div>
                    <div className="w-40"><Label>Status</Label>
                        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
                            <option value="">All</option>
                            <option value="RELEASED">Released</option>
                            <option value="QUARANTINE">Quarantine</option>
                            <option value="HOLD">Hold</option>
                            <option value="REJECTED">Rejected</option>
                            <option value="EXPIRED">Expired</option>
                        </Select></div>
                    <div className="flex gap-2 items-center">
                        <label className="flex items-center gap-1.5 text-xs text-slate-700"><input data-testid="filter-near-exp" type="checkbox" checked={onlyNear} onChange={(e) => setOnlyNear(e.target.checked)} /> Near expiry (60d)</label>
                        <label className="flex items-center gap-1.5 text-xs text-slate-700"><input data-testid="filter-expired" type="checkbox" checked={onlyExpired} onChange={(e) => setOnlyExpired(e.target.checked)} /> Expired only</label>
                    </div>
                </div>
            </Card>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                <Card className="xl:col-span-2">
                    <DataTable testId="batches-table" columns={columns} rows={batches} loading={isLoading}
                        empty={<EmptyState icon={Boxes} title="No batches match your filters" />} />
                </Card>

                <Card>
                    <CardHeader title="Recent stock movements" description="Immutable ledger of every change" />
                    <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto erp-scroll">
                        {movements.length === 0 ? <EmptyState title="No movements" /> : movements.map((m) => (
                            <div key={m.id} className="p-3">
                                <div className="flex justify-between gap-2">
                                    <div className="min-w-0">
                                        <div className="text-xs font-medium text-slate-900 truncate">{m.product_name || m.batch_number}</div>
                                        <div className="text-[10px] text-slate-500">{m.batch_number} • {m.warehouse_name}</div>
                                    </div>
                                    <div className="text-right">
                                        <div className={`text-xs font-semibold tabular-nums ${Number(m.quantity) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                                            {Number(m.quantity) >= 0 ? "+" : ""}{fmtNumber(m.quantity)}
                                        </div>
                                        <div className="text-[10px] text-slate-400">{m.movement_type}</div>
                                    </div>
                                </div>
                                {m.reference_number && <div className="text-[10px] text-slate-400 font-mono mt-0.5">{m.reference_number}</div>}
                            </div>
                        ))}
                    </div>
                </Card>
            </div>

            <Modal open={adjOpen} onClose={() => setAdjOpen(false)} title="Adjust stock">
                {adjBatch && (
                    <div className="space-y-3">
                        <div className="bg-slate-50 rounded-md p-3 text-xs">
                            <div><span className="text-slate-500">Product:</span> <strong>{adjBatch.product_name}</strong></div>
                            <div><span className="text-slate-500">Batch:</span> <span className="font-mono">{adjBatch.batch_number}</span></div>
                            <div><span className="text-slate-500">Current qty:</span> {fmtNumber(adjBatch.quantity_on_hand)}</div>
                        </div>
                        <div><Label required>Quantity delta (+ to add, - to remove)</Label>
                            <Input data-testid="adj-qty" type="number" step="any" value={adjForm.quantity_delta} onChange={(e) => setAdjForm({ ...adjForm, quantity_delta: e.target.value })} /></div>
                        <div><Label>Notes</Label>
                            <Input data-testid="adj-notes" value={adjForm.notes} onChange={(e) => setAdjForm({ ...adjForm, notes: e.target.value })} placeholder="Damage, counting correction..." /></div>
                        {adjust.isError && <div className="text-sm text-rose-700">{adjust.error?.response?.data?.detail}</div>}
                        <div className="flex justify-end gap-2">
                            <Button variant="outline" onClick={() => setAdjOpen(false)}>Cancel</Button>
                            <Button data-testid="adj-submit" onClick={() => adjust.mutate()} disabled={adjust.isPending || Number(adjForm.quantity_delta) === 0}>Save adjustment</Button>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default Inventory;
