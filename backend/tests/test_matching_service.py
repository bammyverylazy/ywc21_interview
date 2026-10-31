from bson import ObjectId
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import create_app
from app.services import matching_service
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

    run_response = client.post("/api/matches/run")
    assert run_response.status_code == 200
    assert run_response.json()["exact_matches"] == 1

    matches_response = client.get("/api/matches", params={"skip": 0, "limit": 200})
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

    rerun_response = client.post("/api/matches/run", json={"scope": "ALL"})
    assert rerun_response.status_code == 200
    assert rerun_response.json() == run_response.json()
    assert fake_db["matches"].count_documents({}) == 1
    assert fake_db["matches"].find_one({})["_id"] == ObjectId(match["id"])
    assert len(client.get(f"/api/matches/{match['id']}/actions").json()) == 1


def test_match_run_rejects_invalid_scope_and_missing_single_item_id(client):
    invalid_scope = client.post("/api/matches/run", json={"scope": "EVERYTHING"})
    assert invalid_scope.status_code == 422
    assert "scope" in str(invalid_scope.json()["detail"])

    missing_inventory_id = client.post(
        "/api/matches/run",
        json={"scope": "SINGLE_INVENTORY_ITEM"},
    )
    assert missing_inventory_id.status_code == 422
    assert "inventory_id is required" in str(missing_inventory_id.json()["detail"])

    invalid_inventory_id = client.post(
        "/api/matches/run",
        json={"scope": "SINGLE_INVENTORY_ITEM", "inventory_id": "not-an-object-id"},
    )
    assert invalid_inventory_id.status_code == 422
    assert "not a valid id" in invalid_inventory_id.json()["detail"]


def test_single_inventory_run_distinguishes_empty_results_from_missing_item(client, fake_db):
    inventory_id = ObjectId()
    fake_db["inventory_items"].insert_one({"_id": inventory_id})

    empty_results = client.post(
        "/api/matches/run",
        json={"scope": "SINGLE_INVENTORY_ITEM", "inventory_id": str(inventory_id)},
    )
    assert empty_results.status_code == 200
    assert empty_results.json()["total_checked"] == 0

    missing_item = client.post(
        "/api/matches/run",
        json={"scope": "SINGLE_INVENTORY_ITEM", "inventory_id": str(ObjectId())},
    )
    assert missing_item.status_code == 404


def test_match_run_openapi_documents_optional_request_body(client):
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/matches/run"]["post"]
    request_body = operation["requestBody"]

    assert request_body.get("required", False) is False
    schema = request_body["content"]["application/json"]["schema"]
    schema_ref = schema["anyOf"][0]["$ref"]
    assert schema_ref.endswith("/MatchRunRequest")


def test_match_run_returns_server_error_when_matching_fails(fake_db, monkeypatch):
    def fail_matching(*args, **kwargs):
        raise RuntimeError("simulated matching failure")

    monkeypatch.setattr(matching_service, "run_matching", fail_matching)
    app = create_app(manage_database=False)
    app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app, raise_server_exceptions=False) as error_client:
        response = error_client.post("/api/matches/run")

    assert response.status_code == 500
