// SAMPLE DATA ONLY — placeholder products and invented lots.
// None of these represent real official safety announcements.
import type { Product } from "../../types/product";
import type { InventoryItem } from "../../types/inventory";
import type { SafetyNotice } from "../../types/notice";
import type { Match, ActionLog } from "../../types/match";

export const PRODUCTS: Product[] = [
  { _id: "prod-1", brand_name: "ยาตัวอย่าง แอลฟา", generic_name: "Example Drug Alpha", registration_no: "DEMO-REG-0001", manufacturer: "บริษัทตัวอย่าง จำกัด", created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z" },
  { _id: "prod-2", brand_name: "ยาตัวอย่าง เบต้า", generic_name: "Example Drug Beta",  registration_no: "DEMO-REG-0002", manufacturer: "บริษัทตัวอย่าง จำกัด", created_at: "2026-10-02T09:00:00Z", updated_at: "2026-10-02T09:00:00Z" },
  { _id: "prod-3", brand_name: "ยาตัวอย่าง แกมมา", generic_name: null, registration_no: null, manufacturer: null, created_at: "2026-10-03T09:00:00Z", updated_at: "2026-10-03T09:00:00Z" },
];

export const INVENTORY: InventoryItem[] = [
  { _id: "inv-1", product_id: "prod-1", lot_number: "L-DEMO-01", quantity: 30, expiry_date: "2027-05-31", created_at: "2026-10-10T08:00:00Z", updated_at: "2026-10-10T08:00:00Z" },
  { _id: "inv-2", product_id: "prod-1", lot_number: "L-DEMO-02", quantity: 20, expiry_date: "2027-08-31", created_at: "2026-10-10T08:05:00Z", updated_at: "2026-10-10T08:05:00Z" },
  { _id: "inv-3", product_id: "prod-2", lot_number: "L-DEMO-07", quantity: 45, expiry_date: "2027-03-31", created_at: "2026-10-11T08:00:00Z", updated_at: "2026-10-11T08:00:00Z" },
  { _id: "inv-4", product_id: "prod-3", lot_number: null,        quantity: 12, expiry_date: "2026-12-31", created_at: "2026-10-12T08:00:00Z", updated_at: "2026-10-12T08:00:00Z" },
];

export const NOTICES: SafetyNotice[] = [
  { _id: "note-1", title: "ประกาศตัวอย่าง: การเรียกคืนยาตัวอย่าง แอลฟา รุ่น L-DEMO-01", notice_type: "RECALL", product_name: "ยาตัวอย่าง แอลฟา", generic_name: "Example Drug Alpha", registration_no: "DEMO-REG-0001", manufacturer: "บริษัทตัวอย่าง จำกัด", affected_lots: ["L-DEMO-01"], reason: "ข้อมูลตัวอย่างสำหรับสาธิต — ไม่ใช่ประกาศจริง", published_at: "2026-10-20", source_name: "แหล่งข้อมูลตัวอย่าง (สาธิตเท่านั้น)", source_url: "https://example.invalid/notice-demo-1", imported_at: "2026-10-25T10:00:00Z", data_completeness: { has_registration_no: true, has_lot_information: true, has_manufacturer: true } },
  { _id: "note-2", title: "ประกาศตัวอย่าง: แจ้งเตือนยาตัวอย่าง เบต้า (ไม่ระบุรุ่น)", notice_type: "WARNING", product_name: "ยาตัวอย่าง เบต้า", generic_name: "Example Drug Beta",  registration_no: "DEMO-REG-0002", manufacturer: null, affected_lots: [], reason: "ข้อมูลตัวอย่างสำหรับสาธิต — ไม่ระบุรุ่นการผลิต", published_at: "2026-10-22", source_name: "แหล่งข้อมูลตัวอย่าง (สาธิตเท่านั้น)", source_url: "https://example.invalid/notice-demo-2", imported_at: "2026-10-26T10:00:00Z", data_completeness: { has_registration_no: true, has_lot_information: false, has_manufacturer: false } },
];

export const MATCHES: Match[] = [
  { _id: "match-1", inventory_id: "inv-1", notice_id: "note-1", match_status: "EXACT_MATCH",    match_reason: "เลขทะเบียนและเลขรุ่นการผลิตตรงกับผลิตภัณฑ์และรุ่นที่ระบุในประกาศทางการ", matched_fields: ["registration_no", "lot_number"], checked_at: "2026-10-30T10:00:00Z", matching_version: "1.0", review_status: "PENDING",   inventory: { ...INVENTORY[0], product: PRODUCTS[0] }, notice: NOTICES[0] },
  { _id: "match-2", inventory_id: "inv-3", notice_id: "note-2", match_status: "POTENTIAL_MATCH", match_reason: "เลขทะเบียนตรงกัน แต่ประกาศไม่ได้ระบุรุ่นการผลิตที่เกี่ยวข้อง ต้องตรวจสอบด้วยตนเอง",   matched_fields: ["registration_no"],               checked_at: "2026-10-30T10:01:00Z", matching_version: "1.0", review_status: "REVIEWED", inventory: { ...INVENTORY[2], product: PRODUCTS[1] }, notice: NOTICES[1] },
  { _id: "match-3", inventory_id: "inv-2", notice_id: "note-1", match_status: "NO_MATCH",        match_reason: "เลขทะเบียนตรงกัน แต่รุ่นการผลิต L-DEMO-02 ไม่ได้อยู่ในรายชื่อรุ่นที่ระบุในประกาศ",   matched_fields: ["registration_no"],               checked_at: "2026-10-30T10:02:00Z", matching_version: "1.0", review_status: "REVIEWED", inventory: { ...INVENTORY[1], product: PRODUCTS[0] }, notice: NOTICES[0] },
];

export const ACTION_LOGS: ActionLog[] = [
  { _id: "log-1", match_id: "match-2", status: "REVIEWED",        action_note: "ตรวจสอบประกาศต้นฉบับแล้ว ไม่พบข้อมูลรุ่นการผลิตในประกาศ", created_at: "2026-10-30T11:00:00Z" },
  { _id: "log-2", match_id: "match-2", status: "ACTION_RECORDED",  action_note: "แยกยารุ่น L-DEMO-07 ออกระหว่างรอตรวจสอบเพิ่มเติม",       created_at: "2026-10-30T11:30:00Z" },
  { _id: "log-3", match_id: "match-3", status: "REVIEWED",         action_note: "ยืนยันว่ารุ่น L-DEMO-02 ไม่อยู่ในรายการที่ประกาศระบุ",     created_at: "2026-10-30T12:00:00Z" },
];

export const DASHBOARD_SUMMARY = {
  total_products: PRODUCTS.length,
  total_inventory: INVENTORY.length,
  total_notices: NOTICES.length,
  exact_matches: MATCHES.filter((m) => m.match_status === "EXACT_MATCH").length,
  potential_matches: MATCHES.filter((m) => m.match_status === "POTENTIAL_MATCH").length,
  pending_review: MATCHES.filter((m) => m.review_status === "PENDING").length,
  last_notice_at: NOTICES.reduce((a, b) => (a > b.imported_at ? a : b.imported_at), ""),
};
