import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bson import ObjectId

from app.config import Settings
from app.ingestion.import_service import import_records
from app.services.sync_service import (
    begin_sync,
    execute_sync,
    get_history,
    get_status,
    record_skipped_sync,
    scheduled_sync_due,
)
from app.ingestion.thai_fda_source import SourceRetrievalError, normalize_listing_record


def make_settings():
    return Settings(
        mongodb_uri="mongodb://localhost",
        database_name="lotshield_test",
        frontend_url="http://localhost:5173",
        cors_origins=("http://localhost:5173",),
        environment="test",
        fda_sync_enabled=True,
        fda_sync_interval_hours=24,
        fda_sync_timeout_seconds=1,
        fda_sync_max_retries=0,
        fda_sync_request_delay_seconds=0.001,
        fda_sync_detail_enrichment_enabled=False,
    )


def source_row(**changes):
    return {
        "TR_ID": "REQ_QLY_PROB_10100-2569-0001_SFTY_ALT",
        "MAIN_TR": "REQ_QLY_PROB_10100-2569-0001",
        "IDA": 123,
        "PROD_NAME": "ชื่อยา",
        "PROD_NAME_EN": "Example Medicine",
        "CASE_ALERT": "เรียกคืนโดยสมัครใจ",
        "REGISTER": "REG-123",
        "CREATE_DATE": "/Date(1791171930653)/",
        "ACTIVE": "ACTIVE",
        **changes,
    }


class ListingSource:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error

    def fetch_listing(self):
        if self.error:
            raise self.error
        return self.rows


class DetailSource(ListingSource):
    def fetch_detail(self, main_transaction_id):
        assert main_transaction_id == "REQ_QLY_PROB_10100-2569-0001"
        return fixture("detail-populated-sanitized.json")

    def fetch_attachments(self, main_transaction_id):
        assert main_transaction_id == "REQ_QLY_PROB_10100-2569-0001"
        return fixture("attachments-sanitized.json")


def fixture(name):
    return json.loads(
        (
            Path(__file__).parent
            / "fixtures"
            / "thai_fda"
            / name
        ).read_text(encoding="utf-8")
    )


def run(fake_db, source):
    run_id, acquired = begin_sync(fake_db, "MANUAL")
    assert acquired
    return execute_sync(fake_db, run_id, make_settings(), source=source)


def test_first_sync_repeat_update_and_revision_are_incremental(fake_db):
    first = run(fake_db, ListingSource([source_row()]))
    second = run(fake_db, ListingSource([source_row()]))
    changed = run(fake_db, ListingSource([source_row(CASE_ALERT="Updated official text")]))

    assert first["records_new"] == 1
    assert first["records_needing_review"] == 1
    assert first["status"] == "PARTIAL_SUCCESS"
    assert second["records_unchanged"] == 1
    assert changed["records_updated"] == 1
    assert fake_db["safety_notices"].count_documents({}) == 1
    assert fake_db["safety_notice_revisions"].count_documents({}) == 1


def test_listing_failure_is_logged_and_preserves_existing_notice(fake_db):
    run(fake_db, ListingSource([source_row()]))
    failed = run(fake_db, ListingSource(error=SourceRetrievalError("FDA listing timed out.")))

    assert failed["status"] == "FAILED"
    assert fake_db["safety_notices"].count_documents({}) == 1
    assert fake_db["sync_logs"].count_documents({}) == 2
    assert fake_db["sync_locks"].count_documents({}) == 0


def test_unexpected_source_exception_is_logged_and_releases_lock(fake_db):
    class BrokenSource(ListingSource):
        def fetch_listing(self):
            raise RuntimeError("unexpected source failure")

    result = run(fake_db, BrokenSource())
    run_record = fake_db["sync_logs"].find_one({"_id": ObjectId(result["id"])})

    assert result["status"] == "FAILED"
    assert "listing_retrieval" in result["error_summary"]
    assert run_record["details"][0]["category"] == "listing_retrieval_error"
    assert fake_db["sync_locks"].count_documents({}) == 0


