import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND}/api`;

export const api = axios.create({
    baseURL: API,
    headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("erp_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

api.interceptors.response.use(
    (r) => r,
    (err) => {
        if (err?.response?.status === 401) {
            const path = window.location.pathname;
            if (path !== "/login") {
                localStorage.removeItem("erp_token");
                localStorage.removeItem("erp_refresh");
                window.location.href = "/login";
            }
        }
        return Promise.reject(err);
    }
);

export const endpoints = {
    login: (data) => api.post("/auth/login", data),
    me: () => api.get("/auth/me"),
    logout: () => api.post("/auth/logout"),
    dashboard: () => api.get("/dashboard"),

    products: {
        list: (params) => api.get("/products", { params }),
        get: (id) => api.get(`/products/${id}`),
        create: (data) => api.post("/products", data),
        update: (id, data) => api.patch(`/products/${id}`, data),
        remove: (id) => api.delete(`/products/${id}`),
    },
    categories: {
        list: () => api.get("/product-categories"),
        create: (data) => api.post("/product-categories", data),
    },
    suppliers: {
        list: (params) => api.get("/suppliers", { params }),
        create: (data) => api.post("/suppliers", data),
        update: (id, data) => api.patch(`/suppliers/${id}`, data),
        approve: (id) => api.post(`/suppliers/${id}/approve`),
        remove: (id) => api.delete(`/suppliers/${id}`),
    },
    customers: {
        list: (params) => api.get("/customers", { params }),
        create: (data) => api.post("/customers", data),
        update: (id, data) => api.patch(`/customers/${id}`, data),
        remove: (id) => api.delete(`/customers/${id}`),
    },
    warehouses: {
        list: () => api.get("/warehouses"),
        create: (data) => api.post("/warehouses", data),
    },
    inventory: {
        batches: (params) => api.get("/inventory/batches", { params }),
        movements: (params) => api.get("/inventory/movements", { params }),
        adjust: (data) => api.post("/inventory/adjust", data),
        releaseBatch: (id) => api.post(`/inventory/batches/${id}/release`),
    },
    purchase: {
        list: (params) => api.get("/purchase-orders", { params }),
        get: (id) => api.get(`/purchase-orders/${id}`),
        create: (data) => api.post("/purchase-orders", data),
        approve: (id) => api.post(`/purchase-orders/${id}/approve`),
        cancel: (id) => api.post(`/purchase-orders/${id}/cancel`),
        grns: () => api.get("/goods-receipts"),
        createGrn: (data) => api.post("/goods-receipts", data),
    },
    sales: {
        list: (params) => api.get("/sales-orders", { params }),
        get: (id) => api.get(`/sales-orders/${id}`),
        create: (data) => api.post("/sales-orders", data),
        allocate: (id) => api.post(`/sales-orders/${id}/allocate`),
        dispatch: (id) => api.post(`/sales-orders/${id}/dispatch`),
        cancel: (id) => api.post(`/sales-orders/${id}/cancel`),
    },
    advertising: {
        campaigns: (params) => api.get("/advertising/campaigns", { params }),
        connections: () => api.get("/advertising/connections"),
        summary: () => api.get("/advertising/summary"),
    },
    audit: (params) => api.get("/audit-logs", { params }),
    users: {
        list: () => api.get("/users"),
        create: (data) => api.post("/users", data),
    },
    roles: () => api.get("/roles"),
};
