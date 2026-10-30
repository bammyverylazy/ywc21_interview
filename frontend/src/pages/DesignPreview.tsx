import { Plus } from "lucide-react";
import { Logo } from "../components/brand/Logo";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { MatchStatusBadge, ReviewStatusBadge } from "../components/feedback/StatusBadge";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { Disclaimer } from "../components/feedback/Disclaimer";
import { EmptyState } from "../components/feedback/EmptyState";
import type { MatchStatus, ReviewStatus } from "../types/match";
const M: MatchStatus[] = ["EXACT_MATCH", "POTENTIAL_MATCH", "NO_MATCH"];
const R: ReviewStatus[] = ["PENDING", "REVIEWED", "ESCALATED", "ACTION_RECORDED"];
/** Temporary Milestone 1 review page; replaced by the router in Milestone 2/3. */
export default function DesignPreview() {
  return (
    <main className="mx-auto max-w-3xl space-y-8 p-6">
      <div className="flex items-center justify-between"><Logo /><Logo variant="mark" className="h-4 w-4" /><DemoDataTag /></div>
      <Card className="space-y-4 p-6">
        <div className="flex flex-wrap gap-2"><Button icon={<Plus className="h-4 w-4" />}>เพิ่มรายการยา</Button><Button variant="secondary">ยกเลิก</Button><Button variant="ghost">ล้างตัวกรอง</Button><Button variant="danger">ลบรายการ</Button><Button loading>บันทึก</Button></div>
        <div className="flex flex-wrap gap-2">{M.map((s) => <MatchStatusBadge key={s} status={s} />)}</div>
        <div className="flex flex-wrap gap-2">{R.map((s) => <ReviewStatusBadge key={s} status={s} />)}</div>
      </Card>
      <div className="glass rounded-panel p-5">ตัวอย่างแผ่นกระจก (ใช้เฉพาะหน้าแรก): ข้อความยังอ่านชัดบนพื้นหลังใดก็ได้</div>
      <EmptyState title="ยังไม่มีรายการยาในคลัง" hint="เพิ่มยาและเลขที่รุ่นการผลิตเพื่อเริ่มตรวจสอบกับประกาศ" />
      <Disclaimer />
    </main>
  );
}
