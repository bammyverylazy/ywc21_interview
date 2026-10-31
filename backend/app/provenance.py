from __future__ import annotations

from typing import Any, Mapping


def build_field_provenance(
    values: Mapping[str, Any],
    *,
    origin: str,
    extraction_method: str,
    source_reference: str | None,
    source_fields: Mapping[str, list[str]] | None = None,
    origin_overrides: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Describe how each value was obtained without treating absence as data."""
    field_sources = source_fields or {}
    field_origins = origin_overrides or {}
    provenance: dict[str, dict[str, Any]] = {}
    for field, value in values.items():
        present = value is not None and value != "" and value != []
        field_origin = field_origins.get(field, origin) if present else "missing"
        provenance[field] = {
            "origin": field_origin,
            "extraction_method": extraction_method,
            "source_fields": field_sources.get(field, []),
            "source_reference": source_reference,
            "verification_status": (
                "verified" if field_origin == "manually_verified" else "manual_review"
            ),
        }
    return provenance
