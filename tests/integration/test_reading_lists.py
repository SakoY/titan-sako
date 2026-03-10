"""Integration tests for reading list endpoints (TASK-029, 030)."""

import pytest

from app.core.config import settings
from app.core.security import hash_pii
from app.models.reading_list import ReadingList, ReadingListItem
from app.models.work import Work


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_tenant(client, name="acme") -> dict:
    resp = client.post("/api/v1/admin/tenants", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def _seed_work(db, tenant_id, key, title="Dune"):
    w = Work(tenant_id=tenant_id, ol_work_key=key, title=title)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def _submit(client, tenant, patron_name="Alice", patron_email="alice@example.com", books=None):
    return client.post(
        "/api/v1/reading-lists",
        json={
            "patron_name": patron_name,
            "patron_email": patron_email,
            "books": books or [],
        },
        headers=_auth(tenant["api_key"]),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/reading-lists (TASK-029)
# ---------------------------------------------------------------------------


def test_submit_returns_201(client):
    t = _create_tenant(client)
    resp = _submit(client, t)
    assert resp.status_code == 201


def test_submit_returns_reading_list_id(client):
    t = _create_tenant(client)
    resp = _submit(client, t)
    assert "reading_list_id" in resp.json()


def test_submit_resolved_and_unresolved_books(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W")
    resp = _submit(client, t, books=["/works/OL1W", "/works/OLmissW"])
    data = resp.json()
    assert "/works/OL1W" in data["resolved"]
    assert "/works/OLmissW" in data["unresolved"]


def test_submit_stores_hashed_pii_not_plaintext(client, db):
    t = _create_tenant(client)
    _submit(client, t, patron_name="Alice Smith", patron_email="alice@example.com")
    rl = db.query(ReadingList).first()
    assert rl is not None
    assert "Alice" not in rl.patron_name_hash
    assert "alice" not in rl.patron_email_hash
    expected_email_hash = hash_pii("alice@example.com", settings.SECRET_KEY)
    assert rl.patron_email_hash == expected_email_hash


def test_submit_same_patron_email_upserts(client, db):
    t = _create_tenant(client)
    _submit(client, t, patron_email="alice@example.com", books=["/works/OL1W"])
    _submit(client, t, patron_email="alice@example.com", books=["/works/OL2W"])
    count = db.query(ReadingList).filter_by(tenant_id=t["id"]).count()
    assert count == 1


def test_submit_upsert_replaces_items(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W")
    _seed_work(db, t["id"], "/works/OL2W")
    _submit(client, t, patron_email="alice@example.com", books=["/works/OL1W"])
    _submit(client, t, patron_email="alice@example.com", books=["/works/OL2W"])
    rl = db.query(ReadingList).filter_by(tenant_id=t["id"]).first()
    items = db.query(ReadingListItem).filter_by(reading_list_id=rl.id).all()
    assert len(items) == 1
    assert items[0].book_reference == "/works/OL2W"


def test_submit_requires_auth(client):
    resp = client.post("/api/v1/reading-lists", json={
        "patron_name": "Alice", "patron_email": "a@b.com", "books": []
    })
    assert resp.status_code in (401, 422)


def test_submit_no_plaintext_pii_in_db(client, db):
    t = _create_tenant(client)
    _submit(client, t, patron_name="SecretName", patron_email="secret@email.com")
    # Check every ReadingList column for plaintext
    rl = db.query(ReadingList).first()
    assert "SecretName" not in str(rl.patron_name_hash)
    assert "secret@email.com" not in str(rl.patron_email_hash)


def test_submit_tenant_isolation(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    _submit(client, t1)
    count_t2 = db.query(ReadingList).filter_by(tenant_id=t2["id"]).count()
    assert count_t2 == 0


# ---------------------------------------------------------------------------
# GET /api/v1/reading-lists (TASK-030)
# ---------------------------------------------------------------------------


def test_list_reading_lists_empty(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/reading-lists", headers=_auth(t["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_reading_lists_returns_submitted(client):
    t = _create_tenant(client)
    _submit(client, t, patron_email="alice@example.com")
    _submit(client, t, patron_email="bob@example.com")
    resp = client.get("/api/v1/reading-lists", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 2


def test_list_reading_lists_no_plaintext_pii(client):
    t = _create_tenant(client)
    _submit(client, t, patron_name="Alice", patron_email="alice@example.com")
    resp = client.get("/api/v1/reading-lists", headers=_auth(t["api_key"]))
    item = resp.json()["items"][0]
    assert "Alice" not in str(item)
    assert "alice@example.com" not in str(item)
    assert "patron_name_hash" in item
    assert "patron_email_hash" in item


def test_list_reading_lists_includes_item_count(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W")
    _seed_work(db, t["id"], "/works/OL2W")
    _submit(client, t, books=["/works/OL1W", "/works/OL2W"])
    resp = client.get("/api/v1/reading-lists", headers=_auth(t["api_key"]))
    assert resp.json()["items"][0]["item_count"] == 2


def test_list_reading_lists_tenant_isolation(client):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    _submit(client, t2)
    resp = client.get("/api/v1/reading-lists", headers=_auth(t1["api_key"]))
    assert resp.json()["total"] == 0


def test_list_reading_lists_pagination(client):
    t = _create_tenant(client)
    for i in range(5):
        _submit(client, t, patron_email=f"patron{i}@example.com")
    resp = client.get("/api/v1/reading-lists?page=1&page_size=3", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3


# ---------------------------------------------------------------------------
# GET /api/v1/reading-lists/{id} (TASK-030)
# ---------------------------------------------------------------------------


def test_get_reading_list_returns_200(client):
    t = _create_tenant(client)
    submitted = _submit(client, t).json()
    rl_id = submitted["reading_list_id"]
    resp = client.get(f"/api/v1/reading-lists/{rl_id}", headers=_auth(t["api_key"]))
    assert resp.status_code == 200


def test_get_reading_list_returns_items(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W")
    submitted = _submit(client, t, books=["/works/OL1W", "/works/OLmissW"]).json()
    rl_id = submitted["reading_list_id"]
    resp = client.get(f"/api/v1/reading-lists/{rl_id}", headers=_auth(t["api_key"]))
    data = resp.json()
    assert len(data["items"]) == 2
    statuses = {item["book_reference"]: item["resolution_status"] for item in data["items"]}
    assert statuses["/works/OL1W"] == "resolved"
    assert statuses["/works/OLmissW"] == "unresolved"


def test_get_reading_list_not_found_returns_404(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/reading-lists/00000000-0000-0000-0000-000000000000",
                      headers=_auth(t["api_key"]))
    assert resp.status_code == 404


def test_get_reading_list_other_tenant_returns_404(client):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    submitted = _submit(client, t2).json()
    rl_id = submitted["reading_list_id"]
    resp = client.get(f"/api/v1/reading-lists/{rl_id}", headers=_auth(t1["api_key"]))
    assert resp.status_code == 404


def test_get_reading_list_no_plaintext_pii(client):
    t = _create_tenant(client)
    submitted = _submit(client, t, patron_name="Alice", patron_email="alice@example.com").json()
    rl_id = submitted["reading_list_id"]
    resp = client.get(f"/api/v1/reading-lists/{rl_id}", headers=_auth(t["api_key"]))
    data = str(resp.json())
    assert "Alice" not in data
    assert "alice@example.com" not in data
