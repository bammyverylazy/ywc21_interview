import { AlertTriangle, Boxes, CircleHelp, FileSearch, PackageSearch } from "lucide-react";
import { StatCard } from "../ui/StatCard";

interface Summary {
  total_products: number; total_inventory: number; total_notices: number;
  exact_matches: number; potential_matches: number; pending_review: number;
}
export function SummaryCards({ data, loading }: { data: Summary | null; loading: boolean }) {
  const stats = [
    { label: "รายการยาในระบบ",         value: data?.total_inventory ?? 0,   icon: Boxes,       accent: "neutral"  },
    { label: "ประกาศที่บันทึก",        value: data?.total_notices ?? 0,     icon: FileSearch,  accent: "neutral"  },
    { label: "พบรายการตรงกัน",         value: data?.exact_matches ?? 0,     icon: AlertTriangle, accent: "danger" },
    { label: "รายการที่อาจเกี่ยวข้อง", value: data?.potential_matches ?? 0, icon: CircleHelp,  accent: "warn"     },
    { label: "รอตรวจสอบ",             value: data?.pending_review ?? 0,    icon: PackageSearch, accent: data?.pending_review ? "warn" : "neutral" },
    { label: "ผลิตภัณฑ์ทั้งหมด",      value: data?.total_products ?? 0,    icon: Boxes,        accent: "neutral"  },
  ] as const;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((s) => <StatCard key={s.label} loading={loading} label={s.label} value={s.value} icon={s.icon} accent={s.accent as "neutral" | "danger" | "warn"} />)}
    </div>
  );
}
