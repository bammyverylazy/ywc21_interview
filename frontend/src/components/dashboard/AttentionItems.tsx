import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Match } from "../../types/match";
import { MatchStatusBadge, ReviewStatusBadge } from "../feedback/StatusBadge";
import { Skeleton } from "../ui/Skeleton";
import { EmptyState } from "../feedback/EmptyState";
import { Card } from "../ui/Card";

export function AttentionItems({ items, loading }: { items: Match[] | null; loading: boolean }) {
  return (
    <Card>
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <h2 className="font-semibold">รายการที่ต้องตรวจสอบ</h2>
        <Link to="/matches" className="flex items-center gap-1 text-sm text-brand hover:underline">ดูทั้งหมด<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
      </div>
      <div className="divide-y divide-line">
        {loading && Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-5 py-4"><Skeleton className="h-4 flex-1" /><Skeleton className="h-5 w-24" /></div>
        ))}
        {!loading && !items?.length && <div className="p-5"><EmptyState title="ไม่มีรายการที่รอตรวจสอบ" hint="ระบบจะแสดงรายการที่พบการตรงกันและยังไม่ได้รับการตรวจสอบไว้ที่นี่" /></div>}
        {items?.map((m) => {
          const productName = m.inventory?.product?.brand_name ?? "ไม่ทราบชื่อยา";
          const lot = m.inventory?.lot_number ?? "ไม่ระบุรุ่น";
          const noticeTitle = m.notice?.title ?? "ไม่ทราบชื่อประกาศ";
          return (
            <Link key={m._id} to={`/matches/${m._id}`} className="flex items-start gap-3 px-5 py-4 transition-colors hover:bg-canvas-alt">
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{productName} <span className="font-normal text-muted-strong">รุ่น {lot}</span></p>
                <p className="mt-0.5 truncate text-sm text-muted-strong">{noticeTitle}</p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <MatchStatusBadge status={m.match_status} />
                {m.review_status && <ReviewStatusBadge status={m.review_status} />}
              </div>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
