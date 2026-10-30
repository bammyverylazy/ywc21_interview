import type { ActionLog } from "../../types/match";
import { formatThaiDate } from "../../lib/th";
import { Skeleton } from "../ui/Skeleton";
import { EmptyState } from "../feedback/EmptyState";
import { Card } from "../ui/Card";
import { ReviewStatusBadge } from "../feedback/StatusBadge";

export function RecentActivity({ logs, loading }: { logs: ActionLog[] | null; loading: boolean }) {
  return (
    <Card>
      <div className="border-b border-line px-5 py-4"><h2 className="font-semibold">กิจกรรมล่าสุด</h2></div>
      <div className="divide-y divide-line">
        {loading && Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-3 px-5 py-4"><Skeleton className="h-4 flex-1" /><Skeleton className="h-4 w-20 shrink-0" /></div>
        ))}
        {!loading && !logs?.length && <div className="p-5"><EmptyState title="ยังไม่มีกิจกรรม" hint="กิจกรรมจะปรากฏเมื่อมีการบันทึกการตรวจสอบ" /></div>}
        {logs?.map((log) => (
          <div key={log._id} className="flex items-start gap-3 px-5 py-4">
            <div className="min-w-0 flex-1">
              <ReviewStatusBadge status={log.status} />
              {log.action_note && <p className="mt-1 truncate text-sm text-muted-strong">{log.action_note}</p>}
            </div>
            <time dateTime={log.created_at} className="shrink-0 text-xs text-muted-strong">{formatThaiDate(log.created_at)}</time>
          </div>
        ))}
      </div>
    </Card>
  );
}
