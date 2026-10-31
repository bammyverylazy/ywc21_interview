from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.match import MatchOut, ReviewStatus


class ActivityOut(BaseModel):
    id: str
    activity_type: str
    description: str
    occurred_at: datetime
    match_id: str
    match: Optional[MatchOut] = None
    actor: Optional[str] = None
    previous_status: Optional[ReviewStatus] = None
    new_status: Optional[ReviewStatus] = None
    notes: Optional[str] = None
