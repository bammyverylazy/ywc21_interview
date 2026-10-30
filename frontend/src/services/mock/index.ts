// Mock service layer — same shape as the real API module.
// Swap by setting VITE_USE_MOCK=false and pointing VITE_API_BASE_URL at the backend.
import { DASHBOARD_SUMMARY, INVENTORY, MATCHES, NOTICES, PRODUCTS, ACTION_LOGS } from "./data";
import type { Product } from "../../types/product";
import type { InventoryItem } from "../../types/inventory";
import type { SafetyNotice } from "../../types/notice";
import type { Match, ActionLog, ReviewStatus } from "../../types/match";
import type { ActivityEvent, ActivityType } from "../../types/activity";

const delay = <T>(v: T, ms = 300) => new Promise<T>((r) => setTimeout(() => r(v), ms));

// Products
export const getProducts = (): Promise<Product[]> => delay([...PRODUCTS]);
export const getProduct = (id: string): Promise<Product | undefined> => delay(PRODUCTS.find((p) => p._id === id));

// Inventory
export const getInventory = (params?: { product_id?: string; search?: string }): Promise<InventoryItem[]> => {
  let items = INVENTORY.map((i) => ({ ...i, product: PRODUCTS.find((p) => p._id === i.product_id) }));
  if (params?.product_id) items = items.filter((i) => i.product_id === params.product_id);
  if (params?.search) { const s = params.search.toLowerCase(); items = items.filter((i) => i.product?.brand_name.toLowerCase().includes(s) || i.lot_number?.toLowerCase().includes(s)); }
  return delay(items);
};
export const getInventoryItem = (id: string): Promise<InventoryItem | undefined> =>
  delay(INVENTORY.map((i) => ({ ...i, product: PRODUCTS.find((p) => p._id === i.product_id) })).find((i) => i._id === id));

// Notices
export const getNotices = (params?: { search?: string; notice_type?: string }): Promise<SafetyNotice[]> => {
  let n = [...NOTICES];
  if (params?.notice_type) n = n.filter((x) => x.notice_type === params.notice_type);
  if (params?.search) { const s = params.search.toLowerCase(); n = n.filter((x) => x.product_name.toLowerCase().includes(s) || x.registration_no?.toLowerCase().includes(s)); }
  return delay(n);
};
export const getNotice = (id: string): Promise<SafetyNotice | undefined> => delay(NOTICES.find((n) => n._id === id));

// Matches
export const getMatches = (params?: { status?: string }): Promise<Match[]> => {
  let m = [...MATCHES];
  if (params?.status) m = m.filter((x) => x.match_status === params.status);
  return delay(m);
};
export const getMatch = (id: string): Promise<Match | undefined> => delay(MATCHES.find((m) => m._id === id));
export const getActionLogs = (matchId: string): Promise<ActionLog[]> => delay(ACTION_LOGS.filter((l) => l.match_id === matchId));
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
export const getActivity = (): Promise<ActivityEvent[]> => {
  const detected: ActivityEvent[] = MATCHES
    .filter((match) => match.match_status !== "NO_MATCH")
    .map((match) => ({
      _id: `detected-${match._id}`,
      activity_type: "MATCH_DETECTED",
      description: "ตรวจพบรายการสินค้าคงคลังที่อาจเกี่ยวข้องกับประกาศ",
      occurred_at: match.checked_at,
      match_id: match._id,
      match,
    }));
  const actions: ActivityEvent[] = ACTION_LOGS.flatMap((log) => {
    const match = MATCHES.find((entry) => entry._id === log.match_id);
    if (!match) return [];
    return [{
      _id: log._id,
      activity_type: activityTypeForStatus(log.status),
      description: reviewDescription(log.status),
      occurred_at: log.created_at,
      match_id: match._id,
      match,
      new_status: log.status,
      notes: log.action_note,
    }];
  });
  return delay([...detected, ...actions].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at)));
};
export const addActionLog = (matchId: string, status: ReviewStatus, note: string): Promise<ActionLog> => {
  const log: ActionLog = { _id: `log-${Date.now()}`, match_id: matchId, status, action_note: note, created_at: new Date().toISOString() };
  ACTION_LOGS.push(log);
  const m = MATCHES.find((x) => x._id === matchId);
  if (m) m.review_status = status;
  return delay(log, 500);
};
export const runMatching = (): Promise<{ total_checked: number; exact_matches: number; potential_matches: number; no_matches: number }> =>
  delay({ total_checked: INVENTORY.length, exact_matches: 1, potential_matches: 1, no_matches: 1 }, 800);

// Dashboard
export const getDashboardSummary = () => delay({ ...DASHBOARD_SUMMARY });
export const getRecentActivity = () => delay([...ACTION_LOGS].reverse().slice(0, 5));
export const getAttentionItems = () => delay(MATCHES.filter((m) => m.match_status !== "NO_MATCH" && m.review_status === "PENDING"));

// Product CRUD stubs (mock)
export const createProduct = (data: Omit<import("../../types/product").Product, "_id"|"created_at"|"updated_at">): Promise<import("../../types/product").Product> => {
  const p = { ...data, _id: `prod-${Date.now()}`, created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
  PRODUCTS.push(p); return delay(p, 400);
};
export const updateProduct = (id: string, data: Partial<import("../../types/product").Product>): Promise<import("../../types/product").Product> => {
  const i = PRODUCTS.findIndex((p) => p._id === id); if (i < 0) throw new Error("ไม่พบรายการ");
  PRODUCTS[i] = { ...PRODUCTS[i], ...data, updated_at: new Date().toISOString() }; return delay(PRODUCTS[i], 400);
};
export const deleteProduct = (id: string): Promise<void> => {
  const i = PRODUCTS.findIndex((p) => p._id === id); if (i >= 0) PRODUCTS.splice(i, 1); return delay(undefined as unknown as void, 400);
};

// Inventory CRUD stubs (mock)
export const createInventoryItem = (data: Omit<import("../../types/inventory").InventoryItem, "_id"|"created_at"|"updated_at"|"product">): Promise<import("../../types/inventory").InventoryItem> => {
  const item = { ...data, _id: `inv-${Date.now()}`, created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
  INVENTORY.push(item); return delay(item, 400);
};
export const updateInventoryItem = (id: string, data: Partial<import("../../types/inventory").InventoryItem>): Promise<import("../../types/inventory").InventoryItem> => {
  const i = INVENTORY.findIndex((x) => x._id === id); if (i < 0) throw new Error("ไม่พบรายการ");
  INVENTORY[i] = { ...INVENTORY[i], ...data, updated_at: new Date().toISOString() }; return delay(INVENTORY[i], 400);
};
export const deleteInventoryItem = (id: string): Promise<void> => {
  const i = INVENTORY.findIndex((x) => x._id === id); if (i >= 0) INVENTORY.splice(i, 1); return delay(undefined as unknown as void, 400);
};

// Notice CRUD stubs (mock)
export const createNotice = (data: Omit<import("../../types/notice").SafetyNotice, "_id"|"imported_at">): Promise<import("../../types/notice").SafetyNotice> => {
  const n = { ...data, _id: `note-${Date.now()}`, imported_at: new Date().toISOString() };
  NOTICES.push(n); return delay(n, 400);
};
export const deleteNotice = (id: string): Promise<void> => {
  const i = NOTICES.findIndex((n) => n._id === id); if (i >= 0) NOTICES.splice(i, 1); return delay(undefined as unknown as void, 400);
};
