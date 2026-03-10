"""Integration tests for ingestion log endpoints (TASK-024, 025, 026)."""

import pytest

from app.models.ingestion_log import IngestionLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_tenant(client, name="acme") -> dict:
    resp = client.post("/api/v1/admin/tenants", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def _seed_log(db, tenant_id, status="completed", query_type="author", query_value="tolkien"):
    log = IngestionLog(
        tenant_id=tenant_id,
        query_type=query_type,
        query_value=query_value,
        status=status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# log_repo — create_log and update_log (TASK-024)
# ---------------------------------------------------------------------------


def test_create_log_returns_pending(db):
    from app.repositories.log_repo import create_log
    from app.models.tenant import Tenant

    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()

    log = create_log(db, t.id, "author", "tolkien")
    assert log.status == "pending"
    assert log.finished_at is None
    assert log.fetched_count == 0


def test_update_log_persists_status(db):
    from app.repositories.log_repo import create_log, update_log
    from app.models.tenant import Tenant
    from datetime import datetime, timezone

    t = Tenant(name="lib", api_key="hk2")
    db.add(t)
    db.commit()

    log = create_log(db, t.id, "subject", "fantasy")
    now = datetime.now(timezone.utc)
    updated = update_log(db, log.id, status="completed", finished_at=now, fetched_count=10)
    assert updated.status == "completed"
    assert updated.fetched_count == 10
    assert updated.finished_at is not None


# ---------------------------------------------------------------------------
# GET /api/v1/ingestion-logs (TASK-025)
# ---------------------------------------------------------------------------


def test_list_logs_empty(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/ingestion-logs", headers=_auth(t["api_key"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_logs_returns_logs_for_tenant(client, db):
    t = _create_tenant(client)
    _seed_log(db, t["id"])
    _seed_log(db, t["id"])
    resp = client.get("/api/v1/ingestion-logs", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 2


def test_list_logs_ordered_newest_first(client, db):
    import time
    t = _create_tenant(client)
    log1 = _seed_log(db, t["id"], query_value="tolkien")
    time.sleep(0.01)  # ensure different started_at
    log2 = _seed_log(db, t["id"], query_value="herbert")
    resp = client.get("/api/v1/ingestion-logs", headers=_auth(t["api_key"]))
    items = resp.json()["items"]
    assert items[0]["query_value"] == "herbert"
    assert items[1]["query_value"] == "tolkien"


def test_list_logs_tenant_isolation(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    _seed_log(db, t2["id"])
    resp = client.get("/api/v1/ingestion-logs", headers=_auth(t1["api_key"]))
    assert resp.json()["total"] == 0


def test_list_logs_includes_all_fields(client, db):
    t = _create_tenant(client)
    _seed_log(db, t["id"])
    resp = client.get("/api/v1/ingestion-logs", headers=_auth(t["api_key"]))
    item = resp.json()["items"][0]
    for field in ("id", "status", "query_type", "query_value", "fetched_count",
                  "succeeded_count", "failed_count", "started_at"):
        assert field in item


def test_list_logs_pagination(client, db):
    t = _create_tenant(client)
    for _ in range(5):
        _seed_log(db, t["id"])
    resp = client.get("/api/v1/ingestion-logs?page=1&page_size=3", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3


def test_list_logs_requires_auth(client):
    resp = client.get("/api/v1/ingestion-logs")
    assert resp.status_code in (401, 422)


# ---------------------------------------------------------------------------
# GET /api/v1/ingestion-logs/{log_id} (TASK-026)
# ---------------------------------------------------------------------------


def test_get_log_returns_200(client, db):
    t = _create_tenant(client)
    log = _seed_log(db, t["id"], status="completed")
    resp = client.get(f"/api/v1/ingestion-logs/{log.id}", headers=_auth(t["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_get_log_returns_all_fields(client, db):
    t = _create_tenant(client)
    log = _seed_log(db, t["id"])
    resp = client.get(f"/api/v1/ingestion-logs/{log.id}", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["id"] == log.id
    assert data["query_type"] == "author"
    assert data["query_value"] == "tolkien"
    assert "error_details" in data
    assert "finished_at" in data


def test_get_log_not_found_returns_404(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/ingestion-logs/00000000-0000-0000-0000-000000000000",
                      headers=_auth(t["api_key"]))
    assert resp.status_code == 404


def test_get_log_other_tenant_returns_404(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    log = _seed_log(db, t2["id"])
    resp = client.get(f"/api/v1/ingestion-logs/{log.id}", headers=_auth(t1["api_key"]))
    assert resp.status_code == 404


def test_get_log_running_status(client, db):
    t = _create_tenant(client)
    log = _seed_log(db, t["id"], status="running")
    resp = client.get(f"/api/v1/ingestion-logs/{log.id}", headers=_auth(t["api_key"]))
    assert resp.json()["status"] == "running"
