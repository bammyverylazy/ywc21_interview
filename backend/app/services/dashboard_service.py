from __future__ import annotations

from pymongo.database import Database

from app.schemas.match import MatchStatus, ReviewStatus
from app.services.matching_service import _enrich_matches
from app.utils.object_id import doc_to_dict


def summary(db: Database) -> dict:
    match_docs = list(db["matches"].find({}, {"_id": 1, "match_status": 1}))
    match_ids = [match["_id"] for match in match_docs]
    latest_status_by_match = {}
    if match_ids:
        action_logs = db["action_logs"].find(
            {"match_id": {"$in": match_ids}},
            {"match_id": 1, "status": 1, "created_at": 1},
        ).sort("created_at", -1)
        for action in action_logs:
            latest_status_by_match.setdefault(action["match_id"], action["status"])

    notices = list(db["safety_notices"].find({}).sort("imported_at", -1).limit(1))
    latest = notices[0].get("imported_at") if notices else None
    return {
        "total_products": db["products"].count_documents({}),
        "total_inventory": db["inventory_items"].count_documents({}),
        "total_notices": db["safety_notices"].count_documents({}),
        "exact_matches": sum(
            match["match_status"] == MatchStatus.EXACT_MATCH.value
            for match in match_docs
        ),
        "potential_matches": sum(
            match["match_status"] == MatchStatus.POTENTIAL_MATCH.value
            for match in match_docs
        ),
        "pending_review": sum(
            latest_status_by_match.get(match["_id"], ReviewStatus.PENDING.value)
            == ReviewStatus.PENDING.value
            for match in match_docs
        ),
        "last_notice_at": latest.isoformat() if latest else None,
    }


def attention_items(db: Database, limit: int = 20) -> list[dict]:
    query = {
        "match_status": {
            "$in": [MatchStatus.EXACT_MATCH.value, MatchStatus.POTENTIAL_MATCH.value]
        }
    }
    needs_attention = []
    offset = 0
    batch_size = max(100, limit * 5)

    while len(needs_attention) < limit:
        match_docs = list(
            db["matches"]
            .find(query)
            .sort("checked_at", -1)
            .skip(offset)
            .limit(batch_size)
        )
        if not match_docs:
            break
        match_ids = [match["_id"] for match in match_docs]
        latest_status_by_match = {}
        action_logs = db["action_logs"].find(
            {"match_id": {"$in": match_ids}},
            {"match_id": 1, "status": 1, "created_at": 1},
        ).sort("created_at", -1)
        for action in action_logs:
            latest_status_by_match.setdefault(action["match_id"], action["status"])

        pending_docs = [
            match for match in match_docs
            if latest_status_by_match.get(
                match["_id"], ReviewStatus.PENDING.value
            ) == ReviewStatus.PENDING.value
        ]
        needs_attention.extend(_enrich_matches(db, pending_docs))
        offset += len(match_docs)
        if len(match_docs) < batch_size:
            break

    return needs_attention[:limit]


def recent_activity(db: Database, limit: int = 10) -> list[dict]:
    logs = list(db["action_logs"].find({}).sort("created_at", -1).limit(limit))
    return [doc_to_dict(log) for log in logs]
