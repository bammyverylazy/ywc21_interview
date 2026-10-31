from __future__ import annotations

from urllib.parse import urlparse

from app.schemas.notice import NoticeCreate

OFFICIAL_HOSTS = (
    "apres.fda.moph.go.th",
    "safetyalert.fda.moph.go.th",
    "fda.moph.go.th",
)


def validate_official_source(source_url: str) -> None:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(
        host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_HOSTS
    ):
        raise ValueError("source_url must use HTTPS and an official Thai FDA hostname")


def validate_record(record: dict) -> NoticeCreate:
    validate_official_source(str(record.get("source_url", "")))
    validated = NoticeCreate.model_validate(record)
    return validated
