"""
Notices router — /api/notices

Endpoints (spec §7.5):
  GET    /api/notices             list notices (paginated, searchable)
  POST   /api/notices             import / create a notice
  GET    /api/notices/{id}        get notice detail
  PUT    /api/notices/{id}        update notice
  DELETE /api/notices/{id}        delete notice (test/incorrectly imported)

Optional query parameters (spec §7.5):
  search          — substring match on product_name and title
  notice_type     — RECALL or WARNING
  registration_no — exact registration number match
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pymongo.database import Database

from app.dependencies import get_db
from app.schemas.notice import NoticeCreate, NoticeOut, NoticeUpdate
from app.schemas.pagination import PaginatedResponse
from app.services import notice_service

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=PaginatedResponse[NoticeOut])
def list_notices(
    search: Optional[str] = Query(default=None, description="Substring search on product name or title"),
    notice_type: Optional[str] = Query(default=None, description="RECALL or WARNING"),
    registration_no: Optional[str] = Query(default=None, description="Filter by registration number"),
    lot_number: Optional[str] = Query(default=None, description="Filter by affected LOT"),
    published_from: Optional[date] = Query(default=None),
    published_to: Optional[date] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    items, total = notice_service.list_notices(
        db,
        search=search,
        notice_type=notice_type,
        registration_no=registration_no,
        lot_number=lot_number,
        published_from=published_from,
        published_to=published_to,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse[NoticeOut](items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
def create_notice(data: NoticeCreate, db: Database = Depends(get_db)):
    return notice_service.create_notice(db, data)


@router.get("/{notice_id}", response_model=NoticeOut)
def get_notice(notice_id: str, db: Database = Depends(get_db)):
    return notice_service.get_notice(db, notice_id)


@router.put("/{notice_id}", response_model=NoticeOut)
def update_notice(notice_id: str, data: NoticeUpdate, db: Database = Depends(get_db)):
    return notice_service.update_notice(db, notice_id, data)


@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice(notice_id: str, db: Database = Depends(get_db)):
    notice_service.delete_notice(db, notice_id)
