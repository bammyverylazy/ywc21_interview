import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
interface Props { open: boolean; onClose: () => void; title: string; children: ReactNode; }
export function Modal({ open, onClose, title, children }: Props) {
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); prev?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 w-full max-w-lg rounded-t-panel bg-white shadow-xl sm:rounded-panel">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 id="modal-title" className="font-semibold">{title}</h2>
          <button type="button" onClick={onClose} className="grid h-8 w-8 place-items-center rounded-app hover:bg-canvas-alt" aria-label="ปิด"><X className="h-4 w-4" /></button>
        </div>
        <div className="max-h-[80vh] overflow-y-auto px-5 py-5">{children}</div>
      </div>
    </div>
  );
}
