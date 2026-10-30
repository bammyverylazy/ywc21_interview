import { useState } from "react";
import { Play } from "lucide-react";
import { Button } from "../ui/Button";
import * as svc from "../../services";

interface Result { total_checked: number; exact_matches: number; potential_matches: number; no_matches: number }

export function RunMatchingButton({ onComplete }: { onComplete?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true); setResult(null); setError(null);
    try {
      const r = await svc.runMatching();
      setResult(r);
      onComplete?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "เกิดข้อผิดพลาด");
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button icon={<Play className="h-4 w-4" />} loading={loading} onClick={run}>
        ตรวจสอบคลังกับประกาศ
      </Button>
      {result && !loading && (
        <p className="text-sm text-muted-strong">
          ตรวจสอบแล้ว {result.total_checked} รายการ ·
          พบตรงกัน {result.exact_matches} · อาจเกี่ยวข้อง {result.potential_matches} · ไม่ตรงกัน {result.no_matches}
        </p>
      )}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    </div>
  );
}
