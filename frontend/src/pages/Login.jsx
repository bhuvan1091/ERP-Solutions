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
        <div className="min-h-dvh relative bg-[#122c24] p-4 sm:p-8 lg:p-12 flex flex-col" data-testid="login-page">
            <img src="/images/greenpeak-leaves.jpg" alt="" className="absolute inset-0 w-full h-full object-cover object-center" aria-hidden="true" />
            <div className="absolute inset-0 bg-[#102a23]/35" />
            <div className="relative flex items-center gap-3 text-white mb-8" data-testid="login-brand">
                <div className="w-10 h-10 rounded-lg bg-[#d9ecb9] text-forest-800 flex items-center justify-center"><Leaf className="w-6 h-6" /></div>
                <div><div className="font-heading font-bold text-xl">GreenPeak.</div><div className="text-[10px] text-forest-100">NUTRITION ERP</div></div>
            </div>
            <div className="relative flex-1 flex items-center justify-center lg:justify-end lg:pr-8">
                <div className="w-full max-w-[460px] bg-white rounded-lg p-6 sm:p-10 shadow-xl animate-fade-in">
                    <div className="text-xs font-bold text-forest-600 mb-3">YOUR GREENPEAK WORKSPACE</div>
                    <h1 className="font-heading text-4xl font-bold text-[#192b25] mb-2">Welcome back.</h1>
                    <p className="text-sm text-slate-500 mb-8">Sign in to continue.</p>

                    <form onSubmit={submit} className="space-y-4">
                        <div>
                            <Label htmlFor="login-email">Email address</Label>
                            <Input
                                data-testid="login-email"
                                id="login-email"
                                type="email" value={email} required
                                onChange={(e) => setEmail(e.target.value)}
                                autoComplete="email"
                            />
                        </div>
                        <div>
                            <Label htmlFor="login-password">Password</Label>
                            <Input
                                data-testid="login-password"
                                id="login-password"
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
                        <Button data-testid="login-submit" type="submit" className="w-full !py-3" disabled={submitting}>
                            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Sign in <ArrowRight className="w-4 h-4" /></>}
                        </Button>
                    </form>

                    <div className="mt-8 pt-6 border-t border-slate-100">
                        <div className="text-xs font-bold text-slate-500 mb-3">Demo workspace</div>
                        <div className="space-y-1">
                            {DEMO.map((d) => (
                                <button
                                    key={d.email}
                                    data-testid={`demo-${d.email}`}
                                    type="button"
                                    onClick={() => { setEmail(d.email); setPassword(d.pwd); }}
                                    className="w-full text-left text-xs flex flex-wrap justify-between items-center gap-1 px-2 py-2 rounded-md hover:bg-forest-50 transition-colors"
                                >
                                    <span className="text-slate-700 break-all">{d.email}</span>
                                    <span className="text-slate-500 text-[10px]">{d.role}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
            <div className="relative text-xs text-white/80 mt-8" data-testid="login-footer">GreenPeak Nutrition · Enterprise workspace</div>
        </div>
    );
};

export default Login;
