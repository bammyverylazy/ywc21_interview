from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.database import Database

from app.config import Settings
from app.ingestion.import_service import upsert_synced_record
from app.ingestion.thai_fda_source import (
    SOURCE_NAME,
    SourceParsingError,
    SourceRetrievalError,
    ThaiFdaSource,
    enrich_listing_record,
    normalize_listing_record,
)

logger = logging.getLogger("YaSafe.sync")
LOCK_ID = "thai-fda-drug-alert"
LOCK_LEASE = timedelta(minutes=30)
MANUAL_SYNC_COOLDOWN = timedelta(seconds=60)
DETAILS_LIMIT = 100


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalise a datetime to timezone-aware UTC.

    PyMongo deserialises BSON UTC datetimes as *naive* ``datetime`` objects
    (``tzinfo=None``).  The application generates *aware* UTC datetimes via
    ``_now()``.  Comparing the two directly raises::

        TypeError: can't compare offset-naive and offset-aware datetimes

    This helper converts any naive datetime to explicit UTC before comparison,
    leaves already-aware datetimes unchanged, and passes ``None`` through so
    callers can chain ``_as_utc(value) <= _now()`` without a prior None-check.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _safe_detail(category: str, message: str, **fields: Any) -> dict[str, Any]:
    return {"category": category, "message": message, **fields}


def _insert_run(db: Database, trigger_type: Literal["MANUAL", "SCHEDULED"]) -> str:
    now = _now()
    result = db["sync_logs"].insert_one({
        "source_name": SOURCE_NAME,
        "started_at": now,
        "completed_at": None,
        "status": "RUNNING",
        "trigger_type": trigger_type,
        "lock_acquired": False,
        "records_discovered": 0,
        "records_new": 0,
        "records_updated": 0,
        "records_unchanged": 0,
        "records_skipped": 0,
        "records_failed": 0,
        "records_needing_review": 0,
        "error_summary": None,
        "details": [],
    })
    return str(result.inserted_id)


def _acquire_lock(db: Database, run_id: str) -> bool:
    now = _now()
    lease = {
        "run_id": run_id,
        "acquired_at": now,
        "lease_expires_at": now + LOCK_LEASE,
    }
    existing = db["sync_locks"].find_one_and_update(
        {"_id": LOCK_ID, "lease_expires_at": {"$lte": now}},
        {"$set": lease},
        return_document=True,
    )
    if existing is not None:
        return True
    try:
        db["sync_locks"].insert_one({"_id": LOCK_ID, **lease})
        return True
    except DuplicateKeyError:
        return False


def _finish(
    db: Database,
    run_id: str,
    *,
    status: str,
    counters: dict[str, int],
    details: list[dict[str, Any]],
    error_summary: str | None = None,
) -> dict[str, Any]:
    completed_at = _now()
    update = {
        **counters,
        "status": status,
        "completed_at": completed_at,
        "details": details[:DETAILS_LIMIT],
        "details_omitted": max(0, len(details) - DETAILS_LIMIT),
        "error_summary": error_summary,
    }
    try:
        db["sync_logs"].find_one_and_update(
            {"_id": ObjectId(run_id)},
            {"$set": update},
            return_document=True,
        )
    finally:
        try:
            db["sync_locks"].delete_one({"_id": LOCK_ID, "run_id": run_id})
        except PyMongoError:
            logger.exception(
                "Could not release Thai FDA sync lock for run %s; it will expire after the lease.",
                run_id,
            )
    return {"id": run_id, **update}


def begin_sync(
    db: Database,
    trigger_type: Literal["MANUAL", "SCHEDULED"],
) -> tuple[str, bool]:
    """Persist every attempt, acquiring a MongoDB-backed cross-process lease."""
    run_id = _insert_run(db, trigger_type)
    try:
        acquired = _acquire_lock(db, run_id)
    except PyMongoError:
        try:
            db["sync_logs"].find_one_and_update(
                {"_id": ObjectId(run_id)},
                {"$set": {
                    "status": "FAILED",
                    "completed_at": _now(),
                    "error_summary": "MongoDB failed while acquiring the sync lock.",
                    "details": [_safe_detail(
                        "mongodb_lock_acquisition",
                        "MongoDB failed while acquiring the synchronization lock.",
                    )],
                }},
                return_document=True,
            )
        except PyMongoError:
            logger.exception(
                "Could not record lock acquisition failure for sync run %s.",
                run_id,
            )
        finally:
            try:
                db["sync_locks"].delete_one({"_id": LOCK_ID, "run_id": run_id})
            except PyMongoError:
                logger.exception(
                    "Could not clean up lock after acquisition failure for run %s.",
                    run_id,
                )
        raise

    if acquired:
        db["sync_logs"].find_one_and_update(
            {"_id": ObjectId(run_id)},
            {"$set": {"lock_acquired": True}},
            return_document=True,
        )
        return run_id, True

    now = _now()
    db["sync_logs"].find_one_and_update(
        {"_id": ObjectId(run_id)},
        {"$set": {
            "status": "FAILED",
            "completed_at": now,
            "error_summary": "Another FDA synchronization is already running.",
            "details": [_safe_detail("lock_contention", "Another run holds the sync lock.")],
        }},
        return_document=True,
    )
    return run_id, False


