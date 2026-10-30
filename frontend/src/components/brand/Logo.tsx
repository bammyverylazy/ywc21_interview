/** Capsule (medicine) with a check (verified). Reads at 16px as a single mark. */
export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <g transform="rotate(-45 16 16)">
        <rect x="4" y="11" width="24" height="10" rx="5" fill="#fff" stroke="#187F6B" strokeWidth="2" />
        <path d="M16 11h7a5 5 0 0 1 0 10h-7z" fill="#187F6B" />
      </g>
      <path d="M18.5 11l2.3 2.2L24 9.5" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
export function Logo({ variant = "full", className = "" }: { variant?: "mark" | "full"; className?: string }) {
  if (variant === "mark") return <LogoMark className={className || "h-8 w-8"} />;
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`} role="img" aria-label="ยาเซฟ YaSafe">
      <LogoMark />
      <span className="flex items-baseline gap-1.5 leading-none" aria-hidden="true">
        <span className="text-lg font-semibold text-ink">ยาเซฟ</span>
        <span className="text-sm font-light text-muted-strong">YaSafe</span>
      </span>
    </span>
  );
}
