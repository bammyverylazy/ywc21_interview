import type { LucideIcon } from "lucide-react";
import { Card } from "./Card";
import { Skeleton } from "./Skeleton";
interface Props { label: string; value: string | number; icon: LucideIcon; accent?: "brand" | "danger" | "warn" | "neutral"; loading?: boolean; }
const A: Record<NonNullable<Props["accent"]>, string> = {
  brand:   "bg-brand-soft text-brand",
  danger:  "bg-danger-soft text-danger",
  warn:    "bg-warn-soft text-warn",
  neutral: "bg-canvas-alt text-muted-strong",
};
export function StatCard({ label, value, icon: Icon, accent = "neutral", loading }: Props) {
  if (loading) return <Card className="p-5"><Skeleton className="h-8 w-16" /><Skeleton className="mt-2 h-4 w-32" /></Card>;
  return (
    <Card className="flex items-start justify-between p-5">
      <div><p className="text-2xl font-semibold">{value}</p><p className="mt-0.5 text-sm text-muted-strong">{label}</p></div>
      <span className={`grid h-10 w-10 place-items-center rounded-app ${A[accent]}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>
    </Card>
  );
}
