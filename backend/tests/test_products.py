"""
Tests for /api/products endpoints.

Coverage:
  POST   /api/products           create — valid, missing brand_name, blank brand_name
  GET    /api/products           list — empty, with item, pagination params
  GET    /api/products/{id}      get — found, not found, invalid id
  PUT    /api/products/{id}      update — partial update, not found
  DELETE /api/products/{id}      delete — success, not found, blocked by inventory
"""


def _create(client, **kwargs) -> dict:
    """Helper: POST /api/products and return parsed body."""
    payload = {"brand_name": "ยาตัวอย่าง", **kwargs}
    response = client.post("/api/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# POST /api/products
# ---------------------------------------------------------------------------


def test_create_product_returns_201_with_id(client):
    body = _create(client, generic_name="Amoxicillin", registration_no="1A-12/34")
    assert "id" in body
    assert body["brand_name"] == "ยาตัวอย่าง"
    assert body["generic_name"] == "Amoxicillin"
    assert body["registration_no"] == "1A-12/34"
    assert "created_at" in body
    assert "updated_at" in body


def test_create_product_without_optional_fields(client):
    body = _create(client)
    assert body["generic_name"] is None
    assert body["registration_no"] is None
    assert body["manufacturer"] is None


def test_create_product_missing_brand_name_returns_422(client):
    response = client.post("/api/products", json={"generic_name": "Amox"})
    assert response.status_code == 422


def test_create_product_blank_brand_name_returns_422(client):
    response = client.post("/api/products", json={"brand_name": "   "})
    assert response.status_code == 422


def test_create_product_strips_whitespace(client):
    body = _create(client, brand_name="  ยาแก้ปวด  ", registration_no="  ABC123  ")
    assert body["brand_name"] == "ยาแก้ปวด"
    assert body["registration_no"] == "ABC123"


# ---------------------------------------------------------------------------
# GET /api/products
# ---------------------------------------------------------------------------


def test_list_products_empty(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_products_returns_created_item(client):
    _create(client)
    response = client.get("/api/products")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_list_products_pagination_fields(client):
    _create(client)
    response = client.get("/api/products?skip=0&limit=10")
    body = response.json()
    assert body["skip"] == 0
    assert body["limit"] == 10


# ---------------------------------------------------------------------------
# GET /api/products/{id}
# ---------------------------------------------------------------------------


def test_get_product_found(client):
    created = _create(client)
    response = client.get(f"/api/products/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_product_not_found(client):
    response = client.get("/api/products/aaaaaaaaaaaaaaaaaaaaaaaa")
    assert response.status_code == 404


def test_get_product_invalid_id(client):
    response = client.get("/api/products/not-a-valid-id")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/products/{id}
# ---------------------------------------------------------------------------


def test_update_product_partial(client):
    created = _create(client, generic_name="Old Name")
    response = client.put(
        f"/api/products/{created['id']}",
        json={"generic_name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["generic_name"] == "New Name"
    assert response.json()["brand_name"] == created["brand_name"]


def test_update_product_not_found(client):
    response = client.put(
        "/api/products/aaaaaaaaaaaaaaaaaaaaaaaa",
        json={"generic_name": "x"},
    )
    assert response.status_code == 404


def test_update_product_blank_brand_name_returns_422(client):
    created = _create(client)
    response = client.put(
        f"/api/products/{created['id']}",
        json={"brand_name": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/products/{id}
# ---------------------------------------------------------------------------


def test_delete_product_returns_204(client):
    created = _create(client)
    response = client.delete(f"/api/products/{created['id']}")
    assert response.status_code == 204


def test_delete_product_not_found(client):
    response = client.delete("/api/products/aaaaaaaaaaaaaaaaaaaaaaaa")
    assert response.status_code == 404


def test_delete_product_blocked_by_inventory(client, fake_db):
    """
    Deleting a product that has inventory items must return 409 Conflict.
    We pre-populate the inventory collection in fake_db so the service
    finds the dependent records.
    """
    from bson import ObjectId

    created = _create(client)
    product_oid = ObjectId(created["id"])

    # Manually insert a dependent inventory item
    fake_db["inventory_items"].insert_one(
        {
            "product_id": product_oid,
            "lot_number": "L001",
            "quantity": 10,
            "expiry_date": None,
            "created_at": None,
            "updated_at": None,
        }
    )

    response = client.delete(f"/api/products/{created['id']}")
    assert response.status_code == 409
    assert "inventory" in response.json()["detail"].lower()
