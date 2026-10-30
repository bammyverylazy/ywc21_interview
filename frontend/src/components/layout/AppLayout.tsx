import { useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { MobileDrawer } from "./MobileDrawer";
import { Header } from "./Header";
interface Props { title: string; breadcrumb?: { label: string; to: string }[]; actions?: ReactNode; children: ReactNode; }
export function AppLayout({ title, breadcrumb, actions, children }: Props) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden bg-canvas-alt">
      <Sidebar />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header title={title} breadcrumb={breadcrumb} actions={actions} onMenuOpen={() => setDrawerOpen(true)} />
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-6 md:py-8" id="main">{children}</main>
      </div>
    </div>
  );
}
