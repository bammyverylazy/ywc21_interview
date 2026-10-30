export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-app bg-line ${className}`} aria-hidden="true" />;
}
