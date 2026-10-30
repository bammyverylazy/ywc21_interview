import type { ButtonHTMLAttributes, ReactNode } from "react";
type Variant = "primary" | "secondary" | "ghost" | "danger";
const V: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-dark",
  secondary: "bg-white text-ink border border-line hover:bg-canvas-alt",
  ghost: "text-ink hover:bg-canvas-alt",
  danger: "bg-danger text-white hover:opacity-90",
};
interface Props extends ButtonHTMLAttributes<HTMLButtonElement> { variant?: Variant; size?: "md" | "lg"; icon?: ReactNode; loading?: boolean; }
export function Button({ variant = "primary", size = "md", icon, loading, children, className = "", disabled, ...rest }: Props) {
  return (
    <button {...rest} disabled={disabled || loading} aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-app font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${size === "lg" ? "h-12 px-6 text-base" : "h-10 px-4 text-sm"} ${V[variant]} ${className}`}>
      {icon}{loading ? "กำลังดำเนินการ…" : children}
    </button>
  );
}
