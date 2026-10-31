from __future__ import annotations

from pymongo.database import Database

from app.schemas.match import MatchStatus, ReviewStatus
from app.services.matching_service import _enrich_match
from app.utils.object_id import doc_to_dict


def summary(db: Database) -> dict:
    match_docs = list(db["matches"].find({}))
    matches = [_enrich_match(db, match) for match in match_docs]
    notices = list(db["safety_notices"].find({}).sort("imported_at", -1).limit(1))
    latest = notices[0].get("imported_at") if notices else None
    return {
        "total_products": db["products"].count_documents({}),
        "total_inventory": db["inventory_items"].count_documents({}),
        "total_notices": db["safety_notices"].count_documents({}),
        "exact_matches": sum(m["match_status"] == MatchStatus.EXACT_MATCH.value for m in matches),
        "potential_matches": sum(m["match_status"] == MatchStatus.POTENTIAL_MATCH.value for m in matches),
        "pending_review": sum(m["review_status"] == ReviewStatus.PENDING.value for m in matches),
        "last_notice_at": latest.isoformat() if latest else None,
    }


def attention_items(db: Database, limit: int = 20) -> list[dict]:
    matches = [
        _enrich_match(db, match)
        for match in db["matches"].find({}).sort("checked_at", -1)
    ]
    needs_attention = [
        match for match in matches
        if match["review_status"] == ReviewStatus.PENDING.value
        and match["match_status"] != MatchStatus.NO_MATCH.value
    ]
    return needs_attention[:limit]


def recent_activity(db: Database, limit: int = 10) -> list[dict]:
    logs = list(db["action_logs"].find({}).sort("created_at", -1).limit(limit))
    return [doc_to_dict(log) for log in logs]
