import { useState } from "react";
import { Plus, Search, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { PageError } from "../components/ui/PageError";
import { EmptyState } from "../components/feedback/EmptyState";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { Badge } from "../components/ui/Badge";
import { NoticeForm } from "../components/alerts/NoticeForm";
import { SyncPanel } from "../components/alerts/SyncPanel";
import { NOTICE_TYPE_LABEL, formatThaiDate } from "../lib/th";
import { useAsync } from "../hooks/useAsync";
import * as svc from "../services";
import { isMockData } from "../services";

export default function Alerts() {
  const [search, setSearch]   = useState("");
  const [typeFilter, setType] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const { data: notices, loading, error, refetch } = useAsync(svc.getNotices);

  const filtered = (notices ?? []).filter((n) => {
    const q = search.toLowerCase();
    const matchText = n.product_name.toLowerCase().includes(q) || (n.product_name_th ?? "").toLowerCase().includes(q) || (n.registration_no ?? "").toLowerCase().includes(q) || n.title.toLowerCase().includes(q) || n.affected_lots.some((lot) => (typeof lot === "string" ? lot : lot.lot_number).toLowerCase().includes(q));
    const matchType = !typeFilter || n.notice_type === typeFilter;
    return matchText && matchType;
  });

  return (
    <AppLayout title="ประกาศแจ้งเตือน" breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }]}
      actions={<>{isMockData && <DemoDataTag />}<Button icon={<Plus className="h-4 w-4" />} onClick={() => setAddOpen(true)}>นำเข้าประกาศ</Button></>}>

      <SyncPanel onSynced={() => refetch()} />

      {/* Filters */}
      <div className="mb-5 flex flex-wrap gap-3">
        <div className="relative w-72">
          <Input label="ค้นหาประกาศ" id="alert-search" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="ชื่อผลิตภัณฑ์, เลขทะเบียน…" className="pl-9" />
          <Search className="pointer-events-none absolute left-3 top-[2.15rem] h-4 w-4 text-muted-strong" aria-hidden="true" />
        </div>
        <div className="w-52">
          <Select label="ประเภท" value={typeFilter} onChange={(e) => setType(e.target.value)}
            placeholder="ทุกประเภท"
            options={[{ value: "RECALL", label: NOTICE_TYPE_LABEL.RECALL }, { value: "WARNING", label: NOTICE_TYPE_LABEL.WARNING }]} />
        </div>
      </div>

      {error && <PageError message={error} onRetry={refetch} />}

      {loading
        ? <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
        : filtered.length === 0
          ? <EmptyState title="ไม่พบประกาศ" hint={search || typeFilter ? "ลองปรับเงื่อนไขการค้นหา" : "นำเข้าประกาศจากแหล่งทางการเพื่อเริ่มตรวจสอบ"} action={!search && !typeFilter && <Button icon={<Plus className="h-4 w-4" />} onClick={() => setAddOpen(true)}>นำเข้าประกาศแรก</Button>} />
          : (
            <div className="overflow-x-auto rounded-panel border border-line bg-white">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-line bg-canvas-alt text-left text-xs text-muted-strong">
                  <th className="px-5 py-3 font-medium">ประกาศ</th>
                  <th className="hidden px-5 py-3 font-medium sm:table-cell">เลขทะเบียน</th>
                  <th className="hidden px-5 py-3 font-medium md:table-cell">วันที่เผยแพร่</th>
                  <th className="hidden px-5 py-3 font-medium lg:table-cell">รุ่นที่ระบุ</th>
                  <th className="px-5 py-3" />
                </tr></thead>
                <tbody className="divide-y divide-line">
                  {filtered.map((n) => (
                    <tr key={n._id} className="hover:bg-canvas-alt">
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge color={n.notice_type === "RECALL" ? "danger" : "warn"}>{NOTICE_TYPE_LABEL[n.notice_type]}</Badge>
                          <span className="font-medium">{n.product_name_th ?? n.product_name}</span>
                          {n.verification_status === "verified" && <Badge color="brand">ตรวจสอบแหล่งทางการแล้ว</Badge>}
                          {n.record_origin === "manual" && <Badge color="warn">รายการป้อนเอง · ยังไม่ยืนยัน</Badge>}
                        </div>
                        <p className="mt-0.5 line-clamp-1 text-xs text-muted-strong">{n.title}</p>
                      </td>
                      <td className="hidden px-5 py-3 text-muted-strong sm:table-cell">{n.registration_no ?? <span className="italic">ไม่ระบุ</span>}</td>
                      <td className="hidden px-5 py-3 text-muted-strong md:table-cell">{formatThaiDate(n.published_at)}</td>
                      <td className="hidden px-5 py-3 lg:table-cell">
                        {n.affected_lots.length > 0
                          ? <span className="font-medium text-danger">{n.affected_lots.length} รุ่น</span>
                          : <span className="text-muted-strong">ไม่ระบุ</span>}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <a href={n.source_url} target="_blank" rel="noreferrer noopener" className="flex items-center gap-1 text-xs text-muted-strong hover:text-brand"><ExternalLink className="h-3 w-3" />ต้นฉบับ</a>
                          <Link to={`/alerts/${n._id}`} className="text-brand hover:underline">รายละเอียด</Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="นำเข้าประกาศแจ้งเตือน">
        <NoticeForm onSaved={() => { setAddOpen(false); refetch(); }} onCancel={() => setAddOpen(false)} />
      </Modal>
    </AppLayout>
  );
}
