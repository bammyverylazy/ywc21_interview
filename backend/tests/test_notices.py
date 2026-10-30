"""
Tests for /api/notices endpoints.

Coverage:
  POST   /api/notices             create — valid full, minimal (no lots/reg),
                                          missing required fields, duplicate URL
  GET    /api/notices             list — empty, with items, filter by notice_type
  GET    /api/notices/{id}        get — found, not found, invalid id
  PUT    /api/notices/{id}        update — partial update, completeness recomputed
  DELETE /api/notices/{id}        delete — success, not found,
                                          dependent matches cleaned up

Key safety notice invariants tested:
  - Missing lot information does NOT cause import failure
  - Missing registration_no does NOT cause import failure
  - data_completeness is computed automatically and reflects actual fields
  - Duplicate source_url returns 409, not 201
"""

import pytest
from bson import ObjectId

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_NOTICE = {
    "title": "ประกาศเรียกคืนยา XYZ",
    "notice_type": "RECALL",
    "product_name": "ยา XYZ",
    "registration_no": "1A-99/00",
    "affected_lots": ["L25001", "L25002"],
    "reason": "พบปัญหาคุณภาพในกระบวนการผลิต",
    "published_at": "2026-10-20",
    "source_name": "สำนักงานคณะกรรมการอาหารและยา",
    "source_url": "https://fda.moph.go.th/recall/001",
}

MINIMAL_NOTICE = {
    "title": "ประกาศเตือนยา ABC",
    "notice_type": "WARNING",
    "product_name": "ยา ABC",
    "published_at": "2026-09-15",
    "source_url": "https://fda.moph.go.th/warning/002",
}


