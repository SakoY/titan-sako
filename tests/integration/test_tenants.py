"""Integration tests for tenant management endpoints (TASK-018) and auth dependency (TASK-017)."""

from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.core.security import hash_pii
from app.models.tenant import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_tenant(client, name="acme") -> dict:
    resp = client.post("/api/v1/admin/tenants", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/v1/admin/tenants — create tenant (TASK-018)
# ---------------------------------------------------------------------------


def test_create_tenant_returns_201(client):
    resp = client.post("/api/v1/admin/tenants", json={"name": "acme"})
    assert resp.status_code == 201


def test_create_tenant_returns_id_name_created_at(client):
    resp = client.post("/api/v1/admin/tenants", json={"name": "acme"})
    data = resp.json()
    assert "id" in data
    assert data["name"] == "acme"
    assert "created_at" in data


def test_create_tenant_returns_plaintext_api_key(client):
    data = _create_tenant(client)
    assert "api_key" in data
    assert len(data["api_key"]) >= 43  # token_urlsafe(32)


def test_create_tenant_stores_hashed_key_not_plaintext(client, db):
    data = _create_tenant(client)
    plaintext = data["api_key"]
    tenant = db.query(Tenant).filter_by(name="acme").first()
    assert tenant is not None
    assert tenant.api_key != plaintext
    expected_hash = hash_pii(plaintext, settings.SECRET_KEY)
    assert tenant.api_key == expected_hash


def test_create_tenant_duplicate_name_returns_409(client):
    _create_tenant(client, "acme")
    resp = client.post("/api/v1/admin/tenants", json={"name": "acme"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_create_tenant_no_auth_required(client):
    # No X-API-Key header — should still succeed
    resp = client.post("/api/v1/admin/tenants", json={"name": "open"})
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /api/v1/admin/tenants — list tenants (TASK-018)
# ---------------------------------------------------------------------------


def test_list_tenants_empty(client):
    resp = client.get("/api/v1/admin/tenants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_tenants_returns_created_tenants(client):
    _create_tenant(client, "alpha")
    _create_tenant(client, "beta")
    resp = client.get("/api/v1/admin/tenants")
    names = [t["name"] for t in resp.json()]
    assert "alpha" in names
    assert "beta" in names


def test_list_tenants_does_not_expose_api_keys(client):
    _create_tenant(client, "acme")
    resp = client.get("/api/v1/admin/tenants")
    for t in resp.json():
        assert "api_key" not in t


def test_list_tenants_includes_id_and_created_at(client):
    _create_tenant(client, "acme")
    resp = client.get("/api/v1/admin/tenants")
    tenant = resp.json()[0]
    assert "id" in tenant
    assert "created_at" in tenant


# ---------------------------------------------------------------------------
# require_tenant auth dependency (TASK-017)
# ---------------------------------------------------------------------------


def test_ingest_endpoint_returns_4xx_without_api_key(client):
    # FastAPI returns 422 (validation) when required header is absent
    resp = client.post("/api/v1/ingest", json={"query_type": "author", "query_value": "tolkien"})
    assert resp.status_code in (401, 422)


def test_ingest_endpoint_returns_401_with_wrong_api_key(client):
    _create_tenant(client, "acme")
    resp = client.post(
        "/api/v1/ingest",
        json={"query_type": "author", "query_value": "tolkien"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_ingest_endpoint_accepts_valid_api_key(client):
    data = _create_tenant(client, "acme")
    with patch("app.api.v1.ingestion.run_ingestion", new=AsyncMock()):
        resp = client.post(
            "/api/v1/ingest",
            json={"query_type": "author", "query_value": "tolkien"},
            headers={"X-API-Key": data["api_key"]},
        )
    assert resp.status_code == 202


def test_auth_returns_401_detail_message(client):
    resp = client.post(
        "/api/v1/ingest",
        json={"query_type": "author", "query_value": "tolkien"},
        headers={"X-API-Key": "bad"},
    )
    assert "Invalid" in resp.json()["detail"] or "missing" in resp.json()["detail"]
