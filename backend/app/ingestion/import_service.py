from __future__ import annotations

import hashlib
import json

from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database

from app.provenance import build_field_provenance
from app.ingestion.normalizer import normalize_record
from app.ingestion.validator import validate_record
from app.services.notice_service import (
    _compute_completeness,
    _date_to_mongo_datetime,
    _lot_to_document,
)


_SOURCE_DETAIL_FIELDS = (
    "source_detail_id",
    "product_name_th",
    "product_name_en",
    "generic_name",
    "registration_no",
    "manufacturer",
    "dosage_form",
    "product_strength",
    "reason",
    "recall_action",
    "affected_lots",
    "attachments",
)


def _source_content_hash(content: dict[str, Any]) -> str:
    hashable_content = {
        key: value
        for key, value in content.items()
        if key not in {
            "raw_source_data",
            "data_completeness",
            "source_detail_status",
            "source_attachments_status",
            "source_content_hash",
            "now",
        }
    }
    return hashlib.sha256(
        json.dumps(
            hashable_content,
            ensure_ascii=False,
            sort_keys=True,
            default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value),
        ).encode("utf-8")
    ).hexdigest()


def _validated_document(record: dict[str, Any], now: datetime) -> dict[str, Any]:
    normalized = normalize_record(record)
    validated = validate_record(normalized)
    lots = [
        _lot_to_document(lot)
        for lot in validated.affected_lots
    ]
    attachments = [
        {
            **attachment.model_dump(mode="python"),
            "file_url": str(attachment.file_url),
        }
        for attachment in validated.attachments
    ]
    source_created_at = record.get("source_created_at")
    if isinstance(source_created_at, str):
        source_created_at = datetime.fromisoformat(source_created_at)
    content = {
        "source_id": validated.source_id,
        "source_name": validated.source_name or "Thai FDA",
        "source_url": str(validated.source_url),
        "title": validated.title,
        "product_name": validated.product_name,
        "product_name_th": validated.product_name_th,
        "product_name_en": validated.product_name_en,
        "generic_name": validated.generic_name,
        "registration_no": validated.registration_no,
        "manufacturer": validated.manufacturer,
        "dosage_form": validated.dosage_form,
        "product_strength": validated.product_strength,
        "notice_type": validated.notice_type.value,
        "recall_action": validated.recall_action,
        "reason": validated.reason,
        "impact": validated.impact,
        "affected_lots": lots,
        "attachments": attachments,
        "source_attachments_status": validated.source_attachments_status,
        "published_at": _date_to_mongo_datetime(validated.published_at),
        "updated_at_source": validated.updated_at_source,
        "source_created_at": source_created_at or validated.source_created_at,
        "source_detail_id": validated.source_detail_id,
        "source_detail_status": validated.source_detail_status,
        "raw_source_data": validated.raw_source_data or record,
        "record_origin": validated.record_origin,
        "verification_status": validated.verification_status,
        "field_provenance": record.get("field_provenance", {}),
        "data_completeness": _compute_completeness(
            validated.registration_no, lots, validated.manufacturer
        ),
    }
    source_hash = _source_content_hash(content)
    return {**content, "source_content_hash": source_hash, "now": now}


