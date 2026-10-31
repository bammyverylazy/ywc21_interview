from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.dependencies import get_db
from app.schemas.match import (
    ActionCreate,
    ActionLogOut,
    MatchOut,
    MatchRunRequest,
    MatchRunResult,
    MatchStatus,
    ReviewStatus,
)
from app.schemas.pagination import PaginatedResponse
from app.services import matching_service
from app.utils.object_id import parse_object_id

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=PaginatedResponse[MatchOut])
def list_matches(
    match_status: Optional[MatchStatus] = Query(default=None),
    review_status: Optional[ReviewStatus] = Query(default=None),
    product_id: Optional[str] = Query(default=None),
    notice_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    items, total = matching_service.list_matches(
        db,
        match_status=match_status.value if match_status else None,
        review_status=review_status.value if review_status else None,
        product_id=product_id,
        notice_id=notice_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse[MatchOut](items=items, total=total, skip=skip, limit=limit)


@router.post("/run", response_model=MatchRunResult)
def run_matching(data: Optional[MatchRunRequest] = None, db: Database = Depends(get_db)):
    scope = data.scope if data else "ALL"
    inventory_id = data.inventory_id if data and scope == "SINGLE_INVENTORY_ITEM" else None
    if scope == "SINGLE_INVENTORY_ITEM" and inventory_id:
        inventory = db["inventory_items"].find_one({"_id": parse_object_id(inventory_id)})
        if inventory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found.")
    result = matching_service.run_matching(db, inventory_id=inventory_id)
    return result


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: str, db: Database = Depends(get_db)):
    return matching_service.get_match(db, match_id)


@router.get("/{match_id}/actions", response_model=list[ActionLogOut])
def get_actions(match_id: str, db: Database = Depends(get_db)):
    return matching_service.list_actions(db, match_id)


@router.post(
    "/{match_id}/actions",
    response_model=ActionLogOut,
    status_code=status.HTTP_201_CREATED,
)
def create_action(match_id: str, data: ActionCreate, db: Database = Depends(get_db)):
    return matching_service.add_action(db, match_id, data.status, data.action_note)
