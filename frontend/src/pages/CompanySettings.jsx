import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, Image as ImageIcon, Trash2, Save, Building2 } from "lucide-react";
import { PageHeader, Card, CardHeader, Button, Input, Label, Textarea, EmptyState } from "../components/UI";
import { endpoints } from "../lib/api";

const CompanySettings = () => {
    const qc = useQueryClient();
    const fileRef = useRef();
    const { data } = useQuery({ queryKey: ["company"], queryFn: async () => (await endpoints.company.get()).data });
    const [form, setForm] = useState({});
    const [saved, setSaved] = useState(false);
    const [logoErr, setLogoErr] = useState("");

    useEffect(() => { if (data) setForm(data); }, [data]);

    const save = useMutation({
        mutationFn: () => endpoints.company.update(form),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["company"] }); setSaved(true); setTimeout(() => setSaved(false), 2000); },
    });

    const onFile = (e) => {
        setLogoErr("");
        const f = e.target.files?.[0];
        if (!f) return;
        if (!/^image\//.test(f.type)) { setLogoErr("Please choose an image file (PNG / JPG)."); return; }
        if (f.size > 500 * 1024) { setLogoErr("Logo must be under 500KB."); return; }
        const reader = new FileReader();
        reader.onload = () => setForm({ ...form, logo_base64: reader.result });
        reader.readAsDataURL(f);
    };

    const upd = (k, v) => setForm({ ...form, [k]: v });

    if (!data) return <EmptyState title="Loading..." />;

    return (
        <div data-testid="settings-page">
            <PageHeader title="Company Settings"
                description="Branding, bank details and finance email. These automatically appear on every invoice PDF."
                breadcrumbs={[{ label: "Admin" }, { label: "Company Settings" }]}
                actions={<Button data-testid="save-settings" onClick={() => save.mutate()} disabled={save.isPending}><Save className="w-4 h-4" /> {save.isPending ? "Saving..." : (saved ? "Saved ✓" : "Save changes")}</Button>}
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Logo & branding */}
                <Card>
                    <CardHeader title="Logo & branding" description="Shown at the top-left of every invoice PDF" />
                    <div className="p-4 space-y-4">
                        <div className="flex items-center gap-4">
                            {form.logo_base64 ? (
                                <img src={form.logo_base64} alt="Company logo" className="w-24 h-24 object-contain rounded-md border border-slate-200 bg-white p-2" data-testid="logo-preview" />
                            ) : (
                                <div className="w-24 h-24 rounded-md border-2 border-dashed border-slate-200 flex items-center justify-center text-slate-400"><ImageIcon className="w-8 h-8" /></div>
                            )}
                            <div className="flex-1">
                                <input ref={fileRef} data-testid="logo-upload" type="file" accept="image/png,image/jpeg,image/webp" onChange={onFile} className="hidden" />
                                <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}><Upload className="w-3.5 h-3.5" /> Upload logo</Button>
                                {form.logo_base64 && (
                                    <Button variant="ghost" size="sm" className="ml-2 text-rose-600" onClick={() => upd("logo_base64", null)}><Trash2 className="w-3.5 h-3.5" /> Remove</Button>
                                )}
                                <p className="text-[11px] text-slate-500 mt-2">PNG / JPG / WebP • Max 500 KB • Square recommended</p>
                                {logoErr && <p className="text-xs text-rose-700 mt-1">{logoErr}</p>}
                            </div>
                        </div>
                        <div><Label>Company name</Label><Input value={form.name || ""} onChange={(e) => upd("name", e.target.value)} /></div>
                        <div><Label>Legal name</Label><Input value={form.legal_name || ""} onChange={(e) => upd("legal_name", e.target.value)} /></div>
                        <div className="grid grid-cols-2 gap-2">
                            <div><Label>GSTIN</Label><Input value={form.gstin || ""} onChange={(e) => upd("gstin", e.target.value)} /></div>
                            <div><Label>FSSAI license</Label><Input value={form.fssai_license || ""} onChange={(e) => upd("fssai_license", e.target.value)} /></div>
                        </div>
                        <div><Label>Address</Label><Textarea rows={3} value={form.address || ""} onChange={(e) => upd("address", e.target.value)} /></div>
                    </div>
                </Card>

                {/* Bank details */}
                <Card>
                    <CardHeader title="Bank details" description="Shown in the footer of customer invoices" />
                    <div className="p-4 space-y-3">
                        <div><Label>Bank name</Label><Input data-testid="bank_name" value={form.bank_name || ""} onChange={(e) => upd("bank_name", e.target.value)} placeholder="HDFC Bank" /></div>
                        <div><Label>Account holder name</Label><Input value={form.bank_account_name || ""} onChange={(e) => upd("bank_account_name", e.target.value)} /></div>
                        <div><Label>Account number</Label><Input data-testid="bank_account_number" value={form.bank_account_number || ""} onChange={(e) => upd("bank_account_number", e.target.value)} /></div>
                        <div className="grid grid-cols-2 gap-2">
                            <div><Label>IFSC</Label><Input value={form.bank_ifsc || ""} onChange={(e) => upd("bank_ifsc", e.target.value)} placeholder="HDFC0001234" /></div>
                            <div><Label>Branch</Label><Input value={form.bank_branch || ""} onChange={(e) => upd("bank_branch", e.target.value)} /></div>
                        </div>
                        <div><Label>UPI ID</Label><Input value={form.upi_id || ""} onChange={(e) => upd("upi_id", e.target.value)} placeholder="greenpeak@hdfcbank" /></div>
                    </div>
                </Card>

                {/* Email + default invoice notes */}
                <Card>
                    <CardHeader title="Email & defaults" description="Used when sending invoices to customers" />
                    <div className="p-4 space-y-3">
                        <div>
                            <Label>Finance reply-to email</Label>
                            <Input data-testid="finance_email" type="email" value={form.finance_email || ""} onChange={(e) => upd("finance_email", e.target.value)} placeholder="finance@yourcompany.com" />
                            <p className="text-[11px] text-slate-500 mt-1">Customers' replies to invoice emails will come here.</p>
                        </div>
                        <div>
                            <Label>Default invoice terms</Label>
                            <Textarea rows={6} value={form.invoice_notes || ""} onChange={(e) => upd("invoice_notes", e.target.value)}
                                placeholder="1. Payment due within the stated due date.&#10;2. Goods once sold are not returnable except as per our returns policy.&#10;..." />
                            <p className="text-[11px] text-slate-500 mt-1">Shown in the Terms &amp; Conditions block on every invoice. Use &lt;br/&gt; for line breaks.</p>
                        </div>
                    </div>
                </Card>
            </div>
            {save.isError && <div className="mt-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md px-3 py-2">{save.error?.response?.data?.detail || "Could not save"}</div>}
        </div>
    );
};

export default CompanySettings;
