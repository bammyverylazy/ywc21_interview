import type { HTMLAttributes } from "react";
export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div {...rest} className={`rounded-panel border border-line bg-white ${className}`} />;
}
