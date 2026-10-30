import { Info } from "lucide-react";
import { DISCLAIMER } from "../../lib/th";
export function Disclaimer({ className = "" }: { className?: string }) {
  return (
    <p role="note" className={`flex gap-2 rounded-app bg-canvas-alt p-3 text-xs leading-relaxed text-muted-strong ${className}`}>
      <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /><span>{DISCLAIMER}</span>
    </p>
  );
}
