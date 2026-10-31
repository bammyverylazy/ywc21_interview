from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.inventory import InventoryOut
from app.schemas.notice import NoticeOut


class MatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    NO_MATCH = "NO_MATCH"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    ESCALATED = "ESCALATED"
    ACTION_RECORDED = "ACTION_RECORDED"


class MatchOut(BaseModel):
    id: str
    inventory_id: str
    notice_id: str
    match_status: MatchStatus
    match_reason: str
    matched_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    checked_at: datetime
    matching_version: str
    review_status: ReviewStatus = ReviewStatus.PENDING
    inventory: Optional[InventoryOut] = None
    notice: Optional[NoticeOut] = None


class ActionCreate(BaseModel):
    status: ReviewStatus
    action_note: str = Field(..., min_length=1, max_length=4000)

    @field_validator("action_note")
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("action_note must not be blank")
        return value.strip()


class ActionLogOut(BaseModel):
    id: str
    match_id: str
    status: ReviewStatus
    action_note: str
    created_at: datetime
    actor: Optional[str] = None


class MatchRunRequest(BaseModel):
    scope: str = Field(default="ALL", pattern="^(ALL|SINGLE_INVENTORY_ITEM)$")
    inventory_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_scope_id(self):
        if self.scope == "SINGLE_INVENTORY_ITEM" and not self.inventory_id:
            raise ValueError("inventory_id is required for SINGLE_INVENTORY_ITEM scope")
        return self


class MatchRunResult(BaseModel):
    total_checked: int
    exact_matches: int
    potential_matches: int
    no_matches: int
