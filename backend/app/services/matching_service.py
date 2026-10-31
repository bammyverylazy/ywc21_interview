from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.schemas.match import MatchStatus, ReviewStatus
from app.utils.object_id import doc_to_dict, parse_object_id

MATCHING_VERSION = "1.0.0"


def _key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def _lots(notice: dict) -> list[str]:
    result: list[str] = []
    for lot in notice.get("affected_lots") or []:
        value = lot.get("lot_number") if isinstance(lot, dict) else lot
        if isinstance(value, str) and value.strip():
            result.append(value.strip())
    return result


def _identity(inventory: dict, notice: dict) -> tuple[str, list[str], list[str]]:
    product = inventory.get("product") or {}
    product_reg = _key(product.get("registration_no"))
    notice_reg = _key(notice.get("registration_no"))
    product_brand = _key(product.get("brand_name"))
    notice_brand = _key(notice.get("product_name_th") or notice.get("product_name"))
    product_generic = _key(product.get("generic_name"))
    notice_generic = _key(notice.get("generic_name"))
    product_mfr = _key(product.get("manufacturer"))
    notice_mfr = _key(notice.get("manufacturer"))
    fields: list[str] = []
    missing: list[str] = []

    registration_matches = bool(product_reg and notice_reg and product_reg == notice_reg)
    brand_matches = bool(product_brand and notice_brand and product_brand == notice_brand)
    generic_matches = bool(product_generic and notice_generic and product_generic == notice_generic)
    manufacturer_matches = bool(product_mfr and notice_mfr and product_mfr == notice_mfr)
    registration_conflict = bool(product_reg and notice_reg and product_reg != notice_reg)
    manufacturer_conflict = bool(product_mfr and notice_mfr and product_mfr != notice_mfr)

    if registration_matches:
        fields.append("registration_no")
    elif not product_reg or not notice_reg:
        missing.append("registration_no")
    if brand_matches:
        fields.append("brand_name")
    elif not product_brand or not notice_brand:
        missing.append("brand_name")
    if generic_matches:
        fields.append("generic_name")
    elif not product_generic or not notice_generic:
        missing.append("generic_name")
    if manufacturer_matches:
        fields.append("manufacturer")
    elif not product_mfr or not notice_mfr:
        missing.append("manufacturer")

    related = registration_matches or brand_matches or generic_matches
    conflict = registration_conflict or manufacturer_conflict
    comparable = any((
        product_reg and notice_reg,
        product_brand and notice_brand,
        product_generic and notice_generic,
        product_mfr and notice_mfr,
    ))
    strong = registration_matches or (
        brand_matches and generic_matches and manufacturer_matches and not conflict
    )
    identity = (
        "conflict" if conflict
        else "strong" if strong
        else "related" if related
        else "unrelated" if comparable
        else "unknown"
    )
    return identity, fields, missing


def evaluate_pair(inventory: dict, notice: dict) -> dict:
    identity, fields, missing = _identity(inventory, notice)
    inventory_lot = inventory.get("lot_number")
    affected_lots = _lots(notice)
    matched_lots = {_key(value) for value in affected_lots}

    if not inventory.get("product"):
        missing.append("product_identity")
    if not inventory_lot:
        missing.append("inventory_lot_number")
    if not affected_lots:
        missing.append("notice_affected_lots")

    if identity == "unrelated":
        match_status = MatchStatus.NO_MATCH
        reason = "ไม่พบข้อมูลระบุตัวผลิตภัณฑ์ที่ตรงกัน การไม่พบรายการตรงกันไม่ได้ยืนยันว่ายาปลอดภัย"
    elif identity == "unknown":
        match_status = MatchStatus.POTENTIAL_MATCH
        reason = "ข้อมูลระบุตัวผลิตภัณฑ์ไม่เพียงพอสำหรับเปรียบเทียบ ต้องตรวจสอบข้อมูลและประกาศต้นฉบับด้วยตนเอง"
    elif identity == "conflict":
        match_status = MatchStatus.POTENTIAL_MATCH
        reason = "พบข้อมูลผลิตภัณฑ์ที่อาจเกี่ยวข้อง แต่เลขทะเบียนหรือผู้ผลิตขัดแย้งกัน ต้องตรวจสอบกับประกาศต้นฉบับ"
    elif not affected_lots or not inventory_lot:
        match_status = MatchStatus.POTENTIAL_MATCH
        reason = "ข้อมูลผลิตภัณฑ์อาจเกี่ยวข้อง แต่ไม่มีเลข LOT ที่ยืนยันได้ทั้งสองด้าน ต้องตรวจสอบด้วยตนเอง"
    elif _key(inventory_lot) in matched_lots and identity == "strong":
        match_status = MatchStatus.EXACT_MATCH
        fields.append("lot_number")
        reason = "ข้อมูลระบุตัวผลิตภัณฑ์ที่เชื่อถือได้และเลข LOT ตรงกับ LOT ที่ประกาศระบุ"
    elif _key(inventory_lot) in matched_lots:
        match_status = MatchStatus.POTENTIAL_MATCH
        fields.append("lot_number")
        reason = "เลข LOT ตรงกับประกาศ แต่ข้อมูลระบุตัวผลิตภัณฑ์ยังไม่เพียงพอสำหรับยืนยันรายการตรงกัน"
    elif identity == "strong":
        match_status = MatchStatus.NO_MATCH
        reason = "ข้อมูลผลิตภัณฑ์ตรงกัน แต่เลข LOT ในคลังไม่อยู่ในรายการ LOT ที่ประกาศระบุ"
    else:
        match_status = MatchStatus.POTENTIAL_MATCH
        reason = "ชื่อผลิตภัณฑ์อาจเกี่ยวข้อง แต่ข้อมูลระบุตัวผลิตภัณฑ์ไม่เพียงพอ ต้องตรวจสอบด้วยตนเอง"

    return {
        "match_status": match_status.value,
        "match_reason": reason,
        "matched_fields": sorted(set(fields)),
        "missing_fields": sorted(set(missing)),
    }


