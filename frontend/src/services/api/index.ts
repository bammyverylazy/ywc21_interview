import axios from "axios";
import type { ActivityEvent } from "../../types/activity";
import type { InventoryItem, InventoryProductSummary } from "../../types/inventory";
import type { ActionLog, Match, ReviewStatus } from "../../types/match";
import type { SafetyNotice } from "../../types/notice";
import type { Product } from "../../types/product";
import type { SyncHistoryPage, SyncRun, SyncStatus, SyncTriggerResult } from "../../types/sync";

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

type ApiProduct = Omit<Product, "_id"> & { id: string };
type ApiProductSummary = Omit<InventoryProductSummary, "_id"> & { id: string };
type ApiInventory = Omit<InventoryItem, "_id" | "product"> & {
  id: string;
  product?: ApiProductSummary | null;
};
type ApiNotice = Omit<SafetyNotice, "_id" | "source_name"> & {
  id: string;
  source_name?: string | null;
};
type ApiMatch = Omit<Match, "_id" | "inventory" | "notice"> & {
  id: string;
  inventory?: ApiInventory | null;
  notice?: ApiNotice | null;
};
type ApiActionLog = Omit<ActionLog, "_id"> & { id: string };
type ApiActivity = Omit<ActivityEvent, "_id" | "match"> & {
  id: string;
  match?: ApiMatch | null;
};

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 15000,
});
client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    console.error("API request failed", error);
    return Promise.reject(error);
  },
);

const get = <T>(url: string, params?: object) =>
  client.get<T>(url, { params }).then((response) => response.data);
const post = <T>(url: string, data?: object) =>
  client.post<T>(url, data).then((response) => response.data);

async function getAll<T>(url: string, params?: object): Promise<T[]> {
  const limit = 200;
  const first = await get<PaginatedResponse<T>>(url, { ...params, skip: 0, limit });
  const items = [...first.items];
  for (let skip = first.items.length; skip < first.total; skip += limit) {
    const page = await get<PaginatedResponse<T>>(url, { ...params, skip, limit });
    items.push(...page.items);
  }
  return items;
}

const normalizeProduct = (product: ApiProduct): Product => ({
  ...product,
  _id: product.id,
});

const normalizeInventory = (item: ApiInventory): InventoryItem => ({
  ...item,
  _id: item.id,
  product: item.product
    ? {
        _id: item.product.id,
        brand_name: item.product.brand_name,
        generic_name: item.product.generic_name,
        registration_no: item.product.registration_no,
        manufacturer: item.product.manufacturer,
      }
    : undefined,
});

const normalizeNotice = (notice: ApiNotice): SafetyNotice => ({
  ...notice,
  _id: notice.id,
  source_name: notice.source_name ?? "ไม่ระบุแหล่งข้อมูล",
});

const normalizeMatch = (match: ApiMatch): Match => ({
  ...match,
  _id: match.id,
  inventory: match.inventory ? normalizeInventory(match.inventory) : undefined,
  notice: match.notice ? normalizeNotice(match.notice) : undefined,
});

const normalizeActionLog = (log: ApiActionLog): ActionLog => ({
  ...log,
  _id: log.id,
});

const normalizeActivity = (event: ApiActivity): ActivityEvent => ({
  ...event,
  _id: event.id,
  match: event.match ? normalizeMatch(event.match) : undefined,
});

export const getProducts = async (params?: object): Promise<Product[]> =>
  (await getAll<ApiProduct>("/products", params)).map(normalizeProduct);
export const getProduct = async (id: string): Promise<Product> =>
  normalizeProduct(await get<ApiProduct>(`/products/${id}`));
export const getInventory = async (params?: object): Promise<InventoryItem[]> =>
  (await getAll<ApiInventory>("/inventory", params)).map(normalizeInventory);
export const getInventoryItem = async (id: string): Promise<InventoryItem> =>
  normalizeInventory(await get<ApiInventory>(`/inventory/${id}`));
export const getNotices = async (params?: object): Promise<SafetyNotice[]> =>
  (await getAll<ApiNotice>("/notices", params)).map(normalizeNotice);
export const getNotice = async (id: string): Promise<SafetyNotice> =>
  normalizeNotice(await get<ApiNotice>(`/notices/${id}`));
export const getMatches = async (params?: object): Promise<Match[]> =>
  (await getAll<ApiMatch>("/matches", params)).map(normalizeMatch);
export const getMatch = async (id: string): Promise<Match> =>
  normalizeMatch(await get<ApiMatch>(`/matches/${id}`));
export const getActionLogs = async (matchId: string): Promise<ActionLog[]> =>
  (await get<ApiActionLog[]>(`/matches/${matchId}/actions`)).map(normalizeActionLog);
export const addActionLog = async (
  matchId: string,
  status: ReviewStatus,
  action_note: string,
): Promise<ActionLog> =>
  normalizeActionLog(await post<ApiActionLog>(`/matches/${matchId}/actions`, { status, action_note }));
export const getActivity = async (): Promise<ActivityEvent[]> =>
  (await getAll<ApiActivity>("/activity")).map(normalizeActivity);
export const runMatching = () =>
  post<{ total_checked: number; exact_matches: number; potential_matches: number; no_matches: number }>(
    "/matches/run",
    { scope: "ALL" },
  );
export const getDashboardSummary = () => get<{
  total_products: number;
  total_inventory: number;
  total_notices: number;
  exact_matches: number;
  potential_matches: number;
  pending_review: number;
  last_notice_at: string | null;
}>("/dashboard/summary");
export const getRecentActivity = async (): Promise<ActionLog[]> =>
  (await get<ApiActionLog[]>("/dashboard/recent-activity")).map(normalizeActionLog);
export const getAttentionItems = async (): Promise<Match[]> =>
  (await get<ApiMatch[]>("/dashboard/attention-items")).map(normalizeMatch);
export const getSyncStatus = () => get<SyncStatus>("/sync/status");
export const getSyncHistory = (params?: object) => get<SyncHistoryPage>("/sync/history", params);
export const getSyncRun = (id: string) => get<SyncRun>(`/sync/history/${id}`);
export const startThaiFdaSync = () =>
  client.post<SyncTriggerResult>("/sync/thai-fda").then((response) => response.data);

export const createProduct = async (data: object): Promise<Product> =>
  normalizeProduct(await post<ApiProduct>("/products", data));
export const updateProduct = async (id: string, data: object): Promise<Product> =>
  normalizeProduct(await client.put<ApiProduct>(`/products/${id}`, data).then((response) => response.data));
export const deleteProduct = (id: string) => client.delete(`/products/${id}`).then((response) => response.data);
export const createInventoryItem = async (data: object): Promise<InventoryItem> =>
  normalizeInventory(await post<ApiInventory>("/inventory", data));
export const updateInventoryItem = async (id: string, data: object): Promise<InventoryItem> =>
  normalizeInventory(await client.put<ApiInventory>(`/inventory/${id}`, data).then((response) => response.data));
export const deleteInventoryItem = (id: string) => client.delete(`/inventory/${id}`).then((response) => response.data);
export const createNotice = async (data: object): Promise<SafetyNotice> =>
  normalizeNotice(await post<ApiNotice>("/notices", data));
export const deleteNotice = (id: string) => client.delete(`/notices/${id}`).then((response) => response.data);
