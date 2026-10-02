import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, CheckCircle2, Truck } from "lucide-react";
import {
    PageHeader, Card, Button, Input, Label, Modal, DataTable, StatusBadge,
    EmptyState, Textarea,
} from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtDate } from "../lib/format";
import { useAuth } from "../lib/auth";

const EMPTY = { name: "", legal_name: "", gstin: "", pan: "", contact_person: "", email: "", phone: "", address: "", city: "", state: "", pincode: "", payment_terms_days: 30, notes: "" };

const Suppliers = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [search, setSearch] = useState("");
    const [open, setOpen] = useState(false);
    const [form, setForm] = useState(EMPTY);
    const [editing, setEditing] = useState(null);

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["suppliers", search],
        queryFn: async () => (await endpoints.suppliers.list({ search: search || undefined })).data,
    });

    const save = useMutation({
        mutationFn: async () => {
            if (editing) return endpoints.suppliers.update(editing.id, form);
            return endpoints.suppliers.create(form);
        },
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); setOpen(false); setEditing(null); setForm(EMPTY); },
    });

    const approve = useMutation({
        mutationFn: (id) => endpoints.suppliers.approve(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["suppliers"] }),
    });

    const openCreate = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
    const openEdit = (s) => { setEditing(s); setForm({ ...EMPTY, ...s }); setOpen(true); };

    const columns = [
        { key: "code", label: "Code", render: (r) => <span className="font-mono text-xs">{r.code}</span> },
        {
            key: "name", label: "Name", render: (r) => (
                <div>
                    <div className="font-medium text-slate-900">{r.name}</div>
                    <div className="text-[11px] text-slate-500">{r.email || r.phone || "—"}</div>
                </div>
            )
        },
        { key: "gstin", label: "GSTIN", render: (r) => <span className="font-mono text-xs">{r.gstin || "—"}</span> },
        { key: "city", label: "Location", render: (r) => <span className="text-xs">{[r.city, r.state].filter(Boolean).join(", ") || "—"}</span> },
        { key: "terms", label: "Terms", render: (r) => <span className="text-xs">Net {r.payment_terms_days}d</span> },
        {
            key: "status", label: "Approval",
            render: (r) => (
                <div className="flex items-center gap-2">
                    <StatusBadge status={r.is_approved ? "APPROVED" : "PENDING_APPROVAL"}>
                        {r.is_approved ? "Approved" : "Pending"}
                    </StatusBadge>
                    {!r.is_approved && hasPermission("supplier:approve") && (
                        <button data-testid={`approve-supplier-${r.id}`} className="text-xs text-forest-700 hover:underline flex items-center gap-1"
                            onClick={() => approve.mutate(r.id)}>
                            <CheckCircle2 className="w-3 h-3" /> Approve
                        </button>
                    )}
                </div>
            )
        },
        {
            key: "actions", label: "", render: (r) => hasPermission("supplier:write") && (
                <button data-testid={`edit-supplier-${r.id}`} onClick={() => openEdit(r)} className="text-xs text-slate-500 hover:text-forest-700">Edit</button>
            )
        },
    ];

    return (
        <div data-testid="suppliers-page">
            <PageHeader
                title="Suppliers"
                description="Approved supplier directory for raw materials, packaging and finished-goods procurement."
                breadcrumbs={[{ label: "Catalog" }, { label: "Suppliers" }]}
                actions={hasPermission("supplier:write") && (
                    <Button data-testid="new-supplier-btn" onClick={openCreate}><Plus className="w-4 h-4" /> New supplier</Button>
                )}
            />

            <Card className="mb-4">
                <div className="p-4">
                    <div className="relative max-w-sm">
                        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                        <Input data-testid="supplier-search" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, code, email..." />
                    </div>
                </div>
            </Card>

            <Card>
                <DataTable testId="suppliers-table" columns={columns} rows={rows} loading={isLoading}
                    empty={<EmptyState icon={Truck} title="No suppliers yet" />} />
            </Card>

            <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit supplier" : "New supplier"} size="lg">
                <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2"><Label required>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                    <div><Label>Legal name</Label><Input value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} /></div>
                    <div><Label>GSTIN</Label><Input value={form.gstin} onChange={(e) => setForm({ ...form, gstin: e.target.value })} /></div>
                    <div><Label>PAN</Label><Input value={form.pan} onChange={(e) => setForm({ ...form, pan: e.target.value })} /></div>
                    <div><Label>Contact person</Label><Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
                    <div><Label>Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                    <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                    <div className="col-span-2"><Label>Address</Label><Textarea rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
                    <div><Label>City</Label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
                    <div><Label>State</Label><Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></div>
                    <div><Label>Pincode</Label><Input value={form.pincode} onChange={(e) => setForm({ ...form, pincode: e.target.value })} /></div>
                    <div><Label>Payment terms (days)</Label><Input type="number" value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: parseInt(e.target.value) || 0 })} /></div>
                    <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
                </div>
                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="supplier-form-save" onClick={() => save.mutate()} disabled={!form.name || save.isPending}>{save.isPending ? "Saving..." : (editing ? "Save" : "Create")}</Button>
                </div>
            </Modal>
        </div>
    );
};

export default Suppliers;
