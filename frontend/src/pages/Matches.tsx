import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ClipboardList, Search, X } from "lucide-react";
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
import { formatThaiDate } from "../lib/th";
import { useAsync } from "../hooks/useAsync";
import type { Match, MatchStatus, ReviewStatus, ActionLog } from "../types/match";
import * as svc from "../services";

const MATCH_STATUS_OPTIONS: { value: MatchStatus; label: string }[] = [
  { value: "EXACT_MATCH", label: "พบรายการตรงกัน" },
  { value: "POTENTIAL_MATCH", label: "อาจเกี่ยวข้อง" },
  { value: "NO_MATCH", label: "ไม่พบรายการตรงกัน" },
];
const REVIEW_STATUS_OPTIONS: { value: ReviewStatus; label: string }[] = [
  { value: "PENDING", label: "รอตรวจสอบ" },
  { value: "REVIEWED", label: "ตรวจสอบแล้ว" },
  { value: "ESCALATED", label: "ส่งตรวจสอบเพิ่มเติม" },
  { value: "ACTION_RECORDED", label: "บันทึกการดำเนินการแล้ว" },
];
const FIELD_LABELS: Record<string, string> = {
  registration_no: "เลขทะเบียนยา",
  lot_number: "เลขรุ่นการผลิต",
  brand_name: "ชื่อการค้า",
  generic_name: "ชื่อสามัญ",
  manufacturer: "ผู้ผลิต",
};

function checkedDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "ไม่มีข้อมูล" : date.toLocaleString("th-TH");
}

