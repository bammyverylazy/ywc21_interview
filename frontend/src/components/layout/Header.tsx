import { Menu } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { LogoMark } from "../brand/Logo";
interface Props { title: string; breadcrumb?: { label: string; to: string }[]; actions?: ReactNode; onMenuOpen: () => void; }
export function Header({ title, breadcrumb, actions, onMenuOpen }: Props) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-white px-4 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button type="button" onClick={onMenuOpen} className="grid h-9 w-9 shrink-0 place-items-center rounded-app hover:bg-canvas-alt md:hidden" aria-label="เปิดเมนู">
          <Menu className="h-5 w-5" />
        </button>
        <span className="flex items-center gap-2 md:hidden"><LogoMark className="h-6 w-6" /></span>
        <div className="min-w-0">
          {breadcrumb && breadcrumb.length > 0 && (
            <nav aria-label="เส้นทาง" className="hidden items-center gap-1 text-xs text-muted-strong sm:flex">
              {breadcrumb.map((b, i) => (
                <span key={b.to} className="flex items-center gap-1">
                  {i > 0 && <span aria-hidden="true">/</span>}
                  <Link to={b.to} className="hover:text-brand">{b.label}</Link>
                </span>
              ))}
            </nav>
          )}
          <h1 className="truncate text-base font-semibold leading-tight">{title}</h1>
        </div>
      </div>
      {actions && <div className="ml-4 flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}
