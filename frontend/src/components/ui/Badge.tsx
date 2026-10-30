import type { ReactNode } from "react";
type Color = "brand" | "danger" | "warn" | "neutral";
const C: Record<Color, string> = {
  brand:   "bg-brand-soft text-brand-dark border-brand/20",
  danger:  "bg-danger-soft text-danger border-danger/25",
  warn:    "bg-warn-soft text-warn border-warn/25",
  neutral: "bg-canvas-alt text-muted-strong border-line",
};
export function Badge({ color = "neutral", children }: { color?: Color; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${C[color]}`}>{children}</span>;
}
