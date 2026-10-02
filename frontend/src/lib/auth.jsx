import React, { createContext, useContext, useEffect, useState } from "react";
import { endpoints } from "./api";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const refreshMe = async () => {
        const token = localStorage.getItem("erp_token");
        if (!token) {
            setUser(null);
            setLoading(false);
            return null;
        }
        try {
            const { data } = await endpoints.me();
            setUser(data);
            return data;
        } catch {
            localStorage.removeItem("erp_token");
            localStorage.removeItem("erp_refresh");
            setUser(null);
            return null;
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { refreshMe(); }, []);

    const login = async (email, password) => {
        const { data } = await endpoints.login({ email, password });
        localStorage.setItem("erp_token", data.access_token);
        localStorage.setItem("erp_refresh", data.refresh_token);
        await refreshMe();
    };

    const logout = async () => {
        try { await endpoints.logout(); } catch {}
        localStorage.removeItem("erp_token");
        localStorage.removeItem("erp_refresh");
        setUser(null);
    };

    const hasPermission = (perm) => {
        if (!user) return false;
        return user.permissions?.includes(perm);
    };
    const hasAnyPermission = (...perms) => perms.some(hasPermission);

    return (
        <AuthCtx.Provider value={{ user, loading, login, logout, refreshMe, hasPermission, hasAnyPermission }}>
            {children}
        </AuthCtx.Provider>
    );
};

export const useAuth = () => useContext(AuthCtx);
