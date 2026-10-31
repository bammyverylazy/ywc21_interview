export type SyncStatusValue =
  | "RUNNING"
  | "SUCCESS"
  | "PARTIAL_SUCCESS"
  | "FAILED"
  | "SKIPPED"
  | "NOT_RUN";

export interface SyncDetail {
  category: string;
  message: string;
  stage?: string;
  source_id?: string;
  missing_fields?: string[];
  record_index?: number;
}

export interface SyncRun {
  id: string;
  source_name: string;
  started_at: string;
  completed_at?: string | null;
  status: Exclude<SyncStatusValue, "NOT_RUN">;
  trigger_type: "MANUAL" | "SCHEDULED";
  records_discovered: number;
  records_new: number;
  records_updated: number;
  records_unchanged: number;
  records_skipped: number;
  records_failed: number;
  records_needing_review: number;
  error_summary?: string | null;
  details: SyncDetail[];
  details_omitted?: number;
}

export interface SyncStatus {
  current_status: SyncStatusValue;
  last_attempted_at?: string | null;
  last_successful_at?: string | null;
  last_run?: SyncRun | null;
}

export interface SyncHistoryPage {
  items: SyncRun[];
  total: number;
  skip: number;
  limit: number;
}

export interface SyncTriggerResult {
  run_id: string;
  status: "RUNNING";
  message: string;
}
