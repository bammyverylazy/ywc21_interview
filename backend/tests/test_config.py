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


def test_env_file_path_resolves_relative_to_config_module(monkeypatch):
    """_ENV_FILE must resolve to backend/.env regardless of the working directory.

    This is the fix for the 503 Service Unavailable bug: when the backend was
    started from the project root, load_dotenv() found no .env file and
    FDA_SYNC_ENABLED defaulted to False (empty-string != "true").
    """
    from pathlib import Path
    from app.config import _ENV_FILE

    # The resolved path must end with backend/.env
    assert _ENV_FILE.name == ".env"
    assert _ENV_FILE.parent.name == "backend"
    # It must be the same .env that lives next to requirements.txt
    assert (_ENV_FILE.parent / "requirements.txt").exists() or (
        _ENV_FILE.parent / ".env.example"
    ).exists(), "_ENV_FILE does not point at the backend directory"


def test_fda_sync_disabled_by_default_when_env_var_absent(monkeypatch):
    """When FDA_SYNC_ENABLED is not set, sync must default to disabled (safe default)."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.delenv("FDA_SYNC_ENABLED", raising=False)

    settings = get_settings()

    assert settings.fda_sync_enabled is False


def test_fda_sync_enabled_when_set_to_true(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("FDA_SYNC_ENABLED", "true")

    assert get_settings().fda_sync_enabled is True


def test_fda_sync_disabled_when_set_to_false(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("FDA_SYNC_ENABLED", "false")

    assert get_settings().fda_sync_enabled is False
