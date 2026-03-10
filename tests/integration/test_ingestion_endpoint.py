"""Integration tests for POST /api/v1/ingest (TASK-019).

run_ingestion is patched out in all tests — it makes live OL HTTP calls and
runs as a BackgroundTask (which TestClient executes synchronously). The unit
tests in tests/unit/test_ingestion.py cover the service logic in full.
"""

from unittest.mock import AsyncMock, patch

from app.models.ingestion_log import IngestionLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_tenant(client, name="acme") -> dict:
    resp = client.post("/api/v1/admin/tenants", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


def _auth_headers(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def _ingest(client, tenant, query_type="author", query_value="tolkien"):
    with patch("app.api.v1.ingestion.run_ingestion", new=AsyncMock()):
        return client.post(
            "/api/v1/ingest",
            json={"query_type": query_type, "query_value": query_value},
            headers=_auth_headers(tenant["api_key"]),
        )


# ---------------------------------------------------------------------------
# POST /api/v1/ingest
# ---------------------------------------------------------------------------


def test_ingest_returns_202(client):
    tenant = _create_tenant(client)
    resp = _ingest(client, tenant)
    assert resp.status_code == 202


def test_ingest_returns_log_id(client):
    tenant = _create_tenant(client)
    resp = _ingest(client, tenant)
    data = resp.json()
    assert "log_id" in data
    assert data["log_id"]


def test_ingest_returns_status_pending(client):
    tenant = _create_tenant(client)
    resp = _ingest(client, tenant)
    assert resp.json()["status"] == "pending"


def test_ingest_creates_log_row_in_db(client, db):
    tenant = _create_tenant(client)
    resp = _ingest(client, tenant)
    log_id = resp.json()["log_id"]
    log = db.query(IngestionLog).filter_by(id=log_id).first()
    assert log is not None


def test_ingest_log_row_has_correct_query_fields(client, db):
    tenant = _create_tenant(client)
    resp = _ingest(client, tenant)
    log_id = resp.json()["log_id"]
    log = db.query(IngestionLog).filter_by(id=log_id).first()
    assert log.query_type == "author"
    assert log.query_value == "tolkien"


def test_ingest_rejects_invalid_query_type(client):
    tenant = _create_tenant(client)
    # No patch needed — request is rejected before background task is added
    resp = client.post(
        "/api/v1/ingest",
        json={"query_type": "title", "query_value": "dune"},
        headers=_auth_headers(tenant["api_key"]),
    )
    assert resp.status_code == 422


def test_ingest_accepts_subject_query_type(client):
    tenant = _create_tenant(client)
    resp = _ingest(client, tenant, query_type="subject", query_value="fantasy")
    assert resp.status_code == 202


def test_ingest_requires_auth(client):
    resp = client.post(
        "/api/v1/ingest",
        json={"query_type": "author", "query_value": "tolkien"},
    )
    assert resp.status_code in (401, 422)


def test_ingest_log_scoped_to_tenant(client, db):
    t1 = _create_tenant(client, "tenant1")
    _create_tenant(client, "tenant2")

    _ingest(client, t1)

    logs = db.query(IngestionLog).all()
    assert len(logs) == 1
    assert logs[0].tenant_id == t1["id"]