def manual_sync_cooldown_remaining(
    db: Database,
    *,
    now: datetime | None = None,
) -> int:
    """Return seconds remaining in the manual-trigger cooldown, or zero."""
    recent_runs = db["sync_logs"].find({"trigger_type": "MANUAL"}).sort(
        "started_at", -1
    )
    latest_accepted = next(
        (run for run in recent_runs if run.get("lock_acquired") is not False),
        None,
    )
    if latest_accepted is None:
        return 0

    started_at = _as_utc(latest_accepted["started_at"])
    remaining = started_at + MANUAL_SYNC_COOLDOWN - (now or _now())
    return max(0, int(remaining.total_seconds() + 0.999))


def sync_is_running(db: Database, *, now: datetime | None = None) -> bool:
    """Report whether a non-expired MongoDB sync lease is held."""
    lock = db["sync_locks"].find_one({"_id": LOCK_ID})
    if lock is None:
        return False
    expires_at = _as_utc(lock.get("lease_expires_at"))
    if expires_at is None:
        return False
    return expires_at > (now or _now())


def scheduled_sync_due(
    db: Database,
    interval_hours: int,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether the configured interval has elapsed since a non-skipped run."""
    latest = db["sync_logs"].find({
        "status": {"$in": ["RUNNING", "SUCCESS", "PARTIAL_SUCCESS", "FAILED"]}
    }).sort("started_at", -1).limit(1)
    last_run = next(iter(latest), None)
    if last_run is None:
        return True
    last_started = _as_utc(last_run["started_at"])
    return (now or _now()) - last_started >= timedelta(hours=interval_hours)


def record_skipped_sync(db: Database) -> dict[str, Any]:
    """Persist a schedule check that did not need to fetch the source."""
    run_id = _insert_run(db, "SCHEDULED")
    return _finish(
        db,
        run_id,
        status="SKIPPED",
        counters={
            "records_discovered": 0,
            "records_new": 0,
            "records_updated": 0,
            "records_unchanged": 0,
            "records_skipped": 0,
            "records_failed": 0,
            "records_needing_review": 0,
        },
        details=[_safe_detail(
            "scheduled_interval",
            "The configured FDA synchronization interval has not elapsed.",
        )],
    )


def _fingerprint(value: Any) -> str:
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key != "raw_source_data"}
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _review_fields(record: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not record.get("published_at"):
        missing.append("published_at")
    if not record.get("registration_no"):
        missing.append("registration_no")
    if not record.get("affected_lots"):
        missing.append("affected_lots")
    if not record.get("manufacturer"):
        missing.append("manufacturer")
    return missing


def execute_sync(
    db: Database,
    run_id: str,
    settings: Settings,
    *,
    source: ThaiFdaSource | None = None,
) -> dict[str, Any]:
    """Fetch one official listing and safely upsert records without deleting data."""
    counters = {
        "records_discovered": 0,
        "records_new": 0,
        "records_updated": 0,
        "records_unchanged": 0,
        "records_skipped": 0,
        "records_failed": 0,
        "records_needing_review": 0,
    }
    details: list[dict[str, Any]] = []
    owned_source = source is None
    stage = "source_initialization"
    client = source or ThaiFdaSource(
        timeout_seconds=settings.fda_sync_timeout_seconds,
        max_retries=settings.fda_sync_max_retries,
        request_delay_seconds=settings.fda_sync_request_delay_seconds,
    )
    try:
        stage = "listing_retrieval"
        try:
            listing = client.fetch_listing()
        except SourceRetrievalError as exc:
            logger.warning("FDA listing retrieval failed: %s", exc)
            details.append(_safe_detail(
                "source_request",
                str(exc),
                stage="listing_retrieval",
            ))
            return _finish(
                db,
                run_id,
                status="FAILED",
                counters=counters,
                details=details,
                error_summary=str(exc),
            )
        except SourceParsingError as exc:
            logger.warning("FDA listing parsing failed: %s", exc)
            details.append(_safe_detail(
                "source_parsing",
                str(exc),
                stage="listing_parsing",
            ))
            return _finish(
                db,
                run_id,
                status="FAILED",
                counters=counters,
                details=details,
                error_summary=str(exc),
            )

        counters["records_discovered"] = len(listing)
        if not listing:
            details.append(_safe_detail(
                "empty_listing",
                "The official listing returned no records; existing notices were retained.",
            ))
            return _finish(
                db,
                run_id,
                status="PARTIAL_SUCCESS",
                counters=counters,
                details=details,
                error_summary="The official FDA listing returned no records.",
            )

        candidates: dict[str, tuple[dict[str, Any], str]] = {}
        conflicts: set[str] = set()
        stage = "record_normalization"
        for index, raw_record in enumerate(listing):
            try:
                record = normalize_listing_record(raw_record)
                source_id = record["source_id"]
                fingerprint = _fingerprint(record)
                if source_id in conflicts:
                    counters["records_failed"] += 1
                    continue
                previous = candidates.get(source_id)
                if previous is None:
                    candidates[source_id] = (record, fingerprint)
                elif previous[1] == fingerprint:
                    counters["records_skipped"] += 1
                else:
                    candidates.pop(source_id)
                    conflicts.add(source_id)
                    counters["records_failed"] += 2
                    details.append(_safe_detail(
                        "duplicate_identity_conflict",
                        "Multiple listing rows share a stable identifier but differ.",
                        source_id=source_id,
                    ))
            except SourceParsingError as exc:
                counters["records_failed"] += 1
                details.append(_safe_detail(
                    "source_parsing",
                    str(exc),
                    stage="record_normalization",
                    record_index=index,
                ))

        consecutive_detail_failures = 0
        detail_enrichment_aborted = False
        for source_id, (record, _) in candidates.items():
            if settings.fda_sync_detail_enrichment_enabled and not detail_enrichment_aborted:
                stage = "detail_enrichment"
                main_transaction_id = record.get("source_detail_id")
                if not main_transaction_id:
                    record["source_detail_status"] = "failed"
                    record["source_attachments_status"] = "failed"
                    consecutive_detail_failures += 1
                    details.append(_safe_detail(
                        "detail_enrichment",
                        "The listing row did not include the MAIN_TR value used by the FDA detail page.",
                        source_id=source_id,
                    ))
                else:
                    try:
                        detail_payload = client.fetch_detail(main_transaction_id)
                    except (SourceRetrievalError, SourceParsingError) as exc:
                        record["source_detail_status"] = "failed"
                        consecutive_detail_failures += 1
                        logger.warning(
                            "FDA detail enrichment failed for %s: %s",
                            source_id,
                            exc,
                        )
                        details.append(_safe_detail(
                            "detail_enrichment",
                            str(exc),
                            stage="detail_retrieval",
                            source_id=source_id,
                        ))
                    else:
                        try:
                            attachment_payload = client.fetch_attachments(
                                main_transaction_id
                            )
                        except (SourceRetrievalError, SourceParsingError) as exc:
                            record = enrich_listing_record(record, detail_payload)
                            record["source_detail_status"] = "partial"
                            record["source_attachments_status"] = "failed"
                            consecutive_detail_failures += 1
                            logger.warning(
                                "FDA attachment retrieval failed for %s: %s",
                                source_id,
                                exc,
                            )
                            details.append(_safe_detail(
                                "attachment_retrieval",
                                str(exc),
                                stage="attachment_retrieval",
                                source_id=source_id,
                            ))
                        else:
                            try:
                                record = enrich_listing_record(
                                    record,
                                    detail_payload,
                                    attachment_payload,
                                )
                            except SourceParsingError as exc:
                                record["source_detail_status"] = "failed"
                                consecutive_detail_failures += 1
                                details.append(_safe_detail(
                                    "detail_parsing",
                                    str(exc),
                                    stage="detail_parsing",
                                    source_id=source_id,
                                ))
                            else:
                                consecutive_detail_failures = 0
                if consecutive_detail_failures >= 3:
                    detail_enrichment_aborted = True
                    details.append(_safe_detail(
                        "detail_enrichment_stopped",
                        "Further detail requests were skipped after three consecutive failures; listing synchronization continues.",
                        source_id=source_id,
                    ))
            elif settings.fda_sync_detail_enrichment_enabled:
                record["source_detail_status"] = "not_requested"
                record["source_attachments_status"] = "not_requested"

            missing = _review_fields(record)
            if missing:
                counters["records_needing_review"] += 1
                details.append(_safe_detail(
                    "manual_review",
                    "The FDA source omits safety-critical or publication fields.",
                    source_id=source_id,
                    missing_fields=missing,
                ))
            try:
                stage = "mongodb_persistence"
                outcome = upsert_synced_record(db, record, sync_run_id=run_id)
                counters[{"new": "records_new", "updated": "records_updated", "unchanged": "records_unchanged"}[outcome]] += 1
            except Exception as exc:
                logger.exception("Could not persist FDA source record %s", source_id)
                counters["records_failed"] += 1
                details.append(_safe_detail(
                    "database_persistence",
                    f"Record persistence failed ({type(exc).__name__}).",
                    stage="mongodb_persistence",
                    source_id=source_id,
                ))

        processed = (
            counters["records_new"]
            + counters["records_updated"]
            + counters["records_unchanged"]
        )
        if counters["records_failed"] and not processed:
            status = "FAILED"
        elif counters["records_failed"] or counters["records_needing_review"]:
            status = "PARTIAL_SUCCESS"
        else:
            status = "SUCCESS"
        error_summary = (
            f"{counters['records_failed']} record(s) failed; "
            f"{counters['records_needing_review']} require manual review."
            if status == "PARTIAL_SUCCESS"
            else None
        )
        return _finish(
            db,
            run_id,
            status=status,
            counters=counters,
            details=details,
            error_summary=error_summary,
        )
    except Exception as exc:
        logger.exception(
            "Unexpected FDA synchronization failure during %s for run %s.",
            stage,
            run_id,
        )
        return _finish(
            db,
            run_id,
            status="FAILED",
            counters=counters,
            details=details + [_safe_detail(
                f"{stage}_error",
                f"Synchronization failed during {stage} ({type(exc).__name__}).",
            )],
            error_summary=f"Synchronization failed during {stage} ({type(exc).__name__}).",
        )
    finally:
        if owned_source:
            client.close()


def _as_run(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    result = dict(document)
    result["id"] = str(result.pop("_id"))
    return result


def get_history(db: Database, *, skip: int = 0, limit: int = 20) -> tuple[list[dict], int]:
    total = db["sync_logs"].count_documents({})
    runs = [
        _as_run(document)
        for document in db["sync_logs"].find({}).sort("started_at", -1).skip(skip).limit(limit)
    ]
    return runs, total


def get_run(db: Database, run_id: str) -> dict:
    try:
        object_id = ObjectId(run_id)
    except (InvalidId, TypeError) as exc:
        raise ValueError("Invalid synchronization run id.") from exc
    document = db["sync_logs"].find_one({"_id": object_id})
    if document is None:
        raise LookupError("Synchronization run not found.")
    return _as_run(document)


def get_status(db: Database) -> dict[str, Any]:
    latest = db["sync_logs"].find({}).sort("started_at", -1).limit(1)
    last_run = next(iter(latest), None)
    if last_run and last_run.get("status") == "RUNNING":
        lock = db["sync_locks"].find_one({"_id": LOCK_ID, "run_id": str(last_run["_id"])})
        if lock is None or _as_utc(lock.get("lease_expires_at")) <= _now():
            db["sync_logs"].find_one_and_update(
                {"_id": last_run["_id"], "status": "RUNNING"},
                {"$set": {
                    "status": "FAILED",
                    "completed_at": _now(),
                    "error_summary": "Synchronization worker stopped before completion.",
                    "details": [_safe_detail(
                        "worker_interrupted",
                        "The run lease expired before the worker completed.",
                    )],
                }},
                return_document=True,
            )
            db["sync_locks"].delete_one({"_id": LOCK_ID, "run_id": str(last_run["_id"])})
            last_run = db["sync_logs"].find_one({"_id": last_run["_id"]})

    successful = db["sync_logs"].find({"status": {"$in": ["SUCCESS", "PARTIAL_SUCCESS"]}}).sort("completed_at", -1).limit(1)
    last_success = next(iter(successful), None)
    normalized_run = _as_run(last_run)
    return {
        "current_status": normalized_run["status"] if normalized_run else "NOT_RUN",
        "last_attempted_at": normalized_run.get("started_at") if normalized_run else None,
        "last_successful_at": last_success.get("completed_at") if last_success else None,
        "last_run": normalized_run,
    }
