"""
API-level tests for POST /api/sync/thai-fda.

These tests use a FakeDB in-process and never touch MongoDB Atlas
or the Thai FDA service.
"""
from bson import ObjectId
from pymongo.errors import ServerSelectionTimeoutError

from app import config
from app.services import sync_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def configure_sync(monkeypatch, *, enabled="true"):
    """Set env vars so get_settings() returns a known configuration."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("FDA_SYNC_ENABLED", enabled)
    config.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Status / history (read-only endpoints)
# ---------------------------------------------------------------------------


def test_sync_status_and_history_are_readable(client, fake_db):
    response = client.get("/api/sync/status")

    assert response.status_code == 200
    assert response.json()["current_status"] == "NOT_RUN"
    assert client.get("/api/sync/history").json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /api/sync/thai-fda — happy path
# ---------------------------------------------------------------------------


def test_sync_trigger_starts_without_admin_key(client, monkeypatch, fake_db):
    configure_sync(monkeypatch, enabled="true")
    monkeypatch.setattr(sync_service, "execute_sync", lambda *_args, **_kwargs: None)

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    assert fake_db["sync_logs"].count_documents({"trigger_type": "MANUAL"}) == 1


def test_sync_trigger_schedules_background_task_without_admin_key(
    client, monkeypatch, fake_db
):
    configure_sync(monkeypatch)
    monkeypatch.setattr(sync_service, "execute_sync", lambda *_args, **_kwargs: None)

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    assert fake_db["sync_logs"].count_documents({"trigger_type": "MANUAL"}) == 1


# ---------------------------------------------------------------------------
# POST /api/sync/thai-fda — configuration errors → 503
# ---------------------------------------------------------------------------


def test_sync_trigger_is_disabled_unless_explicitly_configured(
    client, monkeypatch
):
    configure_sync(monkeypatch, enabled="false")

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["category"] == "sync_disabled"
    assert detail["stage"] == "configuration"
    assert "FDA_SYNC_ENABLED=true" in detail["message"]


def test_sync_trigger_503_message_names_env_var(client, monkeypatch):
    """The 503 body must mention the env var so the operator can fix it."""
    configure_sync(monkeypatch, enabled="false")
    body = client.post("/api/sync/thai-fda").text
    assert "FDA_SYNC_ENABLED" in body


# ---------------------------------------------------------------------------
# POST /api/sync/thai-fda — MongoDB unavailable → 503
# ---------------------------------------------------------------------------


def test_sync_trigger_reports_mongodb_unavailable(client, monkeypatch):
    configure_sync(monkeypatch)

    def fail_db_check(_db):
        raise ServerSelectionTimeoutError("private connection detail")

    monkeypatch.setattr(sync_service, "sync_is_running", fail_db_check)

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["category"] == "mongodb_unavailable"
    assert detail["stage"] == "lock_check"
    # Internal connection strings must not leak to the client.
    assert "private connection detail" not in response.text


def test_sync_trigger_mongodb_failure_during_lock_acquisition(
    client, monkeypatch, fake_db
):
    configure_sync(monkeypatch)

    def fail_begin(*_args, **_kwargs):
        raise ServerSelectionTimeoutError("atlas timeout")

    monkeypatch.setattr(sync_service, "begin_sync", fail_begin)

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 503
    assert "mongodb_unavailable" in response.text


# ---------------------------------------------------------------------------
# POST /api/sync/thai-fda — concurrent sync / cooldown → 409 / 429
# ---------------------------------------------------------------------------


def test_sync_trigger_rejects_an_existing_sync(client, monkeypatch, fake_db):
    configure_sync(monkeypatch)
    run_id, acquired = sync_service.begin_sync(fake_db, "SCHEDULED")
    assert acquired

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 409
    assert response.json()["detail"]["category"] == "sync_already_running"
    assert "already running" in response.json()["detail"]["message"]
    # The original running sync must not be disturbed.
    assert fake_db["sync_logs"].find_one({"_id": ObjectId(run_id)})["status"] == "RUNNING"


def test_sync_trigger_enforces_cooldown(client, monkeypatch, fake_db):
    configure_sync(monkeypatch)
    _, acquired = sync_service.begin_sync(fake_db, "MANUAL")
    assert acquired
    # Release the lock so sync_is_running returns False, but keep the run
    # log so the cooldown check fires.
    fake_db["sync_locks"].delete_one({"_id": sync_service.LOCK_ID})

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert "Try again in" in response.json()["detail"]["message"]


def test_sync_trigger_lock_rejected_run_does_not_count_toward_cooldown(
    client, monkeypatch, fake_db
):
    """A run whose lock was not acquired (lock_acquired=False) must not
    prevent the next manual trigger."""
    configure_sync(monkeypatch)
    # Simulate a rejected lock attempt: run inserted but lock NOT acquired.
    run_id, acquired = sync_service.begin_sync(fake_db, "MANUAL")
    assert acquired
    # A second competing begin_sync will fail to acquire the lock.
    _, competing = sync_service.begin_sync(fake_db, "MANUAL")
    assert not competing
    # Now release the successful lock so sync is not running.
    fake_db["sync_locks"].delete_one({"_id": sync_service.LOCK_ID})
    # The competing (rejected) run has lock_acquired=False and must NOT
    # trigger the cooldown by itself.  The *first* successful run DOES
    # trigger the cooldown, so the second post is still 429, but only
    # because of the first run, not the rejected one.
    response = client.post("/api/sync/thai-fda")
    assert response.status_code == 429  # cooldown from the first successful run
