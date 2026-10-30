import { LogoMark } from "../brand/Logo";
import { MatchStatusBadge, ReviewStatusBadge } from "../feedback/StatusBadge";
import { DemoDataTag } from "../feedback/DemoDataTag";
import type { MatchStatus, ReviewStatus } from "../../types/match";
// SAMPLE DATA ONLY: placeholder products, not real notices or real products.
const ROWS: { name: string; lot: string; m: MatchStatus; r: ReviewStatus }[] = [
  { name: "ยาตัวอย่าง A", lot: "L-DEMO-01", m: "EXACT_MATCH", r: "PENDING" },
  { name: "ยาตัวอย่าง B", lot: "ไม่ระบุ", m: "POTENTIAL_MATCH", r: "PENDING" },
  { name: "ยาตัวอย่าง C", lot: "L-DEMO-07", m: "NO_MATCH", r: "REVIEWED" },
  { name: "ยาตัวอย่าง D", lot: "L-DEMO-02", m: "POTENTIAL_MATCH", r: "ESCALATED" },
];
const STATS = [["รายการในคลัง", "24"], ["ประกาศที่บันทึก", "6"], ["รอตรวจสอบ", "3"], ["พบรายการตรงกัน", "1"]];
const NAV = ["ภาพรวมระบบ", "คลังยา", "ประกาศแจ้งเตือน", "ผลการตรวจสอบ", "ประวัติการดำเนินการ"];
/** Decorative, non-interactive mock of the app UI built from the same components. */
export function DashboardPreview() {
  return (
    <div aria-hidden="true" className="overflow-hidden rounded-panel border border-line bg-canvas-alt shadow-[0_30px_80px_-30px_rgba(36,59,54,0.25)]">
      <div className="flex items-center gap-1.5 border-b border-line bg-white px-4 py-2.5">
        {[0, 1, 2].map((i) => <span key={i} className="h-2.5 w-2.5 rounded-full bg-line" />)}
        <DemoDataTag className="ml-auto" />
      </div>
      <div className="flex">
        <div className="hidden w-44 shrink-0 space-y-1 border-r border-line bg-white p-3 sm:block">
          <div className="mb-3 flex items-center gap-2 px-2"><LogoMark className="h-5 w-5" /><span className="text-sm font-semibold">ยาเซฟ</span></div>
          {NAV.map((n, i) => <div key={n} className={`rounded-app px-2.5 py-1.5 text-xs ${i === 0 ? "bg-brand-soft font-medium text-brand-dark" : "text-muted-strong"}`}>{n}</div>)}
        </div>
        <div className="min-w-0 flex-1 space-y-3 p-4">
          <p className="text-sm font-medium">ภาพรวมระบบ</p>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            {STATS.map(([k, v]) => <div key={k} className="rounded-app border border-line bg-white p-3"><p className="text-xl font-semibold">{v}</p><p className="text-[11px] text-muted-strong">{k}</p></div>)}
          </div>
          <div className="overflow-hidden rounded-app border border-line bg-white">
            {ROWS.map((r) => (
              <div key={r.name} className="flex items-center gap-3 border-b border-line px-3 py-2 last:border-0">
                <div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">{r.name}</p><p className="text-[11px] text-muted-strong">รุ่นการผลิต {r.lot}</p></div>
                <MatchStatusBadge status={r.m} /><span className="hidden xl:inline"><ReviewStatusBadge status={r.r} /></span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
