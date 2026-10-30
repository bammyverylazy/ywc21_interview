import { NavLink } from "react-router-dom";
import { Logo } from "../brand/Logo";
import { NAV_ITEMS } from "./navItems";
export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-white md:flex" aria-label="เมนูหลักแอปพลิเคชัน">
      <div className="flex h-16 items-center border-b border-line px-5"><Logo /></div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} end={to === "/dashboard"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-app px-3 py-2.5 text-sm transition-colors ${isActive ? "bg-brand-soft font-medium text-brand-dark" : "text-muted-strong hover:bg-canvas-alt hover:text-ink"}`}>
            <Icon className="h-4.5 w-4.5 shrink-0" aria-hidden="true" />{label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-line px-5 py-4"><p className="text-[11px] leading-relaxed text-muted-strong">ยาเซฟ v1.0 · ข้อมูลตัวอย่าง</p></div>
    </aside>
  );
}