def upsert_synced_record(
    db: Database,
    record: dict[str, Any],
    *,
    sync_run_id: str,
    now: datetime | None = None,
) -> str:
    """Validate and incrementally upsert one source record; return its outcome."""
    timestamp = now or datetime.now(timezone.utc)
    document = _validated_document(record, timestamp)
    source_id = document.get("source_id")
    existing = None
    if source_id:
        existing = db["safety_notices"].find_one({
            "source_name": document["source_name"],
            "source_id": source_id,
        })
    if existing is None:
        existing = db["safety_notices"].find_one({"source_url": document["source_url"]})

    if existing is not None:
        detail_status = document.get("source_detail_status")
        attachments_status = document.get("source_attachments_status")
        preserve_all_detail = detail_status in {"not_requested", "failed"}
        preserve_incomplete_detail = detail_status == "partial"
        preserved_fields: set[str] = set()
        for field in _SOURCE_DETAIL_FIELDS:
            if field == "attachments" and attachments_status == "none":
                continue
            incoming = document.get(field)
            missing = incoming is None or incoming == "" or incoming == []
            if (
                field in existing
                and (preserve_all_detail or (preserve_incomplete_detail and missing))
            ):
                document[field] = existing[field]
                preserved_fields.add(field)

        previous_raw = existing.get("raw_source_data")
        current_raw = document.get("raw_source_data")
        if (
            preserve_all_detail
            and isinstance(previous_raw, dict)
            and isinstance(current_raw, dict)
        ):
            prior_detail = previous_raw.get("detail_response")
            prior_attachments = previous_raw.get("attachment_response")
            if prior_detail is not None or prior_attachments is not None:
                document["raw_source_data"] = {
                    "listing": current_raw,
                    "detail_response": prior_detail,
                    "attachment_response": prior_attachments,
                    "detail_response_sha256": previous_raw.get(
                        "detail_response_sha256"
                    ),
                }
        elif (
            attachments_status == "failed"
            and isinstance(previous_raw, dict)
            and isinstance(current_raw, dict)
            and previous_raw.get("attachment_response") is not None
        ):
            current_raw["attachment_response"] = previous_raw["attachment_response"]
        provenance = dict(existing.get("field_provenance", {}))
        provenance.update({
            key: value
            for key, value in document.get("field_provenance", {}).items()
            if key not in preserved_fields
        })
        document["field_provenance"] = provenance
        document["data_completeness"] = _compute_completeness(
            document.get("registration_no"),
            document.get("affected_lots", []),
            document.get("manufacturer"),
        )
        document["source_content_hash"] = _source_content_hash(document)

    document["last_checked_at"] = timestamp
    document["last_sync_run_id"] = sync_run_id
    document["last_synced_at"] = timestamp
    document.pop("now")

    if existing is None:
        document["imported_at"] = timestamp
        document["updated_at"] = timestamp
        document["source_changed_at"] = timestamp
        db["safety_notices"].insert_one(document)
        return "new"

    if existing.get("verification_status") == "verified":
        prior_sync_hash = existing.get(
            "latest_sync_source_hash",
            existing.get("source_content_hash"),
        )
        if prior_sync_hash == document["source_content_hash"]:
            db["safety_notices"].find_one_and_update(
                {"_id": existing["_id"]},
                {"$set": {
                    "last_checked_at": timestamp,
                    "last_sync_run_id": sync_run_id,
                    "last_synced_at": timestamp,
                }},
                return_document=True,
            )
            return "unchanged"

        db["safety_notice_revisions"].insert_one({
            "notice_id": existing["_id"],
            "source_name": document["source_name"],
            "source_id": source_id,
            "changed_at": timestamp,
            "sync_run_id": sync_run_id,
            "previous_hash": prior_sync_hash,
            "new_hash": document["source_content_hash"],
            "previous_source_data": existing.get(
                "latest_sync_source_data",
                existing.get("raw_source_data"),
            ),
            "new_source_data": document["raw_source_data"],
        })
        db["safety_notices"].find_one_and_update(
            {"_id": existing["_id"]},
            {"$set": {
                "last_checked_at": timestamp,
                "last_sync_run_id": sync_run_id,
                "last_synced_at": timestamp,
                "source_changed_at": timestamp,
                "latest_sync_source_hash": document["source_content_hash"],
                "latest_sync_source_data": document["raw_source_data"],
            }},
            return_document=True,
        )
        return "updated"

    if existing.get("source_content_hash") == document["source_content_hash"]:
        db["safety_notices"].find_one_and_update(
            {"_id": existing["_id"]},
            {"$set": {
                "last_checked_at": timestamp,
                "last_sync_run_id": sync_run_id,
                "last_synced_at": timestamp,
            }},
            return_document=True,
        )
        return "unchanged"

    db["safety_notice_revisions"].insert_one({
        "notice_id": existing["_id"],
        "source_name": document["source_name"],
        "source_id": source_id,
        "changed_at": timestamp,
        "sync_run_id": sync_run_id,
        "previous_hash": existing.get("source_content_hash"),
        "new_hash": document["source_content_hash"],
        "previous_source_data": existing.get("raw_source_data"),
        "new_source_data": document["raw_source_data"],
    })
    document["imported_at"] = existing.get("imported_at", timestamp)
    document["updated_at"] = timestamp
    document["source_changed_at"] = timestamp
    db["safety_notices"].find_one_and_update(
        {"_id": existing["_id"]},
        {"$set": document},
        return_document=True,
    )
    return "updated"


