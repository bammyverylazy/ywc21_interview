import { ArrowRight, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import type { SafetyNotice } from "../../types/notice";
import { NOTICE_TYPE_LABEL, formatThaiDate } from "../../lib/th";
import { Skeleton } from "../ui/Skeleton";
import { EmptyState } from "../feedback/EmptyState";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";

export function LatestNotices({ notices, loading }: { notices: SafetyNotice[] | null; loading: boolean }) {
  return (
    <Card>
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <h2 className="font-semibold">ประกาศล่าสุด</h2>
        <Link to="/alerts" className="flex items-center gap-1 text-sm text-brand hover:underline">ดูทั้งหมด<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
      </div>
      <div className="divide-y divide-line">
        {loading && Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="flex gap-3 px-5 py-4"><Skeleton className="h-4 flex-1" /><Skeleton className="h-4 w-24 shrink-0" /></div>
        ))}
        {!loading && !notices?.length && <div className="p-5"><EmptyState title="ยังไม่มีประกาศในระบบ" /></div>}
        {notices?.map((n) => (
          <div key={n._id} className="flex items-start gap-3 px-5 py-4">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge color={n.notice_type === "RECALL" ? "danger" : "warn"}>{NOTICE_TYPE_LABEL[n.notice_type]}</Badge>
                <p className="truncate text-sm font-medium">{n.product_name}</p>
              </div>
              <p className="mt-1 truncate text-sm text-muted-strong">{n.title}</p>
              <p className="mt-0.5 text-xs text-muted-strong">เผยแพร่ {formatThaiDate(n.published_at)} · {n.source_name}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-2">
              <Link to={`/alerts/${n._id}`} className="text-xs text-brand hover:underline">ดูรายละเอียด</Link>
              <a href={n.source_url} target="_blank" rel="noreferrer noopener" className="flex items-center gap-0.5 text-xs text-muted-strong hover:text-brand">
                <ExternalLink className="h-3 w-3" aria-hidden="true" />ต้นฉบับ
              </a>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
