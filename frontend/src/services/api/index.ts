// Real API module. Swap VITE_USE_MOCK=false to activate.
// PROVISIONAL: endpoints match README §7; shapes confirmed when backend is ready.
import axios from "axios";
const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "/api" });
client.interceptors.response.use((r) => r, (e) => { console.error("API error", e); return Promise.reject(e); });
const get = <T>(url: string, p?: object) => client.get<T>(url, { params: p }).then((r) => r.data);
const post = <T>(url: string, d?: object) => client.post<T>(url, d).then((r) => r.data);

export const getProducts = () => get("/products");
export const getProduct = (id: string) => get(`/products/${id}`);
export const getInventory = (p?: object) => get("/inventory", p);
export const getInventoryItem = (id: string) => get(`/inventory/${id}`);
export const getNotices = (p?: object) => get("/notices", p);
export const getNotice = (id: string) => get(`/notices/${id}`);
export const getMatches = (p?: object) => get("/matches", p);
export const getMatch = (id: string) => get(`/matches/${id}`);
export const getActionLogs = (matchId: string) => get(`/matches/${matchId}/actions`);
export const addActionLog = (matchId: string, status: string, action_note: string) => post(`/matches/${matchId}/actions`, { status, action_note });
export const runMatching = () => post("/matches/run", { scope: "ALL" });
export const getDashboardSummary = () => get("/dashboard/summary");
export const getRecentActivity = () => get("/dashboard/recent-activity");
export const getAttentionItems = () => get("/dashboard/attention-items");

export const createProduct       = (data: object) => post("/products", data);
export const updateProduct       = (id: string, data: object) => client.put(`/products/${id}`, data).then((r) => r.data);
export const deleteProduct       = (id: string) => client.delete(`/products/${id}`).then((r) => r.data);
export const createInventoryItem = (data: object) => post("/inventory", data);
export const updateInventoryItem = (id: string, data: object) => client.put(`/inventory/${id}`, data).then((r) => r.data);
export const deleteInventoryItem = (id: string) => client.delete(`/inventory/${id}`).then((r) => r.data);
export const createNotice        = (data: object) => post("/notices", data);
export const deleteNotice        = (id: string) => client.delete(`/notices/${id}`).then((r) => r.data);
