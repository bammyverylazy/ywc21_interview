import type { ReactNode } from "react";
export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-panel border border-dashed border-line px-6 py-12 text-center">
      <p className="font-medium">{title}</p>{hint && <p className="max-w-sm text-sm text-muted-strong">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
