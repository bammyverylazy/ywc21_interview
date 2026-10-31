from __future__ import annotations

from typing import Any


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map one canonical verified import record to the API's notice schema."""
    data = dict(record)
    if "product_name" not in data:
        data["product_name"] = data.get("product_name_th") or data.get("product_name_en")
    data.setdefault("source_name", "Thai FDA")
    data.setdefault("affected_lots", [])
    data.setdefault("raw_source_data", dict(record))

    for field in (
        "title", "product_name", "generic_name", "registration_no", "manufacturer",
        "reason", "source_name", "source_id", "product_name_th", "product_name_en",
        "recall_action", "impact",
    ):
        value = data.get(field)
        if isinstance(value, str):
            stripped = value.strip()
            data[field] = stripped or None

    cleaned_lots = []
    for lot in data["affected_lots"] or []:
        if isinstance(lot, str):
            if lot.strip():
                cleaned_lots.append(lot.strip())
        elif isinstance(lot, dict):
            cleaned_lots.append({
                key: value.strip() if isinstance(value, str) else value
                for key, value in lot.items()
            })
        else:
            cleaned_lots.append(lot)
    data["affected_lots"] = cleaned_lots
    data.setdefault("record_origin", "verified_import")
    data.setdefault("verification_status", "verified")
    return data
