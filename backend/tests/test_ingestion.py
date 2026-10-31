from datetime import datetime, timezone

from app.ingestion.import_service import import_records
from app.ingestion.validator import validate_official_source


def valid_record(**overrides):
    return {
        "title": "Verified source notice",
        "notice_type": "RECALL",
        "product_name": "Medicine A",
        "source_name": "Thai FDA",
        "source_url": "https://safetyalert.fda.moph.go.th/notices/123",
        "published_at": "2026-10-30",
        "registration_no": "REG-A",
        "affected_lots": [{"lot_number": "LOT-A"}],
        **overrides,
    }


def test_official_source_requires_https_and_official_hostname():
    validate_official_source("https://safetyalert.fda.moph.go.th/notice/123")

    for url in (
        "http://safetyalert.fda.moph.go.th/notice/123",
        "https://fda.moph.go.th.attacker.example/notice/123",
        "https://example.com/notice/123",
    ):
        try:
            validate_official_source(url)
        except ValueError:
            continue
        raise AssertionError(f"Unexpectedly accepted source URL: {url}")


def test_import_records_upserts_verified_record_and_flags_missing_lot(fake_db):
    first = import_records(fake_db, [valid_record()])
    second = import_records(fake_db, [valid_record()])
    incomplete = import_records(fake_db, [valid_record(
        source_url="https://safetyalert.fda.moph.go.th/notices/456",
        affected_lots=[],
    )])

    assert first["created"] == 1
    assert second["updated"] == 1
    assert incomplete["requires_manual_review"][0]["missing_fields"] == ["affected_lots"]
    assert fake_db["safety_notices"].count_documents({}) == 2
    notice = fake_db["safety_notices"].find_one({"source_url": valid_record()["source_url"]})
    assert notice["record_origin"] == "verified_import"
    assert notice["verification_status"] == "verified"


def test_import_rejects_non_official_source_without_persisting(fake_db):
    result = import_records(fake_db, [valid_record(source_url="https://example.com/fake")])

    assert result["failed"] == 1
    assert fake_db["safety_notices"].count_documents({}) == 0


def test_manual_import_marks_field_level_values_as_verified(fake_db):
    imported = import_records(fake_db, [valid_record()])
    notice = fake_db["safety_notices"].find_one({"source_url": valid_record()["source_url"]})

    assert imported["created"] == 1
    assert notice["field_provenance"]["registration_no"]["origin"] == "manually_verified"
    assert notice["field_provenance"]["registration_no"]["verification_status"] == "verified"
    assert notice["field_provenance"]["manufacturer"]["origin"] == "missing"


def test_manual_import_preserves_multiple_lots(fake_db):
    record = valid_record(affected_lots=[
        {"lot_number": "LOT-A", "manufacturing_date": "2025-01-01"},
        {"lot_number": "LOT-B", "expiry_date": "2027-01-01"},
    ])

    result = import_records(fake_db, [record])
    notice = fake_db["safety_notices"].find_one({"source_url": record["source_url"]})

    assert result["created"] == 1
    assert [lot["lot_number"] for lot in notice["affected_lots"]] == ["LOT-A", "LOT-B"]
    assert notice["affected_lots"][0]["verification_status"] == "verified"
    assert notice["affected_lots"][0]["extraction_method"] == (
        "manual_official_source_review"
    )
    assert notice["affected_lots"][0]["source_reference"] == record["source_url"]
    assert notice["published_at"] == datetime(2026, 10, 30, tzinfo=timezone.utc)
    assert notice["affected_lots"][0]["manufacturing_date"] == datetime(
        2025, 1, 1, tzinfo=timezone.utc
    )
    assert notice["affected_lots"][1]["expiry_date"] == datetime(
        2027, 1, 1, tzinfo=timezone.utc
    )
