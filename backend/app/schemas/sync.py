from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SyncStatus = Literal["RUNNING", "SUCCESS", "PARTIAL_SUCCESS", "FAILED", "SKIPPED"]
SyncTrigger = Literal["MANUAL", "SCHEDULED"]


class SyncRunOut(BaseModel):
    id: str
    source_name: str
    started_at: datetime
    completed_at: datetime | None = None
    status: SyncStatus
    trigger_type: SyncTrigger
    records_discovered: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    records_needing_review: int = 0
    error_summary: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)
    details_omitted: int = 0


class SyncStatusOut(BaseModel):
    current_status: SyncStatus | Literal["NOT_RUN"]
    last_attempted_at: datetime | None = None
    last_successful_at: datetime | None = None
    last_run: SyncRunOut | None = None


class SyncTriggerOut(BaseModel):
    run_id: str
    status: Literal["RUNNING"]
    message: str
