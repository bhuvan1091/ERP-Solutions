import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { Loader2, Leaf, ArrowRight } from "lucide-react";
import { useAuth } from "../lib/auth";
import { Input, Label, Button } from "../components/UI";

const DEMO = [
    { email: "admin@greenpeak.in", pwd: "Admin@12345", role: "Super Admin" },
    { email: "procurement@greenpeak.in", pwd: "Welcome@123", role: "Procurement Mgr" },
    { email: "warehouse@greenpeak.in", pwd: "Welcome@123", role: "Warehouse Mgr" },
    { email: "sales@greenpeak.in", pwd: "Welcome@123", role: "Sales Mgr" },
    { email: "marketing@greenpeak.in", pwd: "Welcome@123", role: "Marketing Mgr" },
];

const Login = () => {
    const { login, user, loading } = useAuth();
    const nav = useNavigate();
    const [email, setEmail] = useState("admin@greenpeak.in");
    const [password, setPassword] = useState("Admin@12345");
    const [err, setErr] = useState("");
    const [submitting, setSubmitting] = useState(false);

    if (!loading && user) return <Navigate to="/" replace />;

    const submit = async (e) => {
        e.preventDefault();
        setErr("");
        setSubmitting(true);
        try {
            await login(email, password);
            nav("/");
        } catch (ex) {
            setErr(ex?.response?.data?.detail || "Login failed");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex" data-testid="login-page">
            {/* Left panel */}
            <div className="hidden lg:flex flex-1 bg-forest-700 text-white p-12 flex-col justify-between relative overflow-hidden">
                <div className="relative z-10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-md bg-white text-forest-700 flex items-center justify-center font-heading font-bold text-lg">G</div>
                        <div>
                            <div className="font-heading font-bold text-xl">GreenPeak</div>
                            <div className="text-xs text-forest-100 uppercase tracking-wider">Nutrition ERP</div>
                        </div>
                    </div>
                </div>
                <div className="relative z-10">
                    <h1 className="font-heading text-4xl font-bold leading-tight mb-4">
                        Run the nutrition business end-to-end.
                    </h1>
                    <p className="text-forest-100 text-sm max-w-md leading-relaxed">
                        Procurement, batch & expiry tracking, FEFO dispatch, sales, finance posting and campaign attribution — in one enterprise workspace.
                    </p>
                    <div className="grid grid-cols-3 gap-6 mt-10 text-xs">
                        <div>
                            <div className="text-forest-200 uppercase tracking-wider mb-1">Phase 1</div>
                            <div className="font-semibold">10 Core modules</div>
                        </div>
                        <div>
                            <div className="text-forest-200 uppercase tracking-wider mb-1">Roles</div>
                            <div className="font-semibold">14 role templates</div>
                        </div>
                        <div>
                            <div className="text-forest-200 uppercase tracking-wider mb-1">Traceability</div>
                            <div className="font-semibold">Batch + FEFO</div>
                        </div>
                    </div>
                </div>
                <div className="absolute -right-24 -bottom-24 w-96 h-96 rounded-full bg-forest-600 opacity-50"></div>
                <div className="absolute -right-10 top-20 w-56 h-56 rounded-full bg-forest-800 opacity-40"></div>
            </div>

            {/* Right form */}
            <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-white">
                <div className="w-full max-w-sm">
                    <div className="lg:hidden flex items-center gap-2 mb-10">
                        <div className="w-10 h-10 rounded-md bg-forest-700 text-white flex items-center justify-center font-heading font-bold">G</div>
                        <div className="font-heading font-bold text-slate-900">GreenPeak Nutrition ERP</div>
                    </div>
                    <h2 className="font-heading text-2xl font-bold text-slate-900 mb-1">Sign in to your workspace</h2>
                    <p className="text-sm text-slate-500 mb-8">Access the enterprise ERP console</p>

                    <form onSubmit={submit} className="space-y-4">
                        <div>
                            <Label>Email</Label>
                            <Input
                                data-testid="login-email"
                                type="email" value={email} required
                                onChange={(e) => setEmail(e.target.value)}
                                autoComplete="email"
                            />
                        </div>
                        <div>
                            <Label>Password</Label>
                            <Input
                                data-testid="login-password"
                                type="password" value={password} required
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete="current-password"
                            />
                        </div>
                        {err && (
                            <div data-testid="login-error" className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md px-3 py-2">
                                {err}
                            </div>
                        )}
                        <Button data-testid="login-submit" type="submit" className="w-full" disabled={submitting}>
                            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Sign in <ArrowRight className="w-4 h-4" /></>}
                        </Button>
                    </form>

                    <div className="mt-8 pt-6 border-t border-slate-100">
                        <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-2">Demo accounts (click to fill)</div>
                        <div className="space-y-1">
                            {DEMO.map((d) => (
                                <button
                                    key={d.email}
                                    data-testid={`demo-${d.email}`}
                                    type="button"
                                    onClick={() => { setEmail(d.email); setPassword(d.pwd); }}
                                    className="w-full text-left text-xs flex justify-between items-center px-3 py-2 rounded-md hover:bg-slate-50 transition-colors"
                                >
                                    <span className="text-slate-700 font-mono">{d.email}</span>
                                    <span className="text-slate-400">{d.role}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;
