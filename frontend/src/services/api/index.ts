// Real API module. Swap VITE_USE_MOCK=false to activate.
// PROVISIONAL: endpoints match README §7; shapes confirmed when backend is ready.
import axios from "axios";
import type { ActivityEvent } from "../../types/activity";
import type { ActionLog, Match, ReviewStatus } from "../../types/match";
import type { ActivityType } from "../../types/activity";
import type { InventoryItem } from "../../types/inventory";
import type { Product } from "../../types/product";
import type { SafetyNotice } from "../../types/notice";
const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "/api" });
client.interceptors.response.use((r) => r, (e) => { console.error("API error", e); return Promise.reject(e); });
const get = <T>(url: string, p?: object) => client.get<T>(url, { params: p }).then((r) => r.data);
const post = <T>(url: string, d?: object) => client.post<T>(url, d).then((r) => r.data);

export const getProducts = (): Promise<Product[]> => get("/products");
export const getProduct = (id: string): Promise<Product> => get(`/products/${id}`);
export const getInventory = (p?: object): Promise<InventoryItem[]> => get("/inventory", p);
export const getInventoryItem = (id: string): Promise<InventoryItem> => get(`/inventory/${id}`);
export const getNotices = (p?: object): Promise<SafetyNotice[]> => get("/notices", p);
export const getNotice = (id: string): Promise<SafetyNotice> => get(`/notices/${id}`);
export const getMatches = (p?: object): Promise<Match[]> => get("/matches", p);
export const getMatch = (id: string): Promise<Match> => get(`/matches/${id}`);
export const getActionLogs = (matchId: string): Promise<ActionLog[]> => get(`/matches/${matchId}/actions`);
export const addActionLog = (matchId: string, status: ReviewStatus, action_note: string): Promise<ActionLog> =>
  post(`/matches/${matchId}/actions`, { status, action_note });
const activityTypeForStatus = (status: ReviewStatus): ActivityType => {
  if (status === "ESCALATED") return "ESCALATED";
  if (status === "ACTION_RECORDED") return "ACTION_RECORDED";
  if (status === "REVIEWED") return "REVIEWED";
  return "STATUS_UPDATED";
};
const reviewDescription = (status: ReviewStatus): string => {
  if (status === "ESCALATED") return "ส่งกรณีนี้เพื่อตรวจสอบเพิ่มเติม";
  if (status === "ACTION_RECORDED") return "บันทึกการดำเนินการสำหรับกรณีนี้";
  if (status === "REVIEWED") return "ตรวจสอบผลการจับคู่แล้ว";
  return "อัปเดตสถานะการตรวจสอบ";
};
export const getActivity = async (): Promise<ActivityEvent[]> => {
  const matches = await getMatches();
  const expandedMatches = await Promise.all(matches.map(async (match) => {
    const [inventory, notice] = await Promise.all([
      match.inventory ?? getInventoryItem(match.inventory_id),
      match.notice ?? getNotice(match.notice_id),
    ]);
    const product = inventory?.product ?? (inventory ? await getProduct(inventory.product_id) : undefined);
    return {
      ...match,
      inventory: inventory ? { ...inventory, product: product ?? undefined } : undefined,
      notice: notice ?? undefined,
    };
  }));
  const events = await Promise.all(expandedMatches.map(async (match) => {
    const logs = await getActionLogs(match._id);
    return logs.map((log): ActivityEvent => ({
      _id: log._id,
      activity_type: activityTypeForStatus(log.status),
      description: reviewDescription(log.status),
      occurred_at: log.created_at,
      match_id: match._id,
      match,
      new_status: log.status,
      notes: log.action_note,
    }));
  }));
  const detections: ActivityEvent[] = matches
    .filter((match) => match.match_status !== "NO_MATCH")
    .map((match) => ({
      _id: `detected-${match._id}`,
      activity_type: "MATCH_DETECTED",
      description: "ตรวจพบรายการสินค้าคงคลังที่อาจเกี่ยวข้องกับประกาศ",
      occurred_at: match.checked_at,
      match_id: match._id,
      match,
    }));
  return [...detections, ...events.flat()].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at));
};
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
