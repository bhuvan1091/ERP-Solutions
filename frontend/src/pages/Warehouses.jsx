import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Warehouse as WhIcon } from "lucide-react";
import { PageHeader, Card, Button, Input, Label, Modal, DataTable, EmptyState } from "../components/UI";
import { endpoints } from "../lib/api";
import { useAuth } from "../lib/auth";

const Warehouses = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [open, setOpen] = useState(false);
    const [form, setForm] = useState({ code: "", name: "", address: "", city: "", state: "", pincode: "" });

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["warehouses"],
        queryFn: async () => (await endpoints.warehouses.list()).data,
    });

    const create = useMutation({
        mutationFn: () => endpoints.warehouses.create(form),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["warehouses"] }); setOpen(false); setForm({ code: "", name: "", address: "", city: "", state: "", pincode: "" }); },
    });

    const columns = [
        { key: "code", label: "Code", render: (r) => <span className="font-mono text-xs">{r.code}</span> },
        { key: "name", label: "Name", render: (r) => <span className="font-medium text-slate-900">{r.name}</span> },
        { key: "address", label: "Address", render: (r) => <span className="text-xs text-slate-600">{[r.address, r.city, r.state, r.pincode].filter(Boolean).join(", ")}</span> },
    ];

    return (
        <div data-testid="warehouses-page">
            <PageHeader title="Warehouses" description="Storage facilities. Stock is tracked by product × warehouse × batch for full traceability."
                breadcrumbs={[{ label: "Inventory" }, { label: "Warehouses" }]}
                actions={hasPermission("warehouse:write") && <Button data-testid="new-warehouse-btn" onClick={() => setOpen(true)}><Plus className="w-4 h-4" /> New warehouse</Button>} />
            <Card>
                <DataTable testId="warehouses-table" columns={columns} rows={rows} loading={isLoading} empty={<EmptyState icon={WhIcon} title="No warehouses yet" />} />
            </Card>
            <Modal open={open} onClose={() => setOpen(false)} title="New warehouse">
                <div className="space-y-3">
                    <div><Label required>Code</Label><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="BLR-MAIN" /></div>
                    <div><Label required>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                    <div><Label>Address</Label><Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
                    <div className="grid grid-cols-3 gap-2">
                        <div><Label>City</Label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
                        <div><Label>State</Label><Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></div>
                        <div><Label>Pincode</Label><Input value={form.pincode} onChange={(e) => setForm({ ...form, pincode: e.target.value })} /></div>
                    </div>
                </div>
                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="warehouse-form-save" onClick={() => create.mutate()} disabled={!form.code || !form.name}>Create</Button>
                </div>
            </Modal>
        </div>
    );
};

export default Warehouses;
