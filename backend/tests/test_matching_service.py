from bson import ObjectId
from datetime import date, datetime, timezone

from app.services.matching_service import evaluate_pair, run_matching


def test_exact_match_requires_strong_identity_and_affected_lot():
    result = evaluate_pair(
        {
            "lot_number": " LOT-7 ",
            "product": {
                "brand_name": "Medicine A",
                "generic_name": "Substance A",
                "registration_no": "REG-7",
                "manufacturer": "Maker A",
            },
        },
        {
            "product_name": "medicine a",
            "generic_name": "substance a",
            "registration_no": "reg-7",
            "manufacturer": "maker a",
            "affected_lots": [{"lot_number": "lot-7"}],
        },
    )

    assert result["match_status"] == "EXACT_MATCH"
    assert "lot_number" in result["matched_fields"]


def test_missing_identity_is_potential_not_no_match():
    result = evaluate_pair(
        {"lot_number": "LOT-1", "product": None},
        {"product_name": "Medicine A", "affected_lots": ["LOT-1"]},
    )

    assert result["match_status"] == "POTENTIAL_MATCH"
    assert "product_identity" in result["missing_fields"]


def test_conflicting_registration_is_never_an_exact_match():
    result = evaluate_pair(
        {
            "lot_number": "LOT-1",
            "product": {
                "brand_name": "Medicine A",
                "generic_name": "Substance A",
                "registration_no": "REG-A",
                "manufacturer": "Maker A",
            },
        },
        {
            "product_name": "Medicine A",
            "generic_name": "Substance A",
            "registration_no": "REG-B",
            "manufacturer": "Maker A",
            "affected_lots": ["LOT-1"],
        },
    )

    assert result["match_status"] == "POTENTIAL_MATCH"


def test_run_matching_is_idempotent_for_inventory_notice_pairs(fake_db):
    product_id = ObjectId()
    inventory_id = ObjectId()
    notice_id = ObjectId()
    fake_db["products"].insert_one({
        "_id": product_id,
        "brand_name": "Medicine A",
        "generic_name": "Substance A",
        "registration_no": "REG-A",
        "manufacturer": "Maker A",
    })
    fake_db["inventory_items"].insert_one({
        "_id": inventory_id,
        "product_id": product_id,
        "lot_number": "LOT-A",
    })
    fake_db["safety_notices"].insert_one({
        "_id": notice_id,
        "product_name": "Medicine A",
        "generic_name": "Substance A",
        "registration_no": "REG-A",
        "manufacturer": "Maker A",
        "affected_lots": ["LOT-A"],
    })

    assert run_matching(fake_db)["exact_matches"] == 1
    assert run_matching(fake_db)["exact_matches"] == 1
    assert fake_db["matches"].count_documents({}) == 1


def test_match_action_activity_and_dashboard_api_flow(client, fake_db):
    now = datetime.now(timezone.utc)
    product_id = ObjectId()
    fake_db["products"].insert_one({
        "_id": product_id,
        "brand_name": "Medicine A",
        "generic_name": "Substance A",
        "registration_no": "REG-A",
        "manufacturer": "Maker A",
        "created_at": now,
        "updated_at": now,
    })
    fake_db["inventory_items"].insert_one({
        "product_id": product_id,
        "lot_number": "LOT-A",
        "quantity": 4,
        "expiry_date": date.today(),
        "is_demo": False,
        "created_at": now,
        "updated_at": now,
    })
    fake_db["safety_notices"].insert_one({
        "title": "Verified source notice",
        "notice_type": "RECALL",
        "product_name": "Medicine A",
        "generic_name": "Substance A",
        "registration_no": "REG-A",
        "manufacturer": "Maker A",
        "affected_lots": ["LOT-A"],
        "published_at": date.today(),
        "source_name": "Thai FDA",
        "source_url": "https://safetyalert.fda.moph.go.th/notices/123",
        "imported_at": now,
        "data_completeness": {
            "has_registration_no": True,
            "has_lot_information": True,
            "has_manufacturer": True,
        },
        "record_origin": "verified_import",
        "verification_status": "verified",
    })

    run_response = client.post("/api/matches/run", json={"scope": "ALL"})
    assert run_response.status_code == 200
    assert run_response.json()["exact_matches"] == 1

    matches_response = client.get("/api/matches")
    assert matches_response.status_code == 200
    match = matches_response.json()["items"][0]
    assert match["match_status"] == "EXACT_MATCH"
    assert match["inventory"]["product"]["id"] == str(product_id)

    action_response = client.post(
        f"/api/matches/{match['id']}/actions",
        json={"status": "REVIEWED", "action_note": "Checked original notice"},
    )
    assert action_response.status_code == 201
    activity_response = client.get("/api/activity", params={"activity_type": "REVIEWED"})
    assert activity_response.status_code == 200
    assert activity_response.json()["items"][0]["match_id"] == match["id"]
    assert client.get("/api/dashboard/summary").json()["pending_review"] == 0