function MatchDetail({ match, onClose, onActionSaved }: {
  match: Match;
  onClose: () => void;
  onActionSaved: (status: ReviewStatus, log: ActionLog) => void;
}) {
  const { data: expandedMatch, loading: detailLoading, error: detailError } = useAsync(async () => {
    const detail = await svc.getMatch(match._id);
    if (!detail) throw new Error("ไม่พบผลการตรวจสอบ");
    const [inventory, notice] = await Promise.all([
      detail.inventory ?? svc.getInventoryItem(detail.inventory_id),
      detail.notice ?? svc.getNotice(detail.notice_id),
    ]);
    const product = inventory?.product ?? (inventory ? await svc.getProduct(inventory.product_id) : undefined);
    return {
      ...detail,
      inventory: inventory ? { ...inventory, product: product ?? undefined } : undefined,
      notice: notice ?? undefined,
    };
  }, [match._id]);
  const { data: actionLogs, loading: logsLoading, error: logsError, refetch } =
    useAsync(() => svc.getActionLogs(match._id), [match._id]);
  const [note, setNote] = useState("");
  const [savingStatus, setSavingStatus] = useState<ReviewStatus | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const currentMatch = expandedMatch
    ? { ...expandedMatch, review_status: match.review_status ?? expandedMatch.review_status }
    : match;
  const product = currentMatch.inventory?.product;
  const notice = currentMatch.notice;
  const lot = currentMatch.inventory?.lot_number;
  const missingFields = [
    !product?.registration_no && "เลขทะเบียนยา",
    !lot && "เลขรุ่นการผลิตในคลัง",
    notice?.affected_lots.length === 0 && "เลขรุ่นการผลิตในประกาศ",
    !product && "รายละเอียดผลิตภัณฑ์",
    !notice && "รายละเอียดประกาศ",
  ].filter((field): field is string => Boolean(field));

  const saveReview = async (status: ReviewStatus) => {
    if (!note.trim()) {
      setActionError("กรุณาระบุบันทึกประกอบการดำเนินการ");
      return;
    }
    setSavingStatus(status);
    setActionError(null);
    setSuccess(null);
    try {
      const log = await svc.addActionLog(match._id, status, note.trim());
      onActionSaved(status, log);
      setNote("");
      setSuccess("บันทึกการดำเนินการแล้ว");
      refetch();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "บันทึกไม่สำเร็จ");
    } finally {
      setSavingStatus(null);
    }
  };

  return (
    <Modal open onClose={onClose} title="รายละเอียดผลการตรวจสอบ">
      <div className="space-y-5">
        {detailLoading && <p className="text-sm text-muted-strong">กำลังโหลดข้อมูลที่เกี่ยวข้อง…</p>}
        {detailError && <p role="alert" className="text-sm text-danger">โหลดรายละเอียดประกอบไม่สำเร็จ: {detailError}</p>}
        <section>
          <div className="flex flex-wrap items-center gap-2">
            <MatchStatusBadge status={currentMatch.match_status} />
            {currentMatch.review_status
              ? <ReviewStatusBadge status={currentMatch.review_status} />
              : <span className="text-xs text-muted-strong">ยังไม่มีสถานะการตรวจสอบ</span>}
          </div>
          <p className="mt-3 text-sm leading-6 text-ink">{currentMatch.match_reason || "ไม่มีคำอธิบายผลการจับคู่"}</p>
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-3 text-sm font-semibold">ข้อมูลผลิตภัณฑ์</h3>
          <dl className="grid gap-x-4 gap-y-3 sm:grid-cols-2">
            <Info label="ชื่อการค้า" value={product?.brand_name} />
            <Info label="ชื่อสามัญ" value={product?.generic_name} />
            <Info label="เลขทะเบียนยา" value={product?.registration_no} />
            <Info label="ผู้ผลิต" value={product?.manufacturer} />
            <Info label="เลขรุ่นการผลิต" value={lot} />
            <Info label="จำนวนคงเหลือ" value={currentMatch.inventory ? `${currentMatch.inventory.quantity} หน่วย` : undefined} />
            <Info label="วันหมดอายุ" value={currentMatch.inventory ? formatThaiDate(currentMatch.inventory.expiry_date) : undefined} />
          </dl>
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-3 text-sm font-semibold">ประกาศที่เกี่ยวข้อง</h3>
          <dl className="grid gap-x-4 gap-y-3 sm:grid-cols-2">
            <Info label="ชื่อประกาศ" value={notice?.title} />
            <Info label="แหล่งข้อมูล" value={notice?.source_name} />
            <Info label="วันที่เผยแพร่" value={notice?.published_at ? formatThaiDate(notice.published_at) : undefined} />
            <div>
              <dt className="text-xs text-muted-strong">ประกาศต้นฉบับ</dt>
              <dd className="mt-0.5 text-sm">
                {notice?.source_url
                  ? <a href={notice.source_url} target="_blank" rel="noreferrer noopener" className="break-all text-brand hover:underline">{notice.source_url}</a>
                  : <span className="italic text-muted-strong">ไม่มีข้อมูล</span>}
              </dd>
            </div>
          </dl>
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-3 text-sm font-semibold">เหตุผลและข้อมูลที่ต้องตรวจสอบ</h3>
          <p className="text-sm leading-6 text-ink">{currentMatch.match_reason || "ไม่มีคำอธิบายผลการจับคู่"}</p>
          <p className="mt-3 text-xs font-medium text-muted-strong">ข้อมูลที่ขาดหรือยังยืนยันไม่ได้</p>
          {missingFields.length
            ? <ul className="mt-1 list-inside list-disc text-sm text-muted-strong">{missingFields.map((field) => <li key={field}>{field}</li>)}</ul>
            : <p className="mt-1 text-sm text-calm">มีข้อมูลผลิตภัณฑ์และรุ่นการผลิตที่จำเป็น</p>}
          <p className="mt-3 text-xs text-muted-strong">
            ตรวจสอบล่าสุด {checkedDate(currentMatch.checked_at)} · รุ่นการจับคู่ {currentMatch.matching_version || "ไม่มีข้อมูล"}
          </p>
          <p className="mt-2 text-xs font-medium text-muted-strong">ฟิลด์ที่ใช้จับคู่</p>
          {currentMatch.matched_fields.length
            ? <div className="mt-1 flex flex-wrap gap-1.5">{currentMatch.matched_fields.map((field) =>
              <span key={field} className="rounded border border-line bg-canvas-alt px-2 py-0.5 text-xs">{FIELD_LABELS[field] ?? field}</span>)}</div>
            : <p className="mt-1 text-sm italic text-muted-strong">ไม่มีข้อมูล</p>}
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-3 text-sm font-semibold">ประวัติการตรวจสอบ</h3>
          {logsLoading && <Skeleton className="h-16" />}
          {logsError && <p role="alert" className="text-sm text-danger">{logsError}</p>}
          {!logsLoading && !logsError && !actionLogs?.length && <p className="text-sm text-muted-strong">ยังไม่มีการดำเนินการ</p>}
          <div className="space-y-3">
            {actionLogs?.map((log) => (
              <div key={log._id} className="border-l-2 border-line pl-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <ReviewStatusBadge status={log.status} />
                  <time className="text-xs text-muted-strong">{checkedDate(log.created_at)}</time>
                </div>
                {log.action_note && <p className="mt-1 text-sm text-ink">{log.action_note}</p>}
              </div>
            ))}
          </div>
        </section>

        <section className="border-t border-line pt-4">
          <h3 className="mb-1 text-sm font-semibold">บันทึกการตรวจสอบ</h3>
          <p className="mb-3 text-xs text-muted-strong">บันทึกจะถูกเพิ่มเป็นรายการประวัติใหม่และไม่แก้ไขรายการเดิม</p>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            placeholder="ระบุสิ่งที่ตรวจสอบหรือดำเนินการ..."
            aria-label="บันทึกการตรวจสอบ"
            className="w-full resize-y rounded-app border border-line bg-white px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
          />
          {actionError && <p role="alert" className="mt-2 text-sm text-danger">{actionError}</p>}
          {success && <p role="status" className="mt-2 text-sm text-calm">{success}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="md" loading={savingStatus === "REVIEWED"} disabled={!!savingStatus || !note.trim()} onClick={() => saveReview("REVIEWED")}>ทำเครื่องหมายตรวจสอบแล้ว</Button>
            <Button variant="secondary" loading={savingStatus === "ESCALATED"} disabled={!!savingStatus || !note.trim()} onClick={() => saveReview("ESCALATED")}>ส่งตรวจสอบเพิ่มเติม</Button>
            <Button variant="secondary" loading={savingStatus === "ACTION_RECORDED"} disabled={!!savingStatus || !note.trim()} onClick={() => saveReview("ACTION_RECORDED")}>บันทึกการดำเนินการ</Button>
          </div>
        </section>
      </div>
    </Modal>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-strong">{label}</dt>
      <dd className="mt-0.5 break-words text-sm font-medium">{value || <span className="font-normal italic text-muted-strong">ไม่มีข้อมูล</span>}</dd>
    </div>
  );
}

