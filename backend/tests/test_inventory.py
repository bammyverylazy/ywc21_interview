"""
Tests for /api/inventory endpoints.

Coverage:
  POST   /api/inventory          create — valid, invalid product_id, negative qty
  GET    /api/inventory          list — empty, with items, filter by product_id
  GET    /api/inventory/{id}     get — found, not found, invalid id
  PUT    /api/inventory/{id}     update — partial, not found
  DELETE /api/inventory/{id}     delete — success, not found

The fake_db fixture from conftest.py is used so no real MongoDB is needed.
"""

from bson import ObjectId
from datetime import datetime, timezone


def _create_product(client) -> dict:
    resp = client.post("/api/products", json={"brand_name": "ยาทดสอบ"})
    assert resp.status_code == 201
    return resp.json()


def _create_item(client, product_id: str, **kwargs) -> dict:
    payload = {
        "product_id": product_id,
        "quantity": 10,
        **kwargs,
    }
    resp = client.post("/api/inventory", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/inventory
# ---------------------------------------------------------------------------


def test_create_inventory_item_returns_201(client):
    product = _create_product(client)
    item = _create_item(client, product["id"], lot_number="L25001", quantity=30)
    assert "id" in item
    assert item["product_id"] == product["id"]
    assert item["lot_number"] == "L25001"
    assert item["quantity"] == 30
    assert item["product"]["brand_name"] == "ยาทดสอบ"


def test_create_inventory_item_without_lot_number(client):
    product = _create_product(client)
    item = _create_item(client, product["id"])
    assert item["lot_number"] is None


def test_create_inventory_item_with_expiry_date(client):
    product = _create_product(client)
    item = _create_item(client, product["id"], expiry_date="2028-06-30")
    assert item["expiry_date"] == "2028-06-30"


def test_create_inventory_item_persists_utc_datetime_and_reads_same_date(client, fake_db):
    product = _create_product(client)
    item = _create_item(client, product["id"], expiry_date="2028-12-31")
    stored = fake_db["inventory_items"].find_one({"_id": ObjectId(item["id"])})
    assert stored["expiry_date"] == datetime(2028, 12, 31, tzinfo=timezone.utc)
    assert client.get(f"/api/inventory/{item['id']}").json()["expiry_date"] == "2028-12-31"


def test_create_inventory_item_with_null_expiry_date(client, fake_db):
    product = _create_product(client)
    item = _create_item(client, product["id"], expiry_date=None)
    stored = fake_db["inventory_items"].find_one({"_id": ObjectId(item["id"])})
    assert stored["expiry_date"] is None
    assert item["expiry_date"] is None


def test_invalid_expiry_date_returns_422(client):
    product = _create_product(client)
    response = client.post("/api/inventory", json={"product_id": product["id"], "quantity": 1, "expiry_date": "2028-02-30"})
    assert response.status_code == 422


def test_create_inventory_item_nonexistent_product_returns_422(client):
    fake_id = "a" * 24
    resp = client.post("/api/inventory", json={"product_id": fake_id, "quantity": 5})
    assert resp.status_code == 422


def test_create_inventory_item_invalid_product_id_returns_422(client):
    resp = client.post("/api/inventory", json={"product_id": "not-an-id", "quantity": 5})
    assert resp.status_code == 422


def test_create_inventory_item_negative_quantity_returns_422(client):
    product = _create_product(client)
    resp = client.post(
        "/api/inventory",
        json={"product_id": product["id"], "quantity": -1},
    )
    assert resp.status_code == 422


def test_create_inventory_item_zero_quantity_is_allowed(client):
    product = _create_product(client)
    item = _create_item(client, product["id"], quantity=0)
    assert item["quantity"] == 0


def test_create_inventory_item_strips_lot_number_whitespace(client):
    product = _create_product(client)
    item = _create_item(client, product["id"], lot_number="  L25001  ")
    assert item["lot_number"] == "L25001"


# ---------------------------------------------------------------------------
# GET /api/inventory
# ---------------------------------------------------------------------------


def test_list_inventory_empty(client):
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_inventory_returns_created_items(client):
    product = _create_product(client)
    _create_item(client, product["id"], lot_number="L001")
    _create_item(client, product["id"], lot_number="L002")
    resp = client.get("/api/inventory")
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_inventory_filter_by_product_id(client):
    p1 = _create_product(client)
    # Create a second product
    p2_resp = client.post("/api/products", json={"brand_name": "ยาชนิดสอง"})
    p2 = p2_resp.json()

    _create_item(client, p1["id"], lot_number="A001")
    _create_item(client, p2["id"], lot_number="B001")

    resp = client.get(f"/api/inventory?product_id={p1['id']}")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["product_id"] == p1["id"]


def test_list_inventory_pagination(client):
    product = _create_product(client)
    for i in range(5):
        _create_item(client, product["id"], lot_number=f"L{i:03d}")
    resp = client.get("/api/inventory?skip=0&limit=3")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 3


# ---------------------------------------------------------------------------
# GET /api/inventory/{id}
# ---------------------------------------------------------------------------


def test_get_inventory_item_found(client):
    product = _create_product(client)
    created = _create_item(client, product["id"])
    resp = client.get(f"/api/inventory/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_inventory_item_not_found(client):
    resp = client.get("/api/inventory/aaaaaaaaaaaaaaaaaaaaaaaa")
    assert resp.status_code == 404


def test_get_inventory_item_invalid_id(client):
    resp = client.get("/api/inventory/bad-id")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/inventory/{id}
# ---------------------------------------------------------------------------


def test_update_inventory_item_quantity(client):
    product = _create_product(client)
    created = _create_item(client, product["id"], quantity=10)
    resp = client.put(f"/api/inventory/{created['id']}", json={"quantity": 25})
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 25


def test_update_inventory_item_lot_number(client):
    product = _create_product(client)
    created = _create_item(client, product["id"], lot_number="OLD")
    resp = client.put(f"/api/inventory/{created['id']}", json={"lot_number": "NEW"})
    assert resp.status_code == 200
    assert resp.json()["lot_number"] == "NEW"


def test_update_inventory_item_expiry_date_persists_utc_and_reads_same_date(client, fake_db):
    product = _create_product(client)
    created = _create_item(client, product["id"])
    response = client.put(f"/api/inventory/{created['id']}", json={"expiry_date": "2028-12-31"})
    assert response.status_code == 200
    assert response.json()["expiry_date"] == "2028-12-31"
    stored = fake_db["inventory_items"].find_one({"_id": ObjectId(created["id"])})
    assert stored["expiry_date"] == datetime(2028, 12, 31, tzinfo=timezone.utc)


def test_existing_mongo_datetime_is_read_as_calendar_date(client, fake_db):
    product = _create_product(client)
    inserted = fake_db["inventory_items"].insert_one({
        "product_id": ObjectId(product["id"]), "lot_number": "LEGACY", "quantity": 1,
        "expiry_date": datetime(2028, 12, 31, 23, 0), "is_demo": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    })
    detail = client.get(f"/api/inventory/{inserted.inserted_id}")
    assert detail.status_code == 200
    assert detail.json()["expiry_date"] == "2028-12-31"


def test_update_inventory_item_not_found(client):
    resp = client.put(
        "/api/inventory/aaaaaaaaaaaaaaaaaaaaaaaa",
        json={"quantity": 5},
    )
    assert resp.status_code == 404


def test_update_inventory_negative_quantity_rejected(client):
    product = _create_product(client)
    created = _create_item(client, product["id"])
    resp = client.put(f"/api/inventory/{created['id']}", json={"quantity": -5})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/inventory/{id}
# ---------------------------------------------------------------------------


def test_delete_inventory_item_returns_204(client):
    product = _create_product(client)
    created = _create_item(client, product["id"])
    resp = client.delete(f"/api/inventory/{created['id']}")
    assert resp.status_code == 204


def test_delete_inventory_item_not_found(client):
    resp = client.delete("/api/inventory/aaaaaaaaaaaaaaaaaaaaaaaa")
    assert resp.status_code == 404


def test_deleted_item_no_longer_returned(client):
    product = _create_product(client)
    created = _create_item(client, product["id"])
    client.delete(f"/api/inventory/{created['id']}")
    resp = client.get(f"/api/inventory/{created['id']}")
    assert resp.status_code == 404
