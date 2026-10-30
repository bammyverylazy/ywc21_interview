import { useParams, Link } from "react-router-dom";
import { ExternalLink, CheckCircle2, XCircle } from "lucide-react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { PageError } from "../components/ui/PageError";
import { Badge } from "../components/ui/Badge";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { NOTICE_TYPE_LABEL, formatThaiDate } from "../lib/th";
import { useAsync } from "../hooks/useAsync";
import * as svc from "../services";

export default function AlertDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: notice, loading, error, refetch } = useAsync(() => svc.getNotice(id!), [id]);

  if (loading) return <AppLayout title="กำลังโหลด…" breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }, { label: "…", to: "#" }]}><Skeleton className="h-64" /></AppLayout>;
  if (error || !notice) return <AppLayout title="ไม่พบประกาศ" breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }, { label: "ไม่พบ", to: "#" }]}><PageError message={error ?? "ไม่พบประกาศ"} onRetry={refetch} /></AppLayout>;

  const dc = notice.data_completeness;
  const completeness: [string, boolean | undefined][] = [["เลขทะเบียน", dc?.has_registration_no], ["ข้อมูลรุ่นการผลิต", dc?.has_lot_information], ["ผู้ผลิต", dc?.has_manufacturer]];

  return (
    <AppLayout title={notice.product_name}
      breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }, { label: notice.product_name, to: `/alerts/${id}` }]}
      actions={<DemoDataTag />}>

      {/* Header card */}
      <Card className="mb-6 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge color={notice.notice_type === "RECALL" ? "danger" : "warn"}>{NOTICE_TYPE_LABEL[notice.notice_type]}</Badge>
              <span className="text-xs text-muted-strong">เผยแพร่ {formatThaiDate(notice.published_at)} · นำเข้า {formatThaiDate(notice.imported_at)}</span>
            </div>
            <h2 className="mt-2 text-lg font-semibold">{notice.title}</h2>
            <p className="mt-1 text-sm text-muted-strong">แหล่งข้อมูล: {notice.source_name}</p>
          </div>
          <a href={notice.source_url} target="_blank" rel="noreferrer noopener"
            className="flex shrink-0 items-center gap-1.5 rounded-app border border-line bg-white px-3 py-2 text-sm hover:bg-canvas-alt">
            <ExternalLink className="h-4 w-4" aria-hidden="true" />เปิดประกาศต้นฉบับ
          </a>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Product info */}
        <Card className="p-5 lg:col-span-2">
          <h3 className="mb-4 font-semibold">ข้อมูลผลิตภัณฑ์จากประกาศ</h3>
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            {([["ชื่อผลิตภัณฑ์", notice.product_name], ["ชื่อสามัญ", notice.generic_name], ["เลขทะเบียน", notice.registration_no], ["ผู้ผลิต", notice.manufacturer], ["เหตุผล", notice.reason]] as [string, string | null | undefined][]).map(([k, v]) => (
              <div key={k} className={k === "เหตุผล" ? "sm:col-span-2" : ""}>
                <dt className="text-xs text-muted-strong">{k}</dt>
                <dd className="mt-0.5 text-sm font-medium">{v ?? <span className="font-normal italic text-muted-strong">ไม่มีข้อมูลในประกาศ</span>}</dd>
              </div>
            ))}
          </dl>

          {/* Affected lots */}
          <div className="mt-5 border-t border-line pt-4">
            <h4 className="mb-2 text-sm font-medium">รุ่นการผลิตที่ระบุในประกาศ</h4>
            {notice.affected_lots.length > 0
              ? <div className="flex flex-wrap gap-2">{notice.affected_lots.map((l) => <span key={l} className="rounded-app bg-danger-soft px-2.5 py-1 text-sm font-medium text-danger">{l}</span>)}</div>
              : <p className="text-sm italic text-muted-strong">ประกาศนี้ไม่ได้ระบุเลขรุ่นการผลิตที่เกี่ยวข้อง ผลการตรวจสอบจะเป็น "พบรายการที่อาจเกี่ยวข้อง" สำหรับผลิตภัณฑ์ที่ตรงกัน</p>}
          </div>
        </Card>

        {/* Completeness + actions */}
        <div className="space-y-4">
          <Card className="p-5">
            <h3 className="mb-3 font-semibold text-sm">ความครบถ้วนของข้อมูล</h3>
            <ul className="space-y-2">
              {completeness.map(([k, v]) => (
                <li key={k} className="flex items-center gap-2 text-sm">
                  {v ? <CheckCircle2 className="h-4 w-4 shrink-0 text-brand" aria-label="มีข้อมูล" /> : <XCircle className="h-4 w-4 shrink-0 text-muted-strong" aria-label="ไม่มีข้อมูล" />}
                  {k}
                </li>
              ))}
            </ul>
          </Card>
          <Card className="p-5">
            <h3 className="mb-3 font-semibold text-sm">ผลการตรวจสอบ</h3>
            <Link to={`/matches?notice_id=${id}`} className="text-sm text-brand hover:underline">ดูผลการตรวจสอบที่เกี่ยวข้อง</Link>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
