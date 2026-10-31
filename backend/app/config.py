"""Application configuration loaded from environment variables.

Settings are loaded explicitly via ``get_settings()`` (not at import time) so that
a missing variable produces one clear ``ConfigurationError`` at startup instead of
an obscure failure later.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Resolve the .env file relative to this source file so the backend can be
# started from any working directory (project root, backend/, etc.) and still
# read its configuration.  Real environment variables always win; load_dotenv
# never overwrites them.
_ENV_FILE = Path(__file__).parent.parent / ".env"


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    database_name: str
    frontend_url: str
    cors_origins: tuple[str, ...]
    environment: str
    fda_sync_enabled: bool
    fda_sync_interval_hours: int
    fda_sync_timeout_seconds: float
    fda_sync_max_retries: int
    fda_sync_request_delay_seconds: float
    fda_sync_detail_enrichment_enabled: bool


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _positive_int(name: str, default: int) -> int:
    value = _clean(os.getenv(name))
    try:
        parsed = int(value) if value else default
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive integer.") from exc
    if parsed < 1:
        raise ConfigurationError(f"{name} must be a positive integer.")
    return parsed


def _positive_float(name: str, default: float) -> float:
    value = _clean(os.getenv(name))
    try:
        parsed = float(value) if value else default
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive number.") from exc
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be a positive number.")
    return parsed


@lru_cache
def get_settings() -> Settings:
    # Reads backend/.env relative to this file. Real environment variables take
    # precedence (load_dotenv never overwrites an already-set variable).
    load_dotenv(_ENV_FILE)

    mongodb_uri = _clean(os.getenv("MONGODB_URI"))
    if not mongodb_uri:
        raise ConfigurationError(
            "MONGODB_URI is not set. Copy backend/.env.example to backend/.env "
            "and fill in your MongoDB Atlas connection string."
        )

    frontend_url = _clean(os.getenv("FRONTEND_URL")) or "http://localhost:5173"
    extra_origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    return Settings(
        mongodb_uri=mongodb_uri,
        database_name=_clean(os.getenv("DATABASE_NAME")) or "YaSafe_db",
        frontend_url=frontend_url,
        cors_origins=tuple(dict.fromkeys((frontend_url, *extra_origins))),
        environment=_clean(os.getenv("ENVIRONMENT")) or "development",
        fda_sync_enabled=_clean(os.getenv("FDA_SYNC_ENABLED")).lower() == "true",
        fda_sync_interval_hours=_positive_int("FDA_SYNC_INTERVAL_HOURS", 24),
        fda_sync_timeout_seconds=_positive_float("FDA_SYNC_TIMEOUT_SECONDS", 20),
        fda_sync_max_retries=_positive_int("FDA_SYNC_MAX_RETRIES", 2),
        fda_sync_request_delay_seconds=_positive_float("FDA_SYNC_REQUEST_DELAY_SECONDS", 1),
        fda_sync_detail_enrichment_enabled=(
            _clean(os.getenv("FDA_SYNC_DETAIL_ENRICHMENT_ENABLED", "true")).lower()
            == "true"
        ),
    )
