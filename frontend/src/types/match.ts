import type { InventoryItem } from "./inventory";
import type { SafetyNotice } from "./notice";
export type MatchStatus = "EXACT_MATCH" | "POTENTIAL_MATCH" | "NO_MATCH";
export type ReviewStatus = "PENDING" | "REVIEWED" | "ESCALATED" | "ACTION_RECORDED";
export interface Match {
  _id: string; inventory_id: string; notice_id: string; match_status: MatchStatus; match_reason: string;
  matched_fields: string[]; missing_fields?: string[]; checked_at: string; matching_version: string;
  review_status?: ReviewStatus;          // ASSUMED: backend supplies current status (open item 6)
  inventory?: InventoryItem; notice?: SafetyNotice; // ASSUMED: expanded by backend (open item 5)
}
export interface ActionLog { _id: string; match_id: string; status: ReviewStatus; action_note: string; created_at: string; }
