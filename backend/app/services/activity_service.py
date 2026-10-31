from __future__ import annotations

from datetime import date
from typing import Optional

from pymongo.database import Database

from app.schemas.match import ReviewStatus
from app.services.matching_service import _enrich_match
from app.utils.object_id import doc_to_dict

ACTIVITY_LABELS = {
    "MATCH_DETECTED": "A relevant inventory match was detected.",
    "REVIEWED": "Match reviewed.",
    "ESCALATED": "Case escalated for further review.",
    "ACTION_RECORDED": "Action recorded.",
}


def list_activity(
    db: Database,
    *,
    search: Optional[str] = None,
    activity_type: Optional[str] = None,
    review_status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    events: list[dict] = []
    for match_doc in db["matches"].find({}).sort("checked_at", -1):
        match = _enrich_match(db, match_doc)
        if match["match_status"] != "NO_MATCH":
            events.append({
                "id": f"detected-{match['id']}",
                "activity_type": "MATCH_DETECTED",
                "description": ACTIVITY_LABELS["MATCH_DETECTED"],
                "occurred_at": match["checked_at"],
                "match_id": match["id"],
                "match": match,
                "actor": None,
                "previous_status": None,
                "new_status": None,
                "notes": None,
            })

        match_oid = match_doc["_id"]
        previous_status: Optional[str] = None
        logs = list(db["action_logs"].find({"match_id": match_oid}).sort("created_at", 1))
        for log in logs:
            status_value = log["status"]
            events.append({
                "id": str(log["_id"]),
                "activity_type": status_value,
                "description": ACTIVITY_LABELS.get(status_value, "Review status updated."),
                "occurred_at": log["created_at"],
                "match_id": str(match_oid),
                "match": match,
                "actor": log.get("actor"),
                "previous_status": previous_status,
                "new_status": status_value,
                "notes": log.get("action_note"),
            })
            previous_status = status_value

    events.sort(key=lambda event: event["occurred_at"], reverse=True)
    if activity_type:
        events = [event for event in events if event["activity_type"] == activity_type]
    if review_status:
        events = [
            event for event in events
            if event["new_status"] == review_status
            or (event["new_status"] is None and (event["match"] or {}).get("review_status") == review_status)
        ]
    if date_from:
        events = [event for event in events if event["occurred_at"].date() >= date_from]
    if date_to:
        events = [event for event in events if event["occurred_at"].date() <= date_to]
    if search:
        needle = search.casefold().strip()
        def matches_search(event: dict) -> bool:
            match = event.get("match") or {}
            inventory = match.get("inventory") or {}
            product = inventory.get("product") or {}
            notice = match.get("notice") or {}
            values = (
                event.get("description"),
                event.get("notes"),
                event.get("actor"),
                product.get("brand_name"),
                product.get("generic_name"),
                product.get("registration_no"),
                inventory.get("lot_number"),
                notice.get("title"),
                notice.get("product_name"),
                event.get("match_id"),
            )
            return any(needle in value.casefold() for value in values if isinstance(value, str))
        events = [event for event in events if matches_search(event)]
    total = len(events)
    return events[skip:skip + limit], total


def get_activity(db: Database, event_id: str) -> dict:
    if event_id.startswith("detected-"):
        match_id = event_id.removeprefix("detected-")
        from app.services.matching_service import get_match
        match = get_match(db, match_id)
        if match["match_status"] == "NO_MATCH":
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity event not found.")
        return {
            "id": event_id,
            "activity_type": "MATCH_DETECTED",
            "description": ACTIVITY_LABELS["MATCH_DETECTED"],
            "occurred_at": match["checked_at"],
            "match_id": match_id,
            "match": match,
            "actor": None,
            "previous_status": None,
            "new_status": None,
            "notes": None,
        }

    from bson import ObjectId
    from fastapi import HTTPException, status
    from app.services.matching_service import get_match

    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid activity id.")
    log = db["action_logs"].find_one({"_id": ObjectId(event_id)})
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity event not found.")
    match_id = str(log["match_id"])
    match = get_match(db, match_id)
    previous = list(db["action_logs"].find({"match_id": log["match_id"]}).sort("created_at", 1))
    previous_status = None
    for previous_log in previous:
        if previous_log["_id"] == log["_id"]:
            break
        previous_status = previous_log["status"]
    status_value = log["status"]
    return {
        "id": event_id,
        "activity_type": status_value,
        "description": ACTIVITY_LABELS.get(status_value, "Review status updated."),
        "occurred_at": log["created_at"],
        "match_id": match_id,
        "match": match,
        "actor": log.get("actor"),
        "previous_status": previous_status,
        "new_status": status_value,
        "notes": log.get("action_note"),
    }
