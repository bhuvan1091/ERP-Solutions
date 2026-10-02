import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Users as UsersIcon } from "lucide-react";
import { PageHeader, Card, Button, Input, Select, Label, Modal, DataTable, StatusBadge, EmptyState, Textarea } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtCurrency } from "../lib/format";
import { useAuth } from "../lib/auth";

const EMPTY = { name: "", customer_type: "RETAIL", gstin: "", contact_person: "", email: "", phone: "", billing_address: "", shipping_address: "", city: "", state: "", pincode: "", credit_limit: 0, payment_terms_days: 0 };

const Customers = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [search, setSearch] = useState(""); const [type, setType] = useState("");
    const [open, setOpen] = useState(false); const [editing, setEditing] = useState(null); const [form, setForm] = useState(EMPTY);

    const { data: rows = [], isLoading } = useQuery({
        queryKey: ["customers", search, type],
        queryFn: async () => (await endpoints.customers.list({ search: search || undefined, customer_type: type || undefined })).data,
    });

    const save = useMutation({
        mutationFn: async () => {
            const payload = { ...form, credit_limit: Number(form.credit_limit), payment_terms_days: Number(form.payment_terms_days) };
            if (editing) return endpoints.customers.update(editing.id, payload);
            return endpoints.customers.create(payload);
        },
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["customers"] }); setOpen(false); setEditing(null); setForm(EMPTY); },
    });

    const openCreate = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
    const openEdit = (c) => { setEditing(c); setForm({ ...EMPTY, ...c }); setOpen(true); };

    const columns = [
        { key: "code", label: "Code", render: (r) => <span className="font-mono text-xs">{r.code}</span> },
        { key: "name", label: "Name", render: (r) => <div><div className="font-medium text-slate-900">{r.name}</div><div className="text-[11px] text-slate-500">{r.email || r.phone || "—"}</div></div> },
        { key: "type", label: "Type", render: (r) => <StatusBadge status="ACTIVE">{r.customer_type}</StatusBadge> },
        { key: "city", label: "Location", render: (r) => <span className="text-xs">{[r.city, r.state].filter(Boolean).join(", ") || "—"}</span> },
        { key: "credit", label: "Credit limit", render: (r) => <span className="tabular-nums text-xs">{fmtCurrency(r.credit_limit)}</span> },
        { key: "terms", label: "Terms", render: (r) => <span className="text-xs">Net {r.payment_terms_days}d</span> },
        { key: "actions", label: "", render: (r) => hasPermission("customer:write") && <button data-testid={`edit-customer-${r.id}`} className="text-xs text-slate-500 hover:text-forest-700" onClick={() => openEdit(r)}>Edit</button> },
    ];

    return (
        <div data-testid="customers-page">
            <PageHeader title="Customers" description="Retailers, wholesalers, distributors and direct consumers."
                breadcrumbs={[{ label: "Catalog" }, { label: "Customers" }]}
                actions={hasPermission("customer:write") && <Button data-testid="new-customer-btn" onClick={openCreate}><Plus className="w-4 h-4" /> New customer</Button>} />

            <Card className="mb-4">
                <div className="p-4 flex gap-3 items-end flex-wrap">
                    <div className="flex-1 min-w-56"><Label>Search</Label>
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                            <Input data-testid="customer-search" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, code, email..." />
                        </div></div>
                    <div className="w-44"><Label>Type</Label>
                        <Select value={type} onChange={(e) => setType(e.target.value)}>
                            <option value="">All</option><option value="RETAIL">Retail</option>
                            <option value="WHOLESALE">Wholesale</option><option value="DISTRIBUTOR">Distributor</option>
                        </Select></div>
                </div>
            </Card>

            <Card>
                <DataTable testId="customers-table" columns={columns} rows={rows} loading={isLoading} empty={<EmptyState icon={UsersIcon} title="No customers yet" />} />
            </Card>

            <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit customer" : "New customer"} size="lg">
                <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2"><Label required>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                    <div><Label>Customer type</Label>
                        <Select value={form.customer_type} onChange={(e) => setForm({ ...form, customer_type: e.target.value })}>
                            <option value="RETAIL">Retail</option><option value="WHOLESALE">Wholesale</option>
                            <option value="DISTRIBUTOR">Distributor</option><option value="DIRECT">Direct</option>
                        </Select></div>
                    <div><Label>GSTIN</Label><Input value={form.gstin} onChange={(e) => setForm({ ...form, gstin: e.target.value })} /></div>
                    <div><Label>Contact person</Label><Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
                    <div><Label>Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                    <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                    <div className="col-span-2"><Label>Billing address</Label><Textarea rows={2} value={form.billing_address} onChange={(e) => setForm({ ...form, billing_address: e.target.value })} /></div>
                    <div className="col-span-2"><Label>Shipping address</Label><Textarea rows={2} value={form.shipping_address} onChange={(e) => setForm({ ...form, shipping_address: e.target.value })} /></div>
                    <div><Label>City</Label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
                    <div><Label>State</Label><Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></div>
                    <div><Label>Pincode</Label><Input value={form.pincode} onChange={(e) => setForm({ ...form, pincode: e.target.value })} /></div>
                    <div><Label>Credit limit (₹)</Label><Input type="number" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} /></div>
                    <div><Label>Payment terms (days)</Label><Input type="number" value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: e.target.value })} /></div>
                </div>
                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="customer-form-save" onClick={() => save.mutate()} disabled={!form.name || save.isPending}>{save.isPending ? "Saving..." : (editing ? "Save" : "Create")}</Button>
                </div>
            </Modal>
        </div>
    );
};

export default Customers;
