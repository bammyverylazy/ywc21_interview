from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.dependencies import get_db
from app.schemas.match import ActionLogOut, MatchOut
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(db: Database = Depends(get_db)):
    return dashboard_service.summary(db)


@router.get("/recent-activity", response_model=list[ActionLogOut])
def get_recent_activity(
    limit: int = Query(default=10, ge=1, le=100),
    db: Database = Depends(get_db),
):
    return dashboard_service.recent_activity(db, limit=limit)


@router.get("/attention-items", response_model=list[MatchOut])
def get_attention_items(
    limit: int = Query(default=20, ge=1, le=100),
    db: Database = Depends(get_db),
):
    return dashboard_service.attention_items(db, limit=limit)
