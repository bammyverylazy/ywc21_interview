"""
Tests for GET /api/health.

These tests use the make_client fixture from conftest.py which wires a
FakeDB so no real MongoDB connection is needed.
"""


def test_health_ok_when_database_reachable(make_client):
    client = make_client(db_fails=False)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "YaSafe API"
    assert body["database"] == "connected"


def test_health_reports_degraded_when_database_down(make_client):
    client = make_client(db_fails=True)
    response = client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


def test_swagger_docs_available(make_client):
    client = make_client()
    response = client.get("/docs")
    assert response.status_code == 200
