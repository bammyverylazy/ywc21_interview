import type { Match, ReviewStatus } from "./match";

export type ActivityType = "MATCH_DETECTED" | "REVIEWED" | "ESCALATED" | "ACTION_RECORDED" | "STATUS_UPDATED";

export interface ActivityEvent {
  _id: string;
  activity_type: ActivityType;
  description: string;
  occurred_at: string;
  match_id: string;
  match?: Match;
  actor?: string | null;
  previous_status?: ReviewStatus | null;
  new_status?: ReviewStatus | null;
  notes?: string | null;
}
