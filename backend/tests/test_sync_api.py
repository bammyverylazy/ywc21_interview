from bson import ObjectId
from pymongo.errors import ServerSelectionTimeoutError

from app import config
from app.services import sync_service


def configure_sync(monkeypatch, *, enabled="true"):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("FDA_SYNC_ENABLED", enabled)
    config.get_settings.cache_clear()


def test_sync_status_and_history_are_readable(client, fake_db):
    response = client.get("/api/sync/status")

    assert response.status_code == 200
    assert response.json()["current_status"] == "NOT_RUN"
    assert client.get("/api/sync/history").json()["total"] == 0


def test_sync_trigger_starts_without_admin_key(client, monkeypatch, fake_db):
    configure_sync(monkeypatch, enabled="true")
    monkeypatch.setattr(sync_service, "execute_sync", lambda *_args, **_kwargs: None)

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    assert fake_db["sync_logs"].count_documents({"trigger_type": "MANUAL"}) == 1


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
    assert "private connection detail" not in response.text


def test_sync_trigger_rejects_an_existing_sync(client, monkeypatch, fake_db):
    configure_sync(monkeypatch)
    run_id, acquired = sync_service.begin_sync(fake_db, "SCHEDULED")
    assert acquired

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 409
    assert response.json()["detail"]["category"] == "sync_already_running"
    assert "already running" in response.json()["detail"]["message"]
    assert fake_db["sync_logs"].find_one({"_id": ObjectId(run_id)})["status"] == "RUNNING"


def test_sync_trigger_enforces_cooldown(client, monkeypatch, fake_db):
    configure_sync(monkeypatch)
    _, acquired = sync_service.begin_sync(fake_db, "MANUAL")
    assert acquired
    fake_db["sync_locks"].delete_one({"_id": sync_service.LOCK_ID})

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert "Try again in" in response.json()["detail"]["message"]


def test_sync_trigger_schedules_background_task_without_admin_key(
    client, monkeypatch, fake_db
):
    configure_sync(monkeypatch)
    monkeypatch.setattr(sync_service, "execute_sync", lambda *_args, **_kwargs: None)

    response = client.post("/api/sync/thai-fda")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    assert fake_db["sync_logs"].count_documents({"trigger_type": "MANUAL"}) == 1
