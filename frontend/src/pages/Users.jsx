import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Shield } from "lucide-react";
import { PageHeader, Card, Button, Input, Select, Label, Modal, DataTable, StatusBadge, EmptyState } from "../components/UI";
import { endpoints } from "../lib/api";
import { fmtDateTime } from "../lib/format";
import { useAuth } from "../lib/auth";

const UsersPage = () => {
    const qc = useQueryClient();
    const { hasPermission } = useAuth();
    const [open, setOpen] = useState(false);
    const [form, setForm] = useState({ email: "", full_name: "", password: "", role_code: "SALES_REPRESENTATIVE", phone: "" });

    const { data: rows = [], isLoading } = useQuery({ queryKey: ["users"], queryFn: async () => (await endpoints.users.list()).data });
    const { data: roles = [] } = useQuery({ queryKey: ["roles"], queryFn: async () => (await endpoints.roles()).data });

    const create = useMutation({
        mutationFn: () => endpoints.users.create(form),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setOpen(false); setForm({ email: "", full_name: "", password: "", role_code: "SALES_REPRESENTATIVE", phone: "" }); },
    });

    const columns = [
        { key: "email", label: "Email", render: (r) => <div><div className="font-medium text-sm">{r.full_name}</div><div className="text-[11px] text-slate-500 font-mono">{r.email}</div></div> },
        { key: "role", label: "Role", render: (r) => <StatusBadge status="ACTIVE">{r.role_name}</StatusBadge> },
        { key: "phone", label: "Phone", render: (r) => <span className="text-xs">{r.phone || "—"}</span> },
        { key: "last", label: "Last login", render: (r) => <span className="text-xs text-slate-500">{r.last_login_at ? fmtDateTime(r.last_login_at) : "Never"}</span> },
        { key: "active", label: "Status", render: (r) => <StatusBadge status={r.is_active ? "ACTIVE" : "DISCONTINUED"}>{r.is_active ? "Active" : "Inactive"}</StatusBadge> },
    ];

    return (
        <div data-testid="users-page">
            <PageHeader title="Users & Roles"
                description="14 default role templates with permission-based access to ERP modules."
                breadcrumbs={[{ label: "Admin" }, { label: "Users & Roles" }]}
                actions={hasPermission("admin:write") && <Button data-testid="new-user-btn" onClick={() => setOpen(true)}><Plus className="w-4 h-4" /> Invite user</Button>} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <Card className="lg:col-span-2">
                    <DataTable testId="users-table" columns={columns} rows={rows} loading={isLoading} empty={<EmptyState icon={Shield} title="No users yet" />} />
                </Card>
                <Card>
                    <div className="px-4 py-3 border-b border-slate-100">
                        <h3 className="font-heading font-semibold text-sm text-slate-900">Available roles</h3>
                        <p className="text-xs text-slate-500 mt-0.5">Each with pre-configured permissions</p>
                    </div>
                    <div className="divide-y divide-slate-100 max-h-[520px] overflow-y-auto erp-scroll">
                        {roles.map((r) => (
                            <div key={r.id} className="p-3">
                                <div className="flex items-center justify-between">
                                    <div className="text-sm font-medium text-slate-900">{r.name}</div>
                                    <span className="text-[10px] text-slate-500">{r.permissions?.length || 0} perms</span>
                                </div>
                                <div className="text-[10px] text-slate-500 font-mono">{r.code}</div>
                                {r.description && <div className="text-[11px] text-slate-500 mt-1">{r.description}</div>}
                            </div>
                        ))}
                    </div>
                </Card>
            </div>

            <Modal open={open} onClose={() => setOpen(false)} title="Invite new user">
                <div className="space-y-3">
                    <div><Label required>Full name</Label><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
                    <div><Label required>Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                    <div><Label required>Temporary password</Label><Input type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="min 6 chars" /></div>
                    <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                    <div><Label required>Role</Label>
                        <Select value={form.role_code} onChange={(e) => setForm({ ...form, role_code: e.target.value })}>
                            {roles.map((r) => <option key={r.id} value={r.code}>{r.name}</option>)}
                        </Select></div>
                </div>
                {create.isError && <div className="mt-3 text-sm text-rose-700">{create.error?.response?.data?.detail}</div>}
                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button data-testid="user-form-save" onClick={() => create.mutate()} disabled={!form.email || !form.full_name || !form.password || form.password.length < 6}>Create user</Button>
                </div>
            </Modal>
        </div>
    );
};

export default UsersPage;
