from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.dependencies import get_db
from app.schemas.activity import ActivityOut
from app.schemas.match import ReviewStatus
from app.schemas.pagination import PaginatedResponse
from app.services import activity_service

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=PaginatedResponse[ActivityOut])
def list_activity(
    search: Optional[str] = Query(default=None, max_length=200),
    activity_type: Optional[str] = Query(default=None, max_length=40),
    review_status: Optional[ReviewStatus] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    if date_from and date_to and date_from > date_to:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_from must not be after date_to.")
    items, total = activity_service.list_activity(
        db,
        search=search,
        activity_type=activity_type,
        review_status=review_status.value if review_status else None,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse[ActivityOut](items=items, total=total, skip=skip, limit=limit)


@router.get("/{event_id}", response_model=ActivityOut)
def get_activity(event_id: str, db: Database = Depends(get_db)):
    return activity_service.get_activity(db, event_id)
