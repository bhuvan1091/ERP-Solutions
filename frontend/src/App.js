import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Products from "./pages/Products";
import Suppliers from "./pages/Suppliers";
import Customers from "./pages/Customers";
import Warehouses from "./pages/Warehouses";
import Inventory from "./pages/Inventory";
import PurchaseOrders from "./pages/PurchaseOrders";
import SalesOrders from "./pages/SalesOrders";
import Advertising from "./pages/Advertising";
import UsersPage from "./pages/Users";
import Audit from "./pages/Audit";
import Invoices from "./pages/Invoices";
import Payments from "./pages/Payments";
import JournalEntries from "./pages/JournalEntries";
import FinanceReports from "./pages/FinanceReports";
import CompanySettings from "./pages/CompanySettings";
import "./App.css";

const queryClient = new QueryClient({
    defaultOptions: {
        queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 10 * 1000 },
    },
});

const Protected = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="animate-pulse text-slate-400">Loading workspace...</div>
            </div>
        );
    }
    if (!user) return <Navigate to="/login" replace />;
    return <Layout>{children}</Layout>;
};

const App = () => (
    <QueryClientProvider client={queryClient}>
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/" element={<Protected><Dashboard /></Protected>} />
                    <Route path="/products" element={<Protected><Products /></Protected>} />
                    <Route path="/suppliers" element={<Protected><Suppliers /></Protected>} />
                    <Route path="/customers" element={<Protected><Customers /></Protected>} />
                    <Route path="/warehouses" element={<Protected><Warehouses /></Protected>} />
                    <Route path="/inventory" element={<Protected><Inventory /></Protected>} />
                    <Route path="/purchase-orders" element={<Protected><PurchaseOrders /></Protected>} />
                    <Route path="/sales-orders" element={<Protected><SalesOrders /></Protected>} />
                    <Route path="/advertising" element={<Protected><Advertising /></Protected>} />
                    <Route path="/invoices" element={<Protected><Invoices /></Protected>} />
                    <Route path="/payments" element={<Protected><Payments /></Protected>} />
                    <Route path="/journal" element={<Protected><JournalEntries /></Protected>} />
                    <Route path="/finance-reports" element={<Protected><FinanceReports /></Protected>} />
                    <Route path="/settings" element={<Protected><CompanySettings /></Protected>} />
                    <Route path="/users" element={<Protected><UsersPage /></Protected>} />
                    <Route path="/audit" element={<Protected><Audit /></Protected>} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    </QueryClientProvider>
);

export default App;