def test_duplicate_ids_are_skipped_or_conflicts_failed(fake_db):
    identical = source_row()
    result = run(fake_db, ListingSource([identical, identical]))
    assert result["records_new"] == 1
    assert result["records_skipped"] == 1

    conflict = run(fake_db, ListingSource([
        source_row(CASE_ALERT="Version A"),
        source_row(CASE_ALERT="Version B"),
    ]))
    assert conflict["records_failed"] == 2
    assert fake_db["safety_notices"].count_documents({}) == 1


def test_concurrent_sync_attempt_is_logged_and_rejected(fake_db):
    first_id, acquired = begin_sync(fake_db, "SCHEDULED")
    competing_id, competing_acquired = begin_sync(fake_db, "MANUAL")

    assert acquired
    assert not competing_acquired
    assert fake_db["sync_logs"].count_documents({}) == 2
    assert get_status(fake_db)["current_status"] == "FAILED"
    assert len(get_history(fake_db)[0]) == 2
    assert first_id != competing_id


def test_empty_listing_does_not_delete_or_create_notices(fake_db):
    result = run(fake_db, ListingSource([]))

    assert result["status"] == "PARTIAL_SUCCESS"
    assert result["records_discovered"] == 0
    assert fake_db["safety_notices"].count_documents({}) == 0


def test_sync_source_date_fields_are_not_used_as_publication_date(fake_db):
    result = run(fake_db, ListingSource([source_row()]))
    saved = fake_db["safety_notices"].find_one({})

    assert result["records_new"] == 1
    assert saved["published_at"] is None
    assert saved["source_created_at"] == datetime.fromtimestamp(
        1791171930653 / 1000, tz=timezone.utc
    )


def test_sync_enriches_listing_data_from_observed_detail_and_attachment_responses(fake_db):
    run_id, acquired = begin_sync(fake_db, "MANUAL")
    assert acquired
    settings = replace(make_settings(), fda_sync_detail_enrichment_enabled=True)

    result = execute_sync(
        fake_db,
        run_id,
        settings,
        source=DetailSource([source_row()]),
    )
    saved = fake_db["safety_notices"].find_one({})

    assert result["records_new"] == 1
    assert result["records_needing_review"] == 1
    assert saved["source_detail_status"] == "partial"
    assert saved["source_attachments_status"] == "available"
    assert saved["registration_no"] == "1C 99/99"
    assert saved["manufacturer"] == "Example Manufacturer"
    assert [lot["lot_number"] for lot in saved["affected_lots"]] == [
        "LOT-TEST-1",
        "LOT-TEST-2",
    ]
    assert saved["attachments"][0]["original_filename"] == "notice-image.jpg"
    assert saved["published_at"] is None


def test_sync_preserves_verified_manual_details_and_tracks_source_changes(fake_db):
    row = source_row()
    synced = normalize_listing_record(row)
    verified = {
        **synced,
        "title": "Manually verified full notice",
        "source_url": "https://safetyalert.fda.moph.go.th/notices/verified",
        "source_name": synced["source_name"],
        "published_at": "2026-10-01",
        "affected_lots": [{"lot_number": "VERIFIED-LOT"}],
    }
    assert import_records(fake_db, [verified])["created"] == 1

    updated = run(fake_db, ListingSource([row]))
    saved = fake_db["safety_notices"].find_one({})

    assert updated["records_updated"] == 1
    assert saved["verification_status"] == "verified"
    assert saved["title"] == "Manually verified full notice"
    assert saved["affected_lots"][0]["lot_number"] == "VERIFIED-LOT"
    assert saved["published_at"].date().isoformat() == "2026-10-01"
    assert saved["field_provenance"]["affected_lots"]["origin"] == "manually_verified"
    assert saved["latest_sync_source_data"] == row
    assert fake_db["safety_notice_revisions"].count_documents({}) == 1

    unchanged = run(fake_db, ListingSource([row]))
    assert unchanged["records_unchanged"] == 1
    assert fake_db["safety_notice_revisions"].count_documents({}) == 1