def _enrich_match(db: Database, match: dict) -> dict:
    inventory_doc = db["inventory_items"].find_one({"_id": match["inventory_id"]})
    notice_doc = db["safety_notices"].find_one({"_id": match["notice_id"]})
    if inventory_doc:
        product_doc = db["products"].find_one({"_id": inventory_doc.get("product_id")})
        inventory_doc["product"] = doc_to_dict(product_doc) if product_doc else None
        match["inventory"] = doc_to_dict(inventory_doc)
    else:
        match["inventory"] = None
    match["notice"] = doc_to_dict(notice_doc) if notice_doc else None
    latest_action = db["action_logs"].find({"match_id": match["_id"]}).sort("created_at", -1).limit(1)
    action = next(iter(latest_action), None)
    match["review_status"] = action.get("status", ReviewStatus.PENDING.value) if action else ReviewStatus.PENDING.value
    return doc_to_dict(match)


def run_matching(db: Database, inventory_id: str | None = None) -> dict:
    inventory_query: dict[str, Any] = {}
    if inventory_id:
        inventory_query["_id"] = parse_object_id(inventory_id)
    inventory_items = list(db["inventory_items"].find(inventory_query))
    notices = list(db["safety_notices"].find({}))
    now = datetime.now(timezone.utc)
    counts = {item.value: 0 for item in MatchStatus}
    checked = 0

    for inventory_raw in inventory_items:
        product_raw = db["products"].find_one({"_id": inventory_raw.get("product_id")})
        inventory = {**inventory_raw, "product": product_raw}
        for notice in notices:
            result = evaluate_pair(inventory, notice)
            identity_query = {
                "inventory_id": inventory_raw["_id"],
                "notice_id": notice["_id"],
            }
            existing = db["matches"].find_one(identity_query)
            document = {
                **identity_query,
                **result,
                "checked_at": now,
                "matching_version": MATCHING_VERSION,
            }
            if existing:
                # Preserve the match identifier and review trail while refreshing current comparison.
                db["matches"].find_one_and_update(
                    {"_id": existing["_id"]},
                    {"$set": document},
                    return_document=True,
                )
            else:
                db["matches"].insert_one(document)
            counts[result["match_status"]] += 1
            checked += 1

    return {
        "total_checked": checked,
        "exact_matches": counts[MatchStatus.EXACT_MATCH.value],
        "potential_matches": counts[MatchStatus.POTENTIAL_MATCH.value],
        "no_matches": counts[MatchStatus.NO_MATCH.value],
    }


def list_matches(
    db: Database,
    *,
    match_status: str | None = None,
    review_status: str | None = None,
    product_id: str | None = None,
    notice_id: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    query: dict[str, Any] = {}
    if match_status:
        query["match_status"] = match_status
    if notice_id:
        query["notice_id"] = parse_object_id(notice_id)
    if product_id:
        inventory_ids = [
            item["_id"] for item in db["inventory_items"].find({"product_id": parse_object_id(product_id)})
        ]
        query["inventory_id"] = {"$in": inventory_ids}
    docs = list(db["matches"].find(query).sort("checked_at", -1))
    matches = [_enrich_match(db, doc) for doc in docs]
    if review_status:
        matches = [match for match in matches if match["review_status"] == review_status]
    if search:
        term = _key(search)
        matches = [
            match for match in matches
            if any(term in _key(value) for value in (
                (match.get("inventory") or {}).get("lot_number"),
                ((match.get("inventory") or {}).get("product") or {}).get("brand_name"),
                ((match.get("inventory") or {}).get("product") or {}).get("generic_name"),
                ((match.get("inventory") or {}).get("product") or {}).get("registration_no"),
                ((match.get("inventory") or {}).get("product") or {}).get("manufacturer"),
                (match.get("notice") or {}).get("title"),
                (match.get("notice") or {}).get("product_name"),
            ))
        ]
    total = len(matches)
    return matches[skip:skip + limit], total


def get_match(db: Database, match_id: str) -> dict:
    oid = parse_object_id(match_id)
    match = db["matches"].find_one({"_id": oid})
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    return _enrich_match(db, match)


def add_action(db: Database, match_id: str, action_status: ReviewStatus, action_note: str) -> dict:
    match_oid = parse_object_id(match_id)
    if db["matches"].find_one({"_id": match_oid}, {"_id": 1}) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    note = action_note.strip()
    if not note:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="action_note must not be blank.")
    doc = {
        "match_id": match_oid,
        "status": action_status.value,
        "action_note": note,
        "created_at": datetime.now(timezone.utc),
        "actor": None,
    }
    result = db["action_logs"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc_to_dict(doc)


def list_actions(db: Database, match_id: str) -> list[dict]:
    match_oid = parse_object_id(match_id)
    if db["matches"].find_one({"_id": match_oid}, {"_id": 1}) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    return [
        doc_to_dict(log)
        for log in db["action_logs"].find({"match_id": match_oid}).sort("created_at", -1)
    ]
