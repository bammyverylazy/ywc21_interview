// Central Thai UI strings. Internal enum values stay English.
export const MATCH_STATUS_LABEL = {
  EXACT_MATCH: "พบรายการตรงกัน",
  POTENTIAL_MATCH: "พบรายการที่อาจเกี่ยวข้อง",
  NO_MATCH: "ไม่พบรายการที่ตรงกัน",
} as const;
export const REVIEW_STATUS_LABEL = {
  PENDING: "รอตรวจสอบ",
  REVIEWED: "ตรวจสอบแล้ว",
  ESCALATED: "ส่งต่อเพื่อตรวจสอบเพิ่มเติม",
  ACTION_RECORDED: "บันทึกการดำเนินการแล้ว",
} as const;
export const NOTICE_TYPE_LABEL = { RECALL: "การเรียกคืนผลิตภัณฑ์", WARNING: "ประกาศแจ้งเตือน" } as const;

export const DISCLAIMER =
  "ยาเซฟเป็นเครื่องมือช่วยติดตามและสนับสนุนการตัดสินใจ ผลการตรวจสอบขึ้นอยู่กับความครบถ้วนและความถูกต้องของข้อมูลคลังยาและประกาศทางการที่มีอยู่ การไม่พบรายการที่ตรงกันไม่ได้รับประกันว่ายานั้นปลอดภัย โปรดตรวจสอบกับประกาศต้นฉบับ และปรึกษาเภสัชกรผู้รับผิดชอบหรือหน่วยงานที่เกี่ยวข้อง";
export const DEMO_LABEL = "ข้อมูลตัวอย่าง";
export const DEMO_HINT = "ข้อมูลนี้ใช้สาธิตเท่านั้น ไม่ใช่ประกาศทางการ";

const TH_MONTHS = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."];
/** ISO date/datetime -> "30 ต.ค. 2569" (Buddhist era). Invalid input -> "ไม่มีข้อมูล". */
export function formatThaiDate(iso?: string | null): string {
  if (!iso) return "ไม่มีข้อมูล";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "ไม่มีข้อมูล";
  return `${d.getDate()} ${TH_MONTHS[d.getMonth()]} ${d.getFullYear() + 543}`;
}