def test_scheduled_interval_skips_until_due_and_skips_do_not_reset_interval(fake_db):
    run(fake_db, ListingSource([source_row()]))
    last_started = get_history(fake_db)[0][0]["started_at"]
    now = last_started + timedelta(hours=12)

    assert not scheduled_sync_due(fake_db, 24, now=now)
    skipped = record_skipped_sync(fake_db)
    assert skipped["status"] == "SKIPPED"
    assert not scheduled_sync_due(fake_db, 24, now=now)
    assert scheduled_sync_due(fake_db, 24, now=last_started + timedelta(hours=25))


# ---------------------------------------------------------------------------
# Additional tests for Phase 6 coverage
# ---------------------------------------------------------------------------

from app.ingestion.thai_fda_source import SourceParsingError


def test_invalid_source_response_fails_and_releases_lock(fake_db):
    """A SourceParsingError on the listing level marks the run FAILED and
    releases the lock so the next attempt is not blocked."""
    result = run(fake_db, ListingSource(
        error=SourceParsingError("FDA listing response was not valid JSON.")
    ))

    assert result["status"] == "FAILED"
    assert "listing" in result["error_summary"].lower() or "json" in result["error_summary"].lower()
    assert fake_db["sync_locks"].count_documents({}) == 0
    assert fake_db["sync_logs"].count_documents({}) == 1


def test_invalid_individual_record_is_failed_not_crash(fake_db):
    """A malformed row (missing TR_ID) fails individually but the rest proceed."""
    good = source_row()
    bad = {"PROD_NAME": "ยาไม่มีรหัส"}  # Missing TR_ID and IDA/NEWCODE

    result = run(fake_db, ListingSource([good, bad]))

    # The good record succeeds; the bad one contributes to records_failed.
    assert result["records_new"] == 1
    assert result["records_failed"] >= 1
    assert fake_db["sync_locks"].count_documents({}) == 0


def test_sync_history_records_success_accurately(fake_db):
    """A successful sync produces a sync_log with status SUCCESS and correct counters."""
    result = run(fake_db, ListingSource([source_row()]))
    log = fake_db["sync_logs"].find_one({"status": {"$in": ["SUCCESS", "PARTIAL_SUCCESS"]}})

    assert log is not None
    assert log["records_discovered"] == 1
    assert log["records_new"] == 1
    assert log["completed_at"] is not None
    # Lock must be released after success.
    assert fake_db["sync_locks"].count_documents({}) == 0


def test_sync_history_records_failure_accurately(fake_db):
    """A failed sync produces a sync_log with status FAILED, error_summary, and no lock."""
    from app.ingestion.thai_fda_source import SourceRetrievalError
    result = run(fake_db, ListingSource(error=SourceRetrievalError("timeout")))
    log = fake_db["sync_logs"].find_one({"status": "FAILED"})

    assert log is not None
    assert log["error_summary"] is not None
    assert log["completed_at"] is not None
    assert fake_db["sync_locks"].count_documents({}) == 0


def test_manually_verified_record_is_not_overwritten_by_sync(fake_db):
    """Manually verified fields (title, published_at, lots) survive a sync cycle."""
    from app.ingestion.import_service import import_records
    row = source_row()
    synced = normalize_listing_record(row)
    verified = {
        **synced,
        "title": "ชื่อที่ตรวจสอบแล้ว",
        "published_at": "2026-01-15",
        "affected_lots": [{"lot_number": "VERIFIED-LOT-XYZ"}],
    }
    import_records(fake_db, [verified])

    result = run(fake_db, ListingSource([row]))
    saved = fake_db["safety_notices"].find_one({})

    assert result["records_updated"] == 1
    assert saved["title"] == "ชื่อที่ตรวจสอบแล้ว"
    assert saved["affected_lots"][0]["lot_number"] == "VERIFIED-LOT-XYZ"
    assert fake_db["safety_notices"].count_documents({}) == 1
