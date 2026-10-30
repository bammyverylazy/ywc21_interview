import { Activity, AlertTriangle, BarChart2, Boxes, ScanSearch } from "lucide-react";
export const NAV_ITEMS = [
  { to: "/dashboard", label: "ภาพรวมระบบ",         Icon: BarChart2 },
  { to: "/inventory",  label: "คลังยา",              Icon: Boxes },
  { to: "/alerts",     label: "ประกาศแจ้งเตือน",   Icon: AlertTriangle },
  { to: "/matches",    label: "ผลการตรวจสอบ",       Icon: ScanSearch },
  { to: "/activity",   label: "ประวัติการดำเนินการ", Icon: Activity },
] as const;
