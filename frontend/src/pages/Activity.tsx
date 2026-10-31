import { useMemo, useState } from "react";
import {
  Activity as ActivityIcon,
  CheckCircle2,
  ClipboardCheck,
  FileCheck2,
  Flag,
  Search,
  ScanSearch,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { PageError } from "../components/ui/PageError";
import { EmptyState } from "../components/feedback/EmptyState";
import { MatchStatusBadge, ReviewStatusBadge } from "../components/feedback/StatusBadge";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { useAsync } from "../hooks/useAsync";
import type { ActivityEvent, ActivityType } from "../types/activity";
import type { ReviewStatus } from "../types/match";
import * as svc from "../services";
import { isMockData } from "../services";

const TYPE_LABELS: Record<ActivityType, string> = {
  MATCH_DETECTED: "พบรายการที่อาจเกี่ยวข้อง",
  REVIEWED: "ตรวจสอบผลแล้ว",
  ESCALATED: "ส่งตรวจสอบเพิ่มเติม",
  ACTION_RECORDED: "บันทึกการดำเนินการ",
  STATUS_UPDATED: "อัปเดตสถานะการตรวจสอบ",
};
const TYPE_ICON: Record<ActivityType, LucideIcon> = {
  MATCH_DETECTED: ScanSearch,
  REVIEWED: CheckCircle2,
  ESCALATED: Flag,
  ACTION_RECORDED: ClipboardCheck,
  STATUS_UPDATED: ClipboardCheck,
};
const REVIEW_OPTIONS: { value: ReviewStatus; label: string }[] = [
  { value: "PENDING", label: "รอตรวจสอบ" },
  { value: "REVIEWED", label: "ตรวจสอบแล้ว" },
  { value: "ESCALATED", label: "ส่งตรวจสอบเพิ่มเติม" },
  { value: "ACTION_RECORDED", label: "บันทึกการดำเนินการแล้ว" },
];

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "ไม่มีข้อมูลเวลา" : date.toLocaleString("th-TH");
}