def _create(client, payload: dict) -> dict:
    resp = client.post("/api/notices", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/notices
# ---------------------------------------------------------------------------


def test_create_full_notice_returns_201(client):
    body = _create(client, VALID_NOTICE)
    assert "id" in body
    assert body["title"] == "ประกาศเรียกคืนยา XYZ"
    assert body["notice_type"] == "RECALL"
    assert body["registration_no"] == "1A-99/00"
    assert body["affected_lots"] == ["L25001", "L25002"]
    assert "imported_at" in body


def test_create_minimal_notice_no_lots_no_reg(client):
    """Missing lot information must NOT cause an import failure (spec Phase 3 criteria)."""
    body = _create(client, MINIMAL_NOTICE)
    assert body["affected_lots"] == []
    assert body["registration_no"] is None
    assert body["generic_name"] is None


def test_create_notice_data_completeness_full(client):
    body = _create(client, VALID_NOTICE)
    dc = body["data_completeness"]
    assert dc["has_registration_no"] is True
    assert dc["has_lot_information"] is True
    assert dc["has_manufacturer"] is False  # not supplied in VALID_NOTICE


def test_create_notice_data_completeness_minimal(client):
    body = _create(client, MINIMAL_NOTICE)
    dc = body["data_completeness"]
    assert dc["has_registration_no"] is False
    assert dc["has_lot_information"] is False
    assert dc["has_manufacturer"] is False


def test_create_notice_strips_lot_whitespace(client):
    payload = {**VALID_NOTICE, "affected_lots": ["  L25001  ", " L25002"], "source_url": "https://fda.moph.go.th/recall/002"}
    body = _create(client, payload)
    assert body["affected_lots"] == ["L25001", "L25002"]


def test_create_notice_missing_title_returns_422(client):
    payload = {k: v for k, v in VALID_NOTICE.items() if k != "title"}
    resp = client.post("/api/notices", json=payload)
    assert resp.status_code == 422


def test_create_notice_missing_product_name_returns_422(client):
    payload = {k: v for k, v in VALID_NOTICE.items() if k != "product_name"}
    resp = client.post("/api/notices", json=payload)
    assert resp.status_code == 422


def test_create_notice_missing_source_url_returns_422(client):
    payload = {k: v for k, v in VALID_NOTICE.items() if k != "source_url"}
    resp = client.post("/api/notices", json=payload)
    assert resp.status_code == 422


def test_create_notice_invalid_source_url_returns_422(client):
    payload = {**VALID_NOTICE, "source_url": "not-a-url"}
    resp = client.post("/api/notices", json=payload)
    assert resp.status_code == 422


def test_create_notice_invalid_notice_type_returns_422(client):
    payload = {**VALID_NOTICE, "notice_type": "UNKNOWN", "source_url": "https://fda.moph.go.th/x/003"}
    resp = client.post("/api/notices", json=payload)
    assert resp.status_code == 422


def test_create_notice_duplicate_source_url_returns_409(client):
    _create(client, VALID_NOTICE)
    resp = client.post("/api/notices", json=VALID_NOTICE)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_create_notice_source_url_stored_as_string(client):
    body = _create(client, VALID_NOTICE)
    assert isinstance(body["source_url"], str)
    assert body["source_url"].startswith("https://")


# ---------------------------------------------------------------------------
# GET /api/notices
# ---------------------------------------------------------------------------


def test_list_notices_empty(client):
    resp = client.get("/api/notices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_notices_returns_created(client):
    _create(client, VALID_NOTICE)
    _create(client, MINIMAL_NOTICE)
    resp = client.get("/api/notices")
    body = resp.json()
    assert body["total"] == 2


def test_list_notices_filter_by_notice_type_recall(client):
    _create(client, VALID_NOTICE)   # RECALL
    _create(client, MINIMAL_NOTICE)  # WARNING
    resp = client.get("/api/notices?notice_type=RECALL")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["notice_type"] == "RECALL"


def test_list_notices_filter_by_notice_type_warning(client):
    _create(client, VALID_NOTICE)
    _create(client, MINIMAL_NOTICE)
    resp = client.get("/api/notices?notice_type=WARNING")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["notice_type"] == "WARNING"


def test_list_notices_pagination(client):
    for i in range(5):
        payload = {
            **VALID_NOTICE,
            "source_url": f"https://fda.moph.go.th/recall/{i:03d}",
        }
        _create(client, payload)
    resp = client.get("/api/notices?skip=0&limit=3")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 3


# ---------------------------------------------------------------------------
# GET /api/notices/{id}
# ---------------------------------------------------------------------------


def test_get_notice_found(client):
    created = _create(client, VALID_NOTICE)
    resp = client.get(f"/api/notices/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_notice_not_found(client):
    resp = client.get("/api/notices/aaaaaaaaaaaaaaaaaaaaaaaa")
    assert resp.status_code == 404


def test_get_notice_invalid_id(client):
    resp = client.get("/api/notices/bad-id")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/notices/{id}
# ---------------------------------------------------------------------------


def test_update_notice_adds_lot_information(client):
    """
    A notice imported without lot data can be updated when the official
    announcement is later corrected to include lot numbers.
    """
    created = _create(client, MINIMAL_NOTICE)
    assert created["data_completeness"]["has_lot_information"] is False

    resp = client.put(
        f"/api/notices/{created['id']}",
        json={"affected_lots": ["L99001"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["affected_lots"] == ["L99001"]
    assert body["data_completeness"]["has_lot_information"] is True


def test_update_notice_completeness_recomputed(client):
    """data_completeness must reflect the updated fields, not the original."""
    created = _create(client, MINIMAL_NOTICE)
    resp = client.put(
        f"/api/notices/{created['id']}",
        json={"registration_no": "1A-00/01", "manufacturer": "บริษัทยา จำกัด"},
    )
    body = resp.json()
    assert body["data_completeness"]["has_registration_no"] is True
    assert body["data_completeness"]["has_manufacturer"] is True


def test_update_notice_not_found(client):
    resp = client.put(
        "/api/notices/aaaaaaaaaaaaaaaaaaaaaaaa",
        json={"reason": "updated"},
    )
    assert resp.status_code == 404


def test_update_notice_blank_title_returns_422(client):
    created = _create(client, VALID_NOTICE)
    resp = client.put(f"/api/notices/{created['id']}", json={"title": "  "})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/notices/{id}
# ---------------------------------------------------------------------------


def test_delete_notice_returns_204(client):
    created = _create(client, VALID_NOTICE)
    resp = client.delete(f"/api/notices/{created['id']}")
    assert resp.status_code == 204


def test_delete_notice_not_found(client):
    resp = client.delete("/api/notices/aaaaaaaaaaaaaaaaaaaaaaaa")
    assert resp.status_code == 404


def test_delete_notice_removes_dependent_matches(client, fake_db):
    """
    Deleting a notice must remove any match records that reference it so the
    matches collection does not contain dangling notice_id references.
    """
    created = _create(client, VALID_NOTICE)
    notice_oid = ObjectId(created["id"])

    # Manually insert a dependent match
    fake_db["matches"].insert_one(
        {
            "inventory_id": ObjectId(),
            "notice_id": notice_oid,
            "match_status": "EXACT_MATCH",
            "match_reason": "test",
            "matched_fields": ["registration_no"],
            "checked_at": None,
            "matching_version": "1.0",
        }
    )

    assert fake_db["matches"].count_documents({"notice_id": notice_oid}) == 1

    resp = client.delete(f"/api/notices/{created['id']}")
    assert resp.status_code == 204

    assert fake_db["matches"].count_documents({"notice_id": notice_oid}) == 0
