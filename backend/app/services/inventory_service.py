"""
Inventory service — all database operations for the inventory_items collection.

Design decisions:
- product_id is stored as an ObjectId in MongoDB (proper reference).
- Responses embed a lightweight product summary so the UI can render a list
  row without a second request.
- expiry_date is stored as midnight UTC in MongoDB and exposed as YYYY-MM-DD.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.schemas.inventory import InventoryCreate, InventoryUpdate
from app.utils.object_id import doc_to_dict, parse_object_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date_to_mongo_datetime(value: date | datetime | None) -> datetime | None:
    """Store calendar dates at midnight UTC without shifting their date."""
    if isinstance(value, datetime):
        # Preserve the represented calendar date. MongoDB dates are UTC; a
        # timezone offset conversion here could move an expiry to another day.
        return value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    return None


def _date_from_mongo_datetime(value: date | datetime | None) -> date | None:
    """Expose the UTC calendar date from BSON datetime values."""
    if isinstance(value, datetime):
        # Preserve the datetime's represented calendar date. PyMongo commonly
        # returns naive UTC values; aware values must not shift the day here.
        return value.date()
    return value if isinstance(value, date) else None


def _normalize_inventory_dates(item: dict) -> dict:
    item["expiry_date"] = _date_from_mongo_datetime(item.get("expiry_date"))
    return item


def _enrich_with_product(db: Database, item: dict) -> dict:
    """
    Attach a 'product' summary dict to an inventory dict.

    product_id is already a str after doc_to_dict(); we re-parse it to look
    up the product. If the product has been deleted, 'product' is None.
    """
    pid_str = item.get("product_id")
    if not pid_str:
        item["product"] = None
        return item
    try:
        oid = ObjectId(pid_str)
    except Exception:
        item["product"] = None
        return item

    product_doc = db["products"].find_one(
        {"_id": oid},
        {"brand_name": 1, "generic_name": 1, "registration_no": 1, "manufacturer": 1},
    )
    if product_doc:
        item["product"] = doc_to_dict(product_doc)
    else:
        item["product"] = None
    return item


def create_inventory_item(db: Database, data: InventoryCreate) -> dict:
    """
    Insert a new inventory batch record.

    Validates that the referenced product exists (spec §6.4: product_id must
    reference an existing product).
    """
    product_oid = parse_object_id(data.product_id)
    if db["products"].find_one({"_id": product_oid}, {"_id": 1}) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Product '{data.product_id}' does not exist.",
        )

    now = _now()
    doc = {
        "product_id": product_oid,
        "lot_number": data.lot_number,
        "quantity": data.quantity,
        "expiry_date": _date_to_mongo_datetime(data.expiry_date),
        "is_demo": data.is_demo,
        "created_at": now,
        "updated_at": now,
    }
    result = db["inventory_items"].insert_one(doc)
    doc["_id"] = result.inserted_id
    item = _normalize_inventory_dates(doc_to_dict(doc))
    return _enrich_with_product(db, item)


def list_inventory_items(
    db: Database,
    search: Optional[str] = None,
    product_id: Optional[str] = None,
    lot_number: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """
    Return a page of inventory items with their product summaries.

    Supported filters (spec §7.4):
      search     — substring match across lot_number
      product_id — exact product reference
      lot_number — exact lot match (case-insensitive)
    """
    query: dict = {}

    if product_id:
        product_oid = parse_object_id(product_id)
        query["product_id"] = product_oid

    if lot_number:
        query["lot_number"] = {"$regex": f"^{re.escape(lot_number.strip())}$", "$options": "i"}

    if search and not lot_number:
        pattern = {"$regex": re.escape(search.strip()), "$options": "i"}
        product_docs = db["products"].find(
            {"$or": [
                {"brand_name": pattern},
                {"generic_name": pattern},
                {"registration_no": pattern},
            ]},
            {"_id": 1},
        )
        matching_product_ids = [product["_id"] for product in product_docs]
        search_or: list[dict] = [{"lot_number": pattern}]
        if matching_product_ids:
            search_or.append({"product_id": {"$in": matching_product_ids}})
        if product_id:
            query["$and"] = [{"$or": search_or}]
        else:
            query["$or"] = search_or

    total = db["inventory_items"].count_documents(query)
    cursor = (
        db["inventory_items"]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = [_enrich_with_product(db, _normalize_inventory_dates(doc_to_dict(doc))) for doc in cursor]
    return items, total


def get_inventory_item(db: Database, item_id: str) -> dict:
    """Return one inventory item by id, or raise 404."""
    oid = parse_object_id(item_id)
    doc = db["inventory_items"].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item '{item_id}' not found.",
        )
    item = _normalize_inventory_dates(doc_to_dict(doc))
    return _enrich_with_product(db, item)


def update_inventory_item(db: Database, item_id: str, data: InventoryUpdate) -> dict:
    """Apply a partial update and return the updated document."""
    oid = parse_object_id(item_id)
    changes = data.non_none_fields()
    if "expiry_date" in changes:
        changes["expiry_date"] = _date_to_mongo_datetime(changes["expiry_date"])
    if not changes:
        return get_inventory_item(db, item_id)

    changes["updated_at"] = _now()
    result = db["inventory_items"].find_one_and_update(
        {"_id": oid},
        {"$set": changes},
        return_document=True,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item '{item_id}' not found.",
        )
    item = _normalize_inventory_dates(doc_to_dict(result))
    return _enrich_with_product(db, item)


def delete_inventory_item(db: Database, item_id: str) -> None:
    """Delete an inventory record by id."""
    oid = parse_object_id(item_id)
    result = db["inventory_items"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item '{item_id}' not found.",
        )
