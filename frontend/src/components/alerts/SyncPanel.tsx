import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { PageError } from "../ui/PageError";
import { isMockData } from "../../services";
import * as svc from "../../services";
import type { SyncRun, SyncStatus, SyncStatusValue } from "../../types/sync";

const STATUS_LABEL: Record<SyncStatusValue, string> = {
  NOT_RUN: "ยังไม่เคยซิงค์",
  RUNNING: "กำลังซิงค์",
  SUCCESS: "สำเร็จ",
  PARTIAL_SUCCESS: "สำเร็จบางส่วน",
  FAILED: "ไม่สำเร็จ",
  SKIPPED: "ข้ามตามช่วงเวลาที่กำหนด",
};

function dateTime(value?: string | null): string {
  if (!value) return "ไม่มีข้อมูล";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "ไม่มีข้อมูล" : parsed.toLocaleString("th-TH");
}

function statusColor(status: SyncStatusValue): "warn" | "danger" | "brand" | "neutral" {
  if (status === "SUCCESS") return "brand";
  if (status === "PARTIAL_SUCCESS" || status === "SKIPPED") return "warn";
  if (status === "FAILED") return "danger";
  if (status === "RUNNING") return "brand";
  return "neutral";
}

function errorText(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === "string") return response.data.detail;
    if (response?.data?.detail && typeof response.data.detail === "object") {
      const detail = response.data.detail as { message?: unknown };
      if (typeof detail.message === "string") return detail.message;
    }
  }
  return error instanceof Error ? error.message : "ไม่สามารถติดต่อ API ได้";
}

function failureDetails(error: unknown): { message: string; category?: string; stage?: string } {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as {
      response?: { data?: { detail?: unknown } };
    }).response;
    const detail = response?.data?.detail;
    if (typeof detail === "object" && detail !== null) {
      const structured = detail as { message?: unknown; category?: unknown; stage?: unknown };
      return {
        message: typeof structured.message === "string" ? structured.message : errorText(error),
        category: typeof structured.category === "string" ? structured.category : undefined,
        stage: typeof structured.stage === "string" ? structured.stage : undefined,
      };
    }
  }
  return { message: errorText(error) };
}

function RunSummary({ run }: { run: SyncRun }) {
  return (
    <div className="mt-2 space-y-1 text-xs text-muted-strong">
      <p>พบ {run.records_discovered} · ใหม่ {run.records_new} · ปรับปรุง {run.records_updated} · ไม่เปลี่ยน {run.records_unchanged} · ล้มเหลว {run.records_failed} · รอตรวจทาน {run.records_needing_review}</p>
      {run.error_summary && <p className="text-danger">{run.error_summary}</p>}
      {run.details.length > 0 && (
        <details className="pt-1">
          <summary className="cursor-pointer text-brand">รายละเอียดของการซิงค์ · {run.completed_at ? dateTime(run.completed_at) : dateTime(run.started_at)}</summary>
          <ul className="mt-2 space-y-1">
            {run.details.slice(0, 5).map((detail, index) => (
              <li key={`${detail.category}-${detail.source_id ?? detail.record_index ?? index}`}>
                {detail.stage ? `[${detail.stage}] ` : `[${detail.category}] `}
                {detail.message}{detail.source_id ? ` (${detail.source_id})` : ""}
                {detail.missing_fields?.length ? ` — ขาด: ${detail.missing_fields.join(", ")}` : ""}
              </li>
            ))}
            {(run.details_omitted ?? 0) > 0 && <li>ยังมีรายละเอียดอีก {run.details_omitted} รายการในประวัติฉบับเต็ม</li>}
          </ul>
        </details>
      )}
    </div>
  );
}

export function SyncPanel({ onSynced }: { onSynced?: () => void }) {
  const onSyncedRef = useRef(onSynced);
  const [watchedRunId, setWatchedRunId] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [history, setHistory] = useState<SyncRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [submitFailure, setSubmitFailure] = useState<{
    message: string;
    category?: string;
    stage?: string;
    occurredAt: string;
  } | null>(null);
  const [syncResultMessage, setSyncResultMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { onSyncedRef.current = onSynced; }, [onSynced]);

  const refresh = useCallback(async (runIdToWatch = watchedRunId) => {
    setRefreshing(true);
    try {
      const [nextStatus, nextHistory] = await Promise.all([
        svc.getSyncStatus(),
        svc.getSyncHistory({ limit: 10 }),
      ]);
      setSyncStatus(nextStatus);
      setHistory(nextHistory.items);
      setRequestError(null);
      if (
        runIdToWatch
        && nextStatus.last_run?.id === runIdToWatch
        && nextStatus.current_status !== "RUNNING"
      ) {
        setSyncResultMessage(
          nextStatus.current_status === "SUCCESS"
            ? "ซิงค์ข้อมูลสำเร็จ"
            : nextStatus.current_status === "PARTIAL_SUCCESS"
              ? "ซิงค์เสร็จแล้ว แต่มีบางรายการต้องตรวจสอบ"
              : "การซิงค์ไม่สำเร็จ ดูรายละเอียดในประวัติการซิงค์",
        );
        setWatchedRunId(null);
        onSyncedRef.current?.();
      }
    } catch (error) {
      setRequestError(errorText(error));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [watchedRunId]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (syncStatus?.current_status !== "RUNNING") return;
    const timer = window.setInterval(() => { void refresh(); }, 2500);
    return () => window.clearInterval(timer);
  }, [syncStatus?.current_status, refresh]);

  const submitSync = async () => {
    setSubmitting(true);
    setSubmitFailure(null);
    setSyncResultMessage(null);
    try {
      const started = await svc.startThaiFdaSync();
      setWatchedRunId(started.run_id);
      await refresh(started.run_id);
    } catch (error) {
      setSubmitFailure({ ...failureDetails(error), occurredAt: new Date().toISOString() });
    } finally {
      setSubmitting(false);
    }
  };

  const lastRun = syncStatus?.last_run;

  return (
    <Card className="mb-6 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">การซิงค์ประกาศจาก อย.</h2>
          <p className="mt-1 text-xs text-muted-strong">แหล่งข้อมูล: {lastRun?.source_name ?? "Thai FDA Drug Alert"}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {syncStatus && <Badge color={statusColor(syncStatus.current_status)}>{STATUS_LABEL[syncStatus.current_status]}</Badge>}
          <Button
            variant="secondary"
            icon={<RefreshCw className="h-4 w-4" />}
            onClick={() => void refresh()}
            loading={refreshing}
          >
            รีเฟรชสถานะ
          </Button>
          <Button
            icon={<RefreshCw className="h-4 w-4" />}
            onClick={() => void submitSync()}
            loading={submitting || syncStatus?.current_status === "RUNNING"}
            disabled={isMockData || submitting || syncStatus?.current_status === "RUNNING"}
          >
            {submitting || syncStatus?.current_status === "RUNNING" ? "กำลังซิงค์…" : "ซิงค์ตอนนี้"}
          </Button>
        </div>
      </div>

      {requestError && <div className="mt-4"><PageError message={requestError} onRetry={() => void refresh()} /></div>}
      {submitFailure && (
        <div role="alert" className="mt-4 rounded-app bg-danger-soft px-3 py-2 text-sm text-danger">
          <p>{submitFailure.message}</p>
          <p className="mt-1 text-xs">
            ขั้นตอน: {submitFailure.stage ?? submitFailure.category ?? "ไม่ทราบ"}
            {" · "}เวลา: {dateTime(submitFailure.occurredAt)}
          </p>
          <a href="#sync-history" className="mt-1 inline-block text-xs underline">
            ตรวจสอบประวัติการซิงค์ล่าสุด
          </a>
        </div>
      )}
      {syncResultMessage && (
        <p
          role="status"
          className={`mt-4 rounded-app px-3 py-2 text-sm ${
            syncStatus?.current_status === "FAILED" ? "bg-danger-soft text-danger" : "bg-canvas-alt"
          }`}
        >
          {syncResultMessage}
          {syncStatus?.last_run?.error_summary && (
            <span className="mt-1 block">{syncStatus.last_run.error_summary}</span>
          )}
        </p>
      )}
      {loading ? (
        <p className="mt-4 text-sm text-muted-strong">กำลังโหลดสถานะการซิงค์…</p>
      ) : (
        <>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-app bg-canvas-alt p-3">
              <dt className="text-xs text-muted-strong">ซิงค์ครั้งล่าสุด</dt>
              <dd className="mt-1 text-sm font-medium">{dateTime(syncStatus?.last_attempted_at)}</dd>
            </div>
            <div className="rounded-app bg-canvas-alt p-3">
              <dt className="text-xs text-muted-strong">ซิงค์สำเร็จล่าสุด</dt>
              <dd className="mt-1 text-sm font-medium">{dateTime(syncStatus?.last_successful_at)}</dd>
            </div>
            <div className="rounded-app bg-canvas-alt p-3">
              <dt className="text-xs text-muted-strong">ประกาศใหม่ / ปรับปรุง</dt>
              <dd className="mt-1 text-sm font-medium">{lastRun ? `${lastRun.records_new} / ${lastRun.records_updated}` : "ไม่มีข้อมูล"}</dd>
            </div>
            <div className="rounded-app bg-canvas-alt p-3">
              <dt className="text-xs text-muted-strong">ไม่เปลี่ยน / ล้มเหลว</dt>
              <dd className="mt-1 text-sm font-medium">{lastRun ? `${lastRun.records_unchanged} / ${lastRun.records_failed}` : "ไม่มีข้อมูล"}</dd>
            </div>
          </dl>

          <div className="mt-5 border-t border-line pt-4">
            <div id="sync-history" />
            <h3 className="text-sm font-semibold">ประวัติการซิงค์</h3>
            {history.length === 0 ? (
              <p className="mt-2 text-sm text-muted-strong">ยังไม่มีประวัติ</p>
            ) : (
              <ul className="mt-2 divide-y divide-line">
                {history.map((run) => (
                  <li key={run.id} className="py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge color={statusColor(run.status)}>{STATUS_LABEL[run.status]}</Badge>
                      <span className="text-xs text-muted-strong">{run.trigger_type === "SCHEDULED" ? "ตามกำหนด" : "สั่งโดยผู้ดูแล"} · เริ่ม {dateTime(run.started_at)}</span>
                      {run.completed_at && <span className="text-xs text-muted-strong">เสร็จ {dateTime(run.completed_at)}</span>}
                    </div>
                    <RunSummary run={run} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}

      {isMockData && <p className="mt-3 text-xs text-muted-strong">โหมดสาธิต: ปิดการซิงค์จริง</p>}
      <p className="mt-3 text-xs text-muted-strong">วันที่เผยแพร่จะแสดงจากแหล่งต้นทางเท่านั้น; เวลาซิงค์และเวลานำเข้าระบบเป็นคนละข้อมูลกัน</p>
    </Card>
  );
}
