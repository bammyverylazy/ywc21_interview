import { AlertOctagon, CheckCircle2, CircleHelp, ClipboardCheck, Clock, Eye, Flag, type LucideIcon } from "lucide-react";
import type { MatchStatus, ReviewStatus } from "../../types/match";
import { MATCH_STATUS_LABEL, REVIEW_STATUS_LABEL } from "../../lib/th";
// Always icon + text label; colour only reinforces.
const MATCH: Record<MatchStatus, { cls: string; Icon: LucideIcon }> = {
  EXACT_MATCH: { cls: "bg-danger-soft text-danger border-danger/25", Icon: AlertOctagon },
  POTENTIAL_MATCH: { cls: "bg-warn-soft text-warn border-warn/25", Icon: CircleHelp },
  NO_MATCH: { cls: "bg-calm-soft text-calm border-calm/20", Icon: CheckCircle2 },
};
const REVIEW: Record<ReviewStatus, { cls: string; Icon: LucideIcon }> = {
  PENDING: { cls: "bg-canvas-alt text-muted-strong border-line", Icon: Clock },
  REVIEWED: { cls: "bg-brand-soft text-brand-dark border-brand/20", Icon: Eye },
  ESCALATED: { cls: "bg-warn-soft text-warn border-warn/25", Icon: Flag },
  ACTION_RECORDED: { cls: "bg-brand-soft text-brand-dark border-brand/20", Icon: ClipboardCheck },
};
const base = "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium";
export function MatchStatusBadge({ status }: { status: MatchStatus }) {
  const { cls, Icon } = MATCH[status];
  return <span className={`${base} ${cls}`}><Icon className="h-3.5 w-3.5" aria-hidden="true" />{MATCH_STATUS_LABEL[status]}</span>;
}
export function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  const { cls, Icon } = REVIEW[status];
  return <span className={`${base} ${cls}`}><Icon className="h-3.5 w-3.5" aria-hidden="true" />{REVIEW_STATUS_LABEL[status]}</span>;
}
