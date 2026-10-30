import { AlertCircle } from "lucide-react";
import { Button } from "./Button";
export function PageError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-panel border border-danger/25 bg-danger-soft px-6 py-10 text-center">
      <AlertCircle className="h-8 w-8 text-danger" aria-hidden="true" />
      <p className="font-medium">โหลดข้อมูลไม่สำเร็จ</p>
      <p className="max-w-sm text-sm text-muted-strong">{message}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry}>ลองอีกครั้ง</Button>}
    </div>
  );
}