function MatchSummary({ label, value, tone, icon }: { label: string; value: number; tone: string; icon: React.ReactNode }) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-app ${tone}`}>{icon}</span>
      <div className="min-w-0">
        <p className="text-xl font-semibold leading-none">{value}</p>
        <p className="mt-1 truncate text-xs text-muted-strong">{label}</p>
      </div>
    </Card>
  );
}

function MatchRow({ match, onSelect }: { match: Match; onSelect: () => void }) {
  const product = match.inventory?.product;
  return (
    <tr className="align-top hover:bg-canvas-alt">
      <td className="px-4 py-4">
        <p className="font-medium">{product?.brand_name ?? "ไม่มีข้อมูลผลิตภัณฑ์"}{match.inventory?.is_demo && <span className="ml-2 text-xs font-normal text-muted-strong">DEMO</span>}</p>
        <p className="mt-1 text-xs text-muted-strong">{product?.registration_no ?? "ไม่ระบุเลขทะเบียน"}</p>
      </td>
      <td className="px-4 py-4 text-sm">{match.inventory?.lot_number || <span className="italic text-muted-strong">ไม่ระบุ</span>}</td>
      <td className="px-4 py-4">
        <p className="max-w-48 truncate text-sm">{match.notice?.title ?? "ไม่มีข้อมูลประกาศ"}</p>
        <p className="mt-1 text-xs text-muted-strong">{product?.manufacturer ?? "ไม่ระบุผู้ผลิต"}</p>
      </td>
      <td className="px-4 py-4"><MatchStatusBadge status={match.match_status} /></td>
      <td className="px-4 py-4">{match.review_status ? <ReviewStatusBadge status={match.review_status} /> : <span className="text-xs text-muted-strong">ไม่ระบุ</span>}</td>
      <td className="whitespace-nowrap px-4 py-4 text-xs text-muted-strong">{formatThaiDate(match.checked_at)}</td>
      <td className="px-4 py-4 text-right">
        <button type="button" onClick={onSelect} className="text-sm font-medium text-brand hover:underline">ดูรายละเอียด</button>
      </td>
    </tr>
  );
}

function MatchCard({ match, onSelect }: { match: Match; onSelect: () => void }) {
  const product = match.inventory?.product;
  return (
    <button type="button" onClick={onSelect} className="w-full rounded-panel border border-line bg-white p-4 text-left hover:border-brand/40">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold">{product?.brand_name ?? "ไม่มีข้อมูลผลิตภัณฑ์"}</p>
          <p className="mt-0.5 text-xs text-muted-strong">{product?.registration_no ?? "ไม่ระบุเลขทะเบียน"}</p>
        </div>
        <MatchStatusBadge status={match.match_status} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-xs text-muted-strong">เลขรุ่น</dt><dd className="mt-0.5">{match.inventory?.lot_number || "ไม่ระบุ"}</dd></div>
        <div><dt className="text-xs text-muted-strong">สถานะตรวจสอบ</dt><dd className="mt-0.5">{match.review_status ? <ReviewStatusBadge status={match.review_status} /> : "ไม่ระบุ"}</dd></div>
        <div className="col-span-2"><dt className="text-xs text-muted-strong">ประกาศ</dt><dd className="mt-0.5 line-clamp-2">{match.notice?.title ?? "ไม่มีข้อมูลประกาศ"}</dd></div>
      </dl>
      <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-xs text-muted-strong">
        <span>{product?.manufacturer ?? "ไม่ระบุผู้ผลิต"}</span><span>{formatThaiDate(match.checked_at)}</span>
      </div>
    </button>
  );
}

export default function Matches() {
  const [query, setQuery] = useState("");
  const [matchStatus, setMatchStatus] = useState("");
  const [reviewStatus, setReviewStatus] = useState("");
  const [sortLatest, setSortLatest] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: matches, loading, error, refetch } = useAsync(() => svc.getMatches(), []);

  const filteredMatches = useMemo(() => {
    const search = query.trim().toLocaleLowerCase();
    return [...(matches ?? [])]
      .filter((match) => {
        const product = match.inventory?.product;
        const searchMatches = !search || [
          product?.brand_name,
          product?.generic_name,
          product?.registration_no,
          product?.manufacturer,
          match.inventory?.lot_number,
          match.notice?.title,
          match.notice?.product_name,
        ].some((value) => value?.toLocaleLowerCase().includes(search));
        return searchMatches
          && (!matchStatus || match.match_status === matchStatus)
          && (!reviewStatus || match.review_status === reviewStatus)
          && (!searchParams.get("notice_id") || match.notice_id === searchParams.get("notice_id"))
          && (!searchParams.get("product_id") || product?._id === searchParams.get("product_id"));
      })
      .sort((a, b) => sortLatest
        ? b.checked_at.localeCompare(a.checked_at)
        : a.checked_at.localeCompare(b.checked_at));
  }, [matches, query, matchStatus, reviewStatus, sortLatest, searchParams]);
  const allMatches = matches ?? [];

  const clearFilters = () => {
    setQuery("");
    setMatchStatus("");
    setReviewStatus("");
    setSearchParams({});
  };
  const filtersClear = !query && !matchStatus && !reviewStatus && !searchParams.get("notice_id") && !searchParams.get("product_id");

  return (
    <AppLayout title="ผลการตรวจสอบ" breadcrumb={[{ label: "ผลการตรวจสอบ", to: "/matches" }]}>
      <header className="mb-6">
        <p className="text-sm text-muted-strong">Review inventory items that may be affected by medicine safety notices.</p>
      </header>

      {error && <div className="mb-5"><PageError message={error} onRetry={refetch} /></div>}

      <section aria-label="สรุปผลการตรวจสอบ" className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => <Skeleton className="h-[72px]" key={index} />)
          : <>
            <MatchSummary label="รายการตรวจสอบทั้งหมด" value={allMatches.length} tone="bg-canvas-alt text-ink" icon={<ClipboardList className="h-4 w-4" />} />
            <MatchSummary label="พบรายการตรงกัน" value={allMatches.filter((m) => m.match_status === "EXACT_MATCH").length} tone="bg-danger-soft text-danger" icon={<AlertTriangle className="h-4 w-4" />} />
            <MatchSummary label="อาจเกี่ยวข้อง" value={allMatches.filter((m) => m.match_status === "POTENTIAL_MATCH").length} tone="bg-warn-soft text-warn" icon={<Search className="h-4 w-4" />} />
            <MatchSummary label="รอตรวจสอบ" value={allMatches.filter((m) => m.review_status === "PENDING").length} tone="bg-brand-soft text-brand" icon={<CheckCircle2 className="h-4 w-4" />} />
          </>}
      </section>

      <Card className="mb-4 p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(220px,1fr)_minmax(180px,0.7fr)_minmax(180px,0.7fr)_minmax(180px,0.7fr)_auto] xl:items-end">
          <div className="relative">
            <Input label="ค้นหา" id="matches-search" value={query} onChange={(event) => setQuery(event.target.value)}
              placeholder="ชื่อยา, LOT, เลขทะเบียน..." className="pl-9" />
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-[2.15rem] h-4 w-4 text-muted-strong" />
          </div>
          <Select label="สถานะผลจับคู่" value={matchStatus} onChange={(event) => setMatchStatus(event.target.value)} placeholder="ทุกสถานะ"
            options={MATCH_STATUS_OPTIONS} />
          <Select label="สถานะตรวจสอบ" value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value)} placeholder="ทุกสถานะ"
            options={REVIEW_STATUS_OPTIONS} />
          <Select label="เรียงตามวันที่" value={sortLatest ? "latest" : "oldest"} onChange={(event) => setSortLatest(event.target.value === "latest")}
            options={[{ value: "latest", label: "ตรวจสอบล่าสุด" }, { value: "oldest", label: "ตรวจสอบเก่าที่สุด" }]} />
          <Button variant="ghost" className="whitespace-nowrap" disabled={filtersClear} onClick={clearFilters} icon={<X className="h-4 w-4" />}>ล้างตัวกรอง</Button>
        </div>
      </Card>

      {!loading && !error && matches?.length === 0 && (
        <EmptyState title="ยังไม่มีผลการตรวจสอบ" hint="เมื่อมีการตรวจคลังยากับประกาศ ผลลัพธ์จะแสดงที่นี่" />
      )}
      {!loading && !error && !!matches?.length && filteredMatches.length === 0 && (
        <EmptyState title="ไม่พบผลลัพธ์" hint="ลองเปลี่ยนคำค้นหาหรือล้างตัวกรองเพื่อดูรายการทั้งหมด"
          action={<Button variant="secondary" onClick={clearFilters}>ล้างตัวกรอง</Button>} />
      )}

      {loading && <div className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-20" /><Skeleton className="h-20" /></div>}
      {!loading && filteredMatches.length > 0 && (
        <>
          <div className="hidden overflow-x-auto rounded-panel border border-line bg-white lg:block">
            <table className="w-full min-w-[980px] text-left">
              <thead className="border-b border-line bg-canvas-alt text-xs text-muted-strong">
                <tr>
                  <th className="px-4 py-3 font-medium">ผลิตภัณฑ์</th>
                  <th className="px-4 py-3 font-medium">LOT</th>
                  <th className="px-4 py-3 font-medium">ประกาศ / ผู้ผลิต</th>
                  <th className="px-4 py-3 font-medium">ผลจับคู่</th>
                  <th className="px-4 py-3 font-medium">การตรวจสอบ</th>
                  <th className="px-4 py-3 font-medium">ตรวจล่าสุด</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredMatches.map((match) => <MatchRow key={match._id} match={match} onSelect={() => setSelectedMatch(match)} />)}
              </tbody>
            </table>
          </div>
          <div className="grid gap-3 lg:hidden">
            {filteredMatches.map((match) => <MatchCard key={match._id} match={match} onSelect={() => setSelectedMatch(match)} />)}
          </div>
          <p className="mt-3 text-xs text-muted-strong">แสดง {filteredMatches.length} จาก {allMatches.length} รายการ</p>
        </>
      )}

      {selectedMatch && (
        <MatchDetail
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
          onActionSaved={(status, log) => {
            setSelectedMatch((current) => current?._id === log.match_id ? { ...current, review_status: status } : current);
            refetch();
          }}
        />
      )}
    </AppLayout>
  );
}
