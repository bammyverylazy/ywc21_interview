"""Application configuration loaded from environment variables.

Settings are loaded explicitly via ``get_settings()`` (not at import time) so that
a missing variable produces one clear ``ConfigurationError`` at startup instead of
an obscure failure later.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    database_name: str
    frontend_url: str
    environment: str


def _clean(value: str | None) -> str:
    return (value or "").strip()


@lru_cache
def get_settings() -> Settings:
    # Reads backend/.env if present. Real environment variables take precedence.
    load_dotenv()

    mongodb_uri = _clean(os.getenv("MONGODB_URI"))
    if not mongodb_uri:
        raise ConfigurationError(
            "MONGODB_URI is not set. Copy backend/.env.example to backend/.env "
            "and fill in your MongoDB Atlas connection string."
        )

    return Settings(
        mongodb_uri=mongodb_uri,
        database_name=_clean(os.getenv("DATABASE_NAME")) or "lotshield_db",
        frontend_url=_clean(os.getenv("FRONTEND_URL")) or "http://localhost:5173",
        environment=_clean(os.getenv("ENVIRONMENT")) or "development",
    )
