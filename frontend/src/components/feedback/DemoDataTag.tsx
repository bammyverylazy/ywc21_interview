import { FlaskConical } from "lucide-react";
import { DEMO_HINT, DEMO_LABEL } from "../../lib/th";
export function DemoDataTag({ className = "" }: { className?: string }) {
  return (
    <span title={DEMO_HINT} className={`inline-flex items-center gap-1 rounded-full border border-dashed border-muted-strong/50 bg-white px-2 py-0.5 text-xs text-muted-strong ${className}`}>
      <FlaskConical className="h-3 w-3" aria-hidden="true" />{DEMO_LABEL}
    </span>
  );
}