def import_records(db: Database, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Idempotently upsert manually verified official-source records."""
    result: dict[str, Any] = {
        "received": len(records),
        "created": 0,
        "updated": 0,
        "failed": 0,
        "requires_manual_review": [],
        "errors": [],
    }

    for index, raw_record in enumerate(records):
        try:
            normalized = normalize_record({
                **raw_record,
                "record_origin": "verified_import",
                "verification_status": "verified",
            })
            validated = validate_record(normalized)
            source_url = str(validated.source_url)
            now = datetime.now(timezone.utc)
            lots = [
                _lot_to_document(lot)
                for lot in validated.affected_lots
            ]
            for lot in lots:
                if isinstance(lot, dict):
                    lot["extraction_method"] = (
                        lot.get("extraction_method")
                        or "manual_official_source_review"
                    )
                    lot["verification_status"] = (
                        lot.get("verification_status") or "verified"
                    )
                    lot["source_reference"] = lot.get("source_reference") or source_url
            attachments = [
                {
                    **attachment.model_dump(mode="python"),
                    "file_url": str(attachment.file_url),
                }
                for attachment in validated.attachments
            ]
            field_provenance = build_field_provenance(
                {
                    "title": validated.title,
                    "product_name": validated.product_name,
                    "generic_name": validated.generic_name,
                    "registration_no": validated.registration_no,
                    "manufacturer": validated.manufacturer,
                    "dosage_form": validated.dosage_form,
                    "product_strength": validated.product_strength,
                    "notice_type": validated.notice_type.value,
                    "reason": validated.reason,
                    "recall_action": validated.recall_action,
                    "impact": validated.impact,
                    "affected_lots": lots,
                    "attachments": attachments,
                    "published_at": _date_to_mongo_datetime(validated.published_at),
                },
                origin="manually_verified",
                extraction_method="manual_official_source_review",
                source_reference=source_url,
            )
            document = {
                "source_id": validated.source_id,
                "source_name": validated.source_name or "Thai FDA",
                "source_url": source_url,
                "title": validated.title,
                "product_name": validated.product_name,
                "product_name_th": validated.product_name_th,
                "product_name_en": validated.product_name_en,
                "generic_name": validated.generic_name,
                "registration_no": validated.registration_no,
                "manufacturer": validated.manufacturer,
                "dosage_form": validated.dosage_form,
                "product_strength": validated.product_strength,
                "notice_type": validated.notice_type.value,
                "recall_action": validated.recall_action,
                "reason": validated.reason,
                "impact": validated.impact,
                "affected_lots": lots,
                "attachments": attachments,
                "published_at": _date_to_mongo_datetime(validated.published_at),
                "updated_at_source": validated.updated_at_source,
                "source_detail_id": validated.source_detail_id,
                "source_detail_status": validated.source_detail_status,
                "source_attachments_status": validated.source_attachments_status,
                "raw_source_data": validated.raw_source_data or raw_record,
                "field_provenance": field_provenance,
                "imported_at": now,
                "updated_at": now,
                "record_origin": "verified_import",
                "verification_status": "verified",
                "data_completeness": _compute_completeness(
                    validated.registration_no, lots, validated.manufacturer
                ),
            }
            existing = db["safety_notices"].find_one({"source_url": source_url}, {"_id": 1})
            query = {"source_url": source_url}
            update = {
                "$set": {key: value for key, value in document.items() if key != "imported_at"},
                "$setOnInsert": {"imported_at": now},
            }
            db["safety_notices"].find_one_and_update(query, update, upsert=True, return_document=True)
            result["updated" if existing else "created"] += 1
            if not validated.registration_no or not lots:
                result["requires_manual_review"].append({
                    "record": index,
                    "source_url": source_url,
                    "missing_fields": [
                        field for field, absent in (
                            ("registration_no", not validated.registration_no),
                            ("affected_lots", not lots),
                        ) if absent
                    ],
                })
        except Exception as exc:
            result["failed"] += 1
            result["errors"].append({"record": index, "error": str(exc)})
    return result
