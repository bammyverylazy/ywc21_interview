import pytest

from app import config
from app.config import ConfigurationError, get_settings


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch):
    # Don't let a developer's real backend/.env leak into these tests.
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_missing_mongodb_uri_raises_clear_error(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        get_settings()

    assert "MONGODB_URI" in str(exc_info.value)
    assert ".env.example" in str(exc_info.value)


def test_blank_mongodb_uri_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "   ")

    with pytest.raises(ConfigurationError):
        get_settings()


def test_defaults_applied_when_optional_vars_missing(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.delenv("DATABASE_NAME", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("FDA_SYNC_DETAIL_ENRICHMENT_ENABLED", raising=False)
    monkeypatch.setenv("FDA_SYNC_ADMIN_KEY", "unused")

    settings = get_settings()

    assert settings.mongodb_uri == "mongodb://localhost:27017"
    assert settings.database_name == "lotshield_db"
    assert settings.frontend_url == "http://localhost:5173"
    assert settings.environment == "development"
    assert settings.fda_sync_detail_enrichment_enabled is True
    assert not hasattr(settings, "fda_sync_admin_key")


def test_detail_enrichment_can_be_disabled_explicitly(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("FDA_SYNC_DETAIL_ENRICHMENT_ENABLED", "false")

    assert get_settings().fda_sync_detail_enrichment_enabled is False
