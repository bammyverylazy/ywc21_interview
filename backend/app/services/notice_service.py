"""
Notice service — all database operations for the safety_notices collection.

Design decisions:

Duplicate detection (spec §6.5):
  source_url is the stable identity for a notice. Before inserting, we check
  whether a notice with the same source_url already exists. If it does, we
  return a 409 Conflict rather than silently creating a duplicate. The caller
  can use PUT to update the existing record if the source was re-imported.

data_completeness:
  Computed from the payload at insert/update time and stored in MongoDB so
  the matching engine can query "notices with registration_no" efficiently
  without loading every document.

Normalisation:
  registration_no and lot numbers are stored as-is (original value preserved
  per spec §8.2). Normalised forms are computed at match time in the matching
  engine, not here.

source_url storage:
  Pydantic validates source_url as AnyHttpUrl (a Pydantic URL object). We
  convert it to a plain string before storing in MongoDB.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any, List, Optional, Union

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.provenance import build_field_provenance
from app.schemas.notice import AffectedLot, NoticeCreate, NoticeUpdate
from app.utils.object_id import doc_to_dict, parse_object_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date_to_mongo_datetime(value: date | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    return None


def _lot_to_document(lot: AffectedLot | dict[str, Any] | str) -> dict[str, Any] | str:
    if isinstance(lot, AffectedLot):
        document = lot.model_dump(mode="python")
    elif isinstance(lot, dict):
        document = dict(lot)
    else:
        return lot
    for field in ("manufacturing_date", "expiry_date"):
        if field in document:
            document[field] = _date_to_mongo_datetime(document[field])
    return document


def _compute_completeness(
    registration_no: Optional[str],
    affected_lots: List[Union[str, AffectedLot, dict[str, Any]]],
    manufacturer: Optional[str],
) -> dict:
    has_lots = any(
        (lot.get("lot_number") if isinstance(lot, dict) else lot)
        for lot in affected_lots
    )
    return {
        "has_registration_no": bool(registration_no),
        "has_lot_information": has_lots,
        "has_manufacturer": bool(manufacturer),
    }


def create_notice(db: Database, data: NoticeCreate) -> dict:
    """
    Insert a new safety notice.

    Rejects duplicate source_url with 409 so the same official page cannot
    be imported twice by accident.
    """
    source_url_str = str(data.source_url)

    existing = db["safety_notices"].find_one({"source_url": source_url_str}, {"_id": 1})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A notice from this source URL already exists "
                f"(id: {str(existing['_id'])}). "
                f"Use PUT /api/notices/{{id}} to update it."
            ),
        )

    now = _now()
    doc = {
        "title": data.title,
        "notice_type": data.notice_type.value,
        "product_name": data.product_name,
        "product_name_th": data.product_name_th,
        "product_name_en": data.product_name_en,
        "generic_name": data.generic_name,
        "registration_no": data.registration_no,
        "manufacturer": data.manufacturer,
        "dosage_form": data.dosage_form,
        "product_strength": data.product_strength,
        "affected_lots": data.affected_lots,
        "attachments": data.attachments,
        "reason": data.reason,
        "recall_action": data.recall_action,
        "impact": data.impact,
        "published_at": _date_to_mongo_datetime(data.published_at),
        "source_name": data.source_name,
        "source_url": source_url_str,
        "source_id": data.source_id,
        "source_detail_id": data.source_detail_id,
        "source_detail_status": data.source_detail_status,
        "source_attachments_status": data.source_attachments_status,
        "updated_at_source": data.updated_at_source,
        "raw_source_data": data.raw_source_data,
        "record_origin": "manual",
        "verification_status": "manual_review",
        "field_provenance": build_field_provenance(
            {
                "title": data.title,
                "product_name": data.product_name,
                "generic_name": data.generic_name,
                "registration_no": data.registration_no,
                "manufacturer": data.manufacturer,
                "dosage_form": data.dosage_form,
                "product_strength": data.product_strength,
                "notice_type": data.notice_type.value,
                "reason": data.reason,
                "recall_action": data.recall_action,
                "impact": data.impact,
                "affected_lots": data.affected_lots,
                "attachments": data.attachments,
                "published_at": data.published_at,
            },
            origin="manual_unverified",
            extraction_method="manual_api_entry",
            source_reference=source_url_str,
        ),
        "imported_at": now,
        "data_completeness": _compute_completeness(
            data.registration_no, data.affected_lots, data.manufacturer
        ),
    }
    doc["affected_lots"] = [
        _lot_to_document(lot)
        for lot in data.affected_lots
    ]
    doc["attachments"] = [
        {
            **attachment.model_dump(mode="python"),
            "file_url": str(attachment.file_url),
        }
        for attachment in data.attachments
    ]
    result = db["safety_notices"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc_to_dict(doc)


def list_notices(
    db: Database,
    search: Optional[str] = None,
    notice_type: Optional[str] = None,
    registration_no: Optional[str] = None,
    lot_number: Optional[str] = None,
    published_from: Optional[date] = None,
    published_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """
    Return a page of notices with optional filters (spec §7.5).

    search         — case-insensitive substring match on product_name, title
    notice_type    — exact match on notice_type enum value
    registration_no — exact match on registration_no (case-insensitive)
    """
    query: dict = {}

    if notice_type:
        query["notice_type"] = notice_type.upper()

    if registration_no:
        query["registration_no"] = {
            "$regex": f"^{re.escape(registration_no.strip())}$",
            "$options": "i",
        }

    if search and not registration_no:
        pattern = {"$regex": re.escape(search.strip()), "$options": "i"}
        query["$or"] = [
            {"product_name": pattern},
            {"product_name_th": pattern},
            {"product_name_en": pattern},
            {"title": pattern},
            {"generic_name": pattern},
        ]
    if lot_number:
        query["$or"] = [
            {"affected_lots": {"$regex": f"^{re.escape(lot_number.strip())}$", "$options": "i"}},
            {"affected_lots.lot_number": {"$regex": f"^{re.escape(lot_number.strip())}$", "$options": "i"}},
        ]
    if published_from or published_to:
        date_query: dict = {}
        if published_from:
            date_query["$gte"] = published_from
        if published_to:
            date_query["$lte"] = published_to
        query["published_at"] = date_query

    total = db["safety_notices"].count_documents(query)
    cursor = (
        db["safety_notices"]
        .find(query)
        .sort("published_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [doc_to_dict(doc) for doc in cursor], total


def get_notice(db: Database, notice_id: str) -> dict:
    """Return one notice by id, or raise 404."""
    oid = parse_object_id(notice_id)
    doc = db["safety_notices"].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice '{notice_id}' not found.",
        )
    return doc_to_dict(doc)


def update_notice(db: Database, notice_id: str, data: NoticeUpdate) -> dict:
    """
    Apply a partial update. Re-computes data_completeness after the update
    so the stored flags stay consistent.
    """
    oid = parse_object_id(notice_id)
    changes = data.non_none_fields()
    if not changes:
        return get_notice(db, notice_id)

    # Fetch current doc to merge for completeness recomputation
    current = db["safety_notices"].find_one({"_id": oid})
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice '{notice_id}' not found.",
        )

    merged_reg = changes.get("registration_no", current.get("registration_no"))
    merged_lots = changes.get("affected_lots", current.get("affected_lots", []))
    merged_mfr = changes.get("manufacturer", current.get("manufacturer"))

    changes["data_completeness"] = _compute_completeness(merged_reg, merged_lots, merged_mfr)
    changes["updated_at"] = _now()
    if "published_at" in changes:
        changes["published_at"] = _date_to_mongo_datetime(changes["published_at"])
    if "affected_lots" in changes:
        changes["affected_lots"] = [
            _lot_to_document(lot)
            for lot in merged_lots
        ]
    if "attachments" in changes:
        changes["attachments"] = [
            {
                **attachment.model_dump(mode="python"),
                "file_url": str(attachment.file_url),
            }
            if hasattr(attachment, "model_dump")
            else attachment
            for attachment in changes["attachments"]
        ]

    # Serialise NoticeType enum values if present
    if "notice_type" in changes and hasattr(changes["notice_type"], "value"):
        changes["notice_type"] = changes["notice_type"].value

    provenance = dict(current.get("field_provenance", {}))
    for field in changes:
        if field in {
            "title", "product_name", "generic_name", "registration_no",
            "manufacturer", "dosage_form", "product_strength", "notice_type",
            "reason", "recall_action", "impact", "affected_lots",
            "attachments", "published_at",
        }:
            provenance.update(build_field_provenance(
                {field: changes[field]},
                origin="manual_unverified",
                extraction_method="manual_api_update",
                source_reference=current.get("source_url"),
            ))
    if provenance:
        changes["field_provenance"] = provenance

    result = db["safety_notices"].find_one_and_update(
        {"_id": oid},
        {"$set": changes},
        return_document=True,
    )
    return doc_to_dict(result)


def delete_notice(db: Database, notice_id: str) -> None:
    """
    Delete a safety notice. Also removes any matches referencing this notice
    so the matches collection doesn't have dangling references.
    """
    oid = parse_object_id(notice_id)

    result = db["safety_notices"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice '{notice_id}' not found.",
        )

    # Clean up dependent matches (best-effort; matching engine will not
    # return results for deleted notices anyway, but this keeps the DB tidy)
    db["matches"].delete_many({"notice_id": oid})