function ActivitySummary({ label, value, icon: Icon, tone }: {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: string;
}) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-app ${tone}`}>
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <div>
        <p className="text-xl font-semibold leading-none">{value}</p>
        <p className="mt-1 text-xs text-muted-strong">{label}</p>
      </div>
    </Card>
  );
}

function ActivityDetail({ event, onClose }: { event: ActivityEvent; onClose: () => void }) {
  const match = event.match;
  const product = match?.inventory?.product;
  const notice = match?.notice;
  const Icon = TYPE_ICON[event.activity_type];
  return (
    <Modal open onClose={onClose} title="รายละเอียดกิจกรรม">
      <div className="space-y-5">
        <section>
          <div className="flex items-center gap-2 text-brand">
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span className="text-sm font-semibold">{TYPE_LABELS[event.activity_type]}</span>
          </div>
          <p className="mt-3 text-sm leading-6">{event.description}</p>
          <p className="mt-2 text-xs text-muted-strong">{formatTimestamp(event.occurred_at)}</p>
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-3 text-sm font-semibold">รายการที่เกี่ยวข้อง</h3>
          <dl className="grid gap-x-4 gap-y-3 sm:grid-cols-2">
            <DetailInfo label="ผู้ดำเนินการ" value={event.actor} />
            <DetailInfo label="ผลิตภัณฑ์" value={product?.brand_name} />
            <DetailInfo label="เลขรุ่นการผลิต" value={match?.inventory?.lot_number} />
            <DetailInfo label="เลขทะเบียนยา" value={product?.registration_no} />
            <DetailInfo label="ประกาศแจ้งเตือน" value={notice?.title} />
            <DetailInfo label="รหัสผลการตรวจสอบ" value={event.match_id} />
            <DetailInfo label="ก่อนดำเนินการ" value={event.previous_status} />
            <DetailInfo label="สถานะใหม่" value={event.new_status} />
          </dl>
          {match && (
            <div className="mt-4 flex flex-wrap gap-2">
              <MatchStatusBadge status={match.match_status} />
              {match.review_status && <ReviewStatusBadge status={match.review_status} />}
            </div>
          )}
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-2 text-sm font-semibold">รายละเอียดเพิ่มเติม</h3>
          <p className="whitespace-pre-wrap text-sm leading-6">{event.notes || "ไม่มีบันทึกเพิ่มเติม"}</p>
          <p className="mt-3 text-xs text-muted-strong">
            {event.previous_status
              ? "สถานะก่อนหน้าแสดงตามข้อมูลประวัติที่มี"
              : "ไม่มีข้อมูลสถานะก่อนหน้าในประวัตินี้"}
          </p>
          {notice?.source_url && (
            <a href={notice.source_url} target="_blank" rel="noreferrer noopener" className="mt-3 inline-block break-all text-sm text-brand hover:underline">
              เปิดประกาศต้นฉบับ
            </a>
          )}
        </section>
      </div>
    </Modal>
  );
}

function DetailInfo({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-strong">{label}</dt>
      <dd className="mt-0.5 break-words text-sm font-medium">{value || <span className="font-normal italic text-muted-strong">ไม่มีข้อมูล</span>}</dd>
    </div>
  );
}

function EventCard({ event, onSelect }: { event: ActivityEvent; onSelect: () => void }) {
  const Icon = TYPE_ICON[event.activity_type];
  const product = event.match?.inventory?.product;
  const reviewStatus = event.new_status ?? event.match?.review_status;
  return (
    <button type="button" onClick={onSelect} className="w-full rounded-panel border border-line bg-white p-4 text-left transition-colors hover:border-brand/40 focus-visible:outline-brand">
      <div className="flex gap-3">
        <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full border border-line bg-canvas-alt text-brand">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-semibold">{TYPE_LABELS[event.activity_type]}</span>
            <time dateTime={event.occurred_at} className="text-xs text-muted-strong">{formatTimestamp(event.occurred_at)}</time>
          </div>
          <p className="mt-1 text-sm leading-5 text-muted-strong">{event.description}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {product?.brand_name && <span className="text-sm font-medium">{product.brand_name}</span>}
            {event.match?.inventory?.lot_number && <span className="text-xs text-muted-strong">LOT {event.match.inventory.lot_number}</span>}
            {event.match && <MatchStatusBadge status={event.match.match_status} />}
            {reviewStatus && <ReviewStatusBadge status={reviewStatus} />}
          </div>
          {event.notes && <p className="mt-2 line-clamp-2 text-sm text-muted-strong">{event.notes}</p>}
        </div>
      </div>
    </button>
  );
}

export default function Activity() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<ActivityEvent | null>(null);
  const { data: events, loading, error, refetch } = useAsync(() => svc.getActivity(), []);

  const filteredEvents = useMemo(() => {
    const search = query.trim().toLocaleLowerCase();
    return [...(events ?? [])]
      .filter((event) => {
        const match = event.match;
        const product = match?.inventory?.product;
        const searchMatches = !search || [
          event.description,
          event.notes,
          event.actor,
          event.match_id,
          product?.brand_name,
          product?.generic_name,
          product?.registration_no,
          match?.inventory?.lot_number,
          match?.notice?.title,
          match?.notice?.product_name,
        ].some((value) => value?.toLocaleLowerCase().includes(search));
        const eventDate = event.occurred_at.slice(0, 10);
        const relatedReviewStatus = event.new_status ?? match?.review_status;
        return searchMatches
          && (!typeFilter || event.activity_type === typeFilter)
          && (!reviewFilter || relatedReviewStatus === reviewFilter)
          && (!dateFrom || eventDate >= dateFrom)
          && (!dateTo || eventDate <= dateTo);
      })
      .sort((a, b) => b.occurred_at.localeCompare(a.occurred_at));
  }, [events, query, typeFilter, reviewFilter, dateFrom, dateTo]);
  const allEvents = events ?? [];
  const clearFilters = () => {
    setQuery("");
    setTypeFilter("");
    setReviewFilter("");
    setDateFrom("");
    setDateTo("");
  };
  const filtersClear = !query && !typeFilter && !reviewFilter && !dateFrom && !dateTo;

  return (
    <AppLayout title="ประวัติการดำเนินการ" breadcrumb={[{ label: "ประวัติการดำเนินการ", to: "/activity" }]}
      actions={isMockData ? <DemoDataTag /> : undefined}>
      <header className="mb-6">
        <p className="text-sm text-muted-strong">Track review actions and changes made across your pharmacy workspace.</p>
      </header>

      {error && <div className="mb-5"><PageError message={error} onRetry={refetch} /></div>}

      <section aria-label="สรุปประวัติการดำเนินการ" className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => <Skeleton className="h-[72px]" key={index} />)
          : <>
            <ActivitySummary label="กิจกรรมทั้งหมด" value={allEvents.length} tone="bg-canvas-alt text-ink" icon={ActivityIcon} />
            <ActivitySummary label="ตรวจสอบแล้ว" value={allEvents.filter((event) => event.activity_type === "REVIEWED").length} tone="bg-brand-soft text-brand" icon={CheckCircle2} />
            <ActivitySummary label="ส่งตรวจสอบเพิ่มเติม" value={allEvents.filter((event) => event.activity_type === "ESCALATED").length} tone="bg-warn-soft text-warn" icon={Flag} />
            <ActivitySummary label="บันทึกการดำเนินการ" value={allEvents.filter((event) => event.activity_type === "ACTION_RECORDED").length} tone="bg-calm-soft text-calm" icon={FileCheck2} />
          </>}
      </section>

      <Card className="mb-4 p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(220px,1fr)_minmax(170px,0.7fr)_minmax(170px,0.7fr)_minmax(150px,0.6fr)_minmax(150px,0.6fr)_auto] xl:items-end">
          <div className="relative">
            <Input id="activity-search" label="ค้นหาประวัติ" value={query} onChange={(event) => setQuery(event.target.value)}
              placeholder="ชื่อยา, LOT, รายละเอียด..." className="pl-9" />
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-[2.15rem] h-4 w-4 text-muted-strong" />
          </div>
          <Select label="ประเภทกิจกรรม" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} placeholder="ทุกประเภท"
            options={Object.entries(TYPE_LABELS).map(([value, label]) => ({ value, label }))} />
          <Select label="สถานะ" value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)} placeholder="ทุกสถานะ"
            options={REVIEW_OPTIONS} />
          <Input id="activity-from" label="ตั้งแต่วันที่" type="date" value={dateFrom} max={dateTo || undefined} onChange={(event) => setDateFrom(event.target.value)} />
          <Input id="activity-to" label="ถึงวันที่" type="date" value={dateTo} min={dateFrom || undefined} onChange={(event) => setDateTo(event.target.value)} />
          <Button variant="ghost" className="whitespace-nowrap" disabled={filtersClear} onClick={clearFilters}>ล้างตัวกรอง</Button>
        </div>
      </Card>

      {!loading && !error && allEvents.length === 0 && (
        <EmptyState title="ยังไม่มีประวัติกิจกรรม" hint="รายการประวัติจะปรากฏเมื่อมีการตรวจพบผลหรือบันทึกการดำเนินการ" />
      )}
      {!loading && !error && allEvents.length > 0 && filteredEvents.length === 0 && (
        <EmptyState title="ไม่พบกิจกรรมที่ตรงกัน" hint="ลองเปลี่ยนตัวกรองหรือคำค้นหา"
          action={<Button variant="secondary" onClick={clearFilters}>ล้างตัวกรอง</Button>} />
      )}

      {loading && <div className="space-y-3"><Skeleton className="h-24" /><Skeleton className="h-24" /><Skeleton className="h-24" /></div>}
      {!loading && filteredEvents.length > 0 && (
        <>
          <div className="space-y-3">
            {filteredEvents.map((event) => <EventCard key={event._id} event={event} onSelect={() => setSelectedEvent(event)} />)}
          </div>
          <p className="mt-3 text-xs text-muted-strong">แสดง {filteredEvents.length} จาก {allEvents.length} กิจกรรม เรียงจากใหม่ไปเก่า</p>
        </>
      )}
      {selectedEvent && <ActivityDetail event={selectedEvent} onClose={() => setSelectedEvent(null)} />}
    </AppLayout>
  );
}
