import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Logo } from "../brand/Logo";
const LINKS = [
  { href: "#about", label: "เกี่ยวกับยาเซฟ" }, { href: "#how", label: "วิธีการทำงาน" },
  { href: "#features", label: "ฟีเจอร์" }, { href: "#sources", label: "แหล่งข้อมูล" },
];
const cta = "inline-flex h-10 items-center rounded-full bg-brand px-5 text-sm font-medium text-white hover:bg-brand-dark";
export function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 px-4 pt-[calc(env(safe-area-inset-top,0px)+12px)]">
      <nav aria-label="เมนูหลัก" className="glass mx-auto flex max-w-6xl items-center justify-between rounded-full py-2 pl-5 pr-2">
        <a href="#top" aria-label="ยาเซฟ กลับด้านบน"><Logo /></a>
        <ul className="hidden items-center gap-7 text-sm md:flex">
          {LINKS.map((l) => <li key={l.href}><a href={l.href} className="text-ink hover:text-brand">{l.label}</a></li>)}
        </ul>
        <div className="flex items-center gap-1">
          <Link to="/dashboard" className={`${cta} hidden md:inline-flex`}>เปิดระบบจัดการ</Link>
          <button type="button" className="grid h-10 w-10 place-items-center rounded-full md:hidden" aria-expanded={open} aria-controls="mobile-menu"
            aria-label={open ? "ปิดเมนู" : "เปิดเมนู"} onClick={() => setOpen(!open)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </nav>
      {open && (
        <div id="mobile-menu" className="mx-auto mt-2 max-w-6xl rounded-panel border border-line bg-white p-4 shadow-sm md:hidden">
          <ul className="space-y-1">{LINKS.map((l) => <li key={l.href}><a href={l.href} onClick={() => setOpen(false)} className="block rounded-app px-3 py-2.5 hover:bg-canvas-alt">{l.label}</a></li>)}</ul>
          <Link to="/dashboard" className={`${cta} mt-3 w-full justify-center`}>เปิดระบบจัดการ</Link>
        </div>
      )}
    </header>
  );
}
