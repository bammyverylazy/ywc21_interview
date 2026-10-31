"""
Product service — all database operations for the products collection.

Keeping database logic here (rather than inside route handlers) means the
matching engine and other services can call these functions directly, and
tests can verify business rules without HTTP overhead.

Design decisions:
- Returns raw dicts from MongoDB; the router is responsible for validating
  the response shape with ProductOut.
- Raises HTTPException for "not found" so the router stays thin.
- Uses doc_to_dict() to normalise _id → id before returning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.object_id import doc_to_dict, parse_object_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_product(db: Database, data: ProductCreate) -> dict:
    """Insert a new product and return the created document."""
    now = _now()
    doc = {
        "brand_name": data.brand_name,
        "generic_name": data.generic_name,
        "registration_no": data.registration_no,
        "manufacturer": data.manufacturer,
        "strength": data.strength,
        "dosage_form": data.dosage_form,
        "data_origin": data.data_origin,
        "created_at": now,
        "updated_at": now,
    }
    result = db["products"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc_to_dict(doc)


def list_products(
    db: Database,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """
    Return a page of products and the total count matching the filter.

    'search' is a case-insensitive substring match against brand_name,
    generic_name, and registration_no — the three fields a pharmacy staff
    member is most likely to type into a search box.
    """
    query: dict = {}
    if search:
        pattern = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"brand_name": pattern},
            {"generic_name": pattern},
            {"registration_no": pattern},
        ]

    total = db["products"].count_documents(query)
    cursor = (
        db["products"]
        .find(query)
        .sort("brand_name", 1)
        .skip(skip)
        .limit(limit)
    )
    items = [doc_to_dict(doc) for doc in cursor]
    return items, total


def get_product(db: Database, product_id: str) -> dict:
    """Return one product by id, or raise 404."""
    oid = parse_object_id(product_id)
    doc = db["products"].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )
    return doc_to_dict(doc)


def update_product(db: Database, product_id: str, data: ProductUpdate) -> dict:
    """Apply a partial update and return the updated document."""
    oid = parse_object_id(product_id)
    changes = data.non_none_fields()
    if not changes:
        # Nothing to change — just return the current record
        return get_product(db, product_id)

    changes["updated_at"] = _now()
    result = db["products"].find_one_and_update(
        {"_id": oid},
        {"$set": changes},
        return_document=True,  # return the updated doc
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )
    return doc_to_dict(result)


def delete_product(db: Database, product_id: str) -> None:
    """
    Delete a product if it has no inventory items.

    Spec §7.3: "Delete product if safe to do so."
    Deleting a product that has inventory records would orphan those records
    and break the inventory display. We refuse the delete and tell the caller
    how many records would be affected.
    """
    oid = parse_object_id(product_id)

    # Check for dependent inventory items first
    inventory_count = db["inventory_items"].count_documents({"product_id": oid})
    if inventory_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete product '{product_id}': it has {inventory_count} "
                f"inventory item(s). Delete or reassign those first."
            ),
        )

    result = db["products"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )
