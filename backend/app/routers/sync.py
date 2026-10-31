from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pymongo.errors import PyMongoError
from pymongo.database import Database

from app.config import ConfigurationError, get_settings
from app.dependencies import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.sync import SyncRunOut, SyncStatusOut, SyncTriggerOut
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["synchronization"])
logger = logging.getLogger("YaSafe.sync.api")


@router.get("/status", response_model=SyncStatusOut)
def read_sync_status(db: Database = Depends(get_db)):
    return sync_service.get_status(db)


@router.get("/history", response_model=PaginatedResponse[SyncRunOut])
def read_sync_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Database = Depends(get_db),
):
    items, total = sync_service.get_history(db, skip=skip, limit=limit)
    return PaginatedResponse[SyncRunOut](items=items, total=total, skip=skip, limit=limit)


@router.get("/history/{run_id}", response_model=SyncRunOut)
def read_sync_run(run_id: str, db: Database = Depends(get_db)):
    try:
        return sync_service.get_run(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/thai-fda",
    response_model=SyncTriggerOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_thai_fda_sync(
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
):
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        logger.exception("Manual Thai FDA sync configuration failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "category": "configuration_error",
                "stage": "configuration",
                "message": str(exc),
            },
        ) from exc
    if not settings.fda_sync_enabled:
        logger.warning("Manual Thai FDA sync rejected: FDA_SYNC_ENABLED is false.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "category": "sync_disabled",
                "stage": "configuration",
                "message": (
                    "Thai FDA synchronization is disabled. Set FDA_SYNC_ENABLED=true "
                    "in backend/.env and restart the backend."
                ),
            },
        )
    try:
        if sync_service.sync_is_running(db):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "category": "sync_already_running",
                    "stage": "lock_check",
                    "message": "A Thai FDA synchronization is already running.",
                },
            )
        cooldown_seconds = sync_service.manual_sync_cooldown_remaining(db)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.exception("MongoDB failed while checking sync lock and cooldown.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "category": "mongodb_unavailable",
                "stage": "lock_check",
                "message": "Cannot access MongoDB to check synchronization status.",
            },
        ) from exc
    if cooldown_seconds:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "category": "sync_cooldown",
                "stage": "rate_limit",
                "message": (
                    "Please wait before starting another synchronization. "
                    f"Try again in {cooldown_seconds} seconds."
                ),
            },
            headers={"Retry-After": str(cooldown_seconds)},
        )

    try:
        run_id, acquired = sync_service.begin_sync(db, "MANUAL")
    except PyMongoError as exc:
        logger.exception("MongoDB failed while acquiring the synchronization lock.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "category": "mongodb_unavailable",
                "stage": "lock_acquisition",
                "message": "Cannot start synchronization because MongoDB is unavailable.",
            },
        ) from exc
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "category": "sync_already_running",
                "stage": "lock_acquisition",
                "message": "A Thai FDA synchronization is already running.",
                "run_id": run_id,
            },
        )
    background_tasks.add_task(sync_service.execute_sync, db, run_id, settings)
    return SyncTriggerOut(
        run_id=run_id,
        status="RUNNING",
        message="Thai FDA listing synchronization started.",
    )
