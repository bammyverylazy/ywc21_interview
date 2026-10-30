import { X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { Logo } from "../brand/Logo";
import { NAV_ITEMS } from "./navItems";
interface Props { open: boolean; onClose: () => void; }
export function MobileDrawer({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <>
      <div className="fixed inset-0 z-40 bg-ink/25 md:hidden" aria-hidden="true" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-label="เมนูนำทาง"
        className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-white shadow-xl md:hidden">
        <div className="flex h-16 items-center justify-between border-b border-line px-5">
          <Logo /><button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-app hover:bg-canvas-alt" aria-label="ปิดเมนู"><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} end={to === "/dashboard"} onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-app px-3 py-3 text-sm ${isActive ? "bg-brand-soft font-medium text-brand-dark" : "text-muted-strong hover:bg-canvas-alt hover:text-ink"}`}>
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />{label}
            </NavLink>
          ))}
        </nav>
      </div>
    </>
  );
}
