"""Integration tests for works retrieval endpoints (TASK-020, 021, 022, 023)."""

import pytest

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


def _seed_work(db, tenant_id, key, title="Dune", author_names=None, subjects=None, year=1965):
    w = Work(
        tenant_id=tenant_id,
        ol_work_key=key,
        title=title,
        author_names=author_names or ["Frank Herbert"],
        first_publish_year=year,
        subjects=subjects or ["science fiction"],
        cover_image_url=None,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


# ---------------------------------------------------------------------------
# GET /api/v1/works — list + pagination (TASK-020)
# ---------------------------------------------------------------------------


def test_list_works_empty(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/works", headers=_auth(t["api_key"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_list_works_returns_correct_fields(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", title="Dune", author_names=["Frank Herbert"], year=1965)
    resp = client.get("/api/v1/works", headers=_auth(t["api_key"]))
    item = resp.json()["items"][0]
    assert item["title"] == "Dune"
    assert item["author_names"] == ["Frank Herbert"]
    assert item["first_publish_year"] == 1965
    assert "id" in item
    assert "ol_work_key" in item


def test_list_works_pagination_page1(client, db):
    t = _create_tenant(client)
    for i in range(25):
        _seed_work(db, t["id"], f"/works/OL{i}W", title=f"Book {i}")
    resp = client.get("/api/v1/works?page=1&page_size=20", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["total"] == 25
    assert len(data["items"]) == 20
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_list_works_pagination_page2(client, db):
    t = _create_tenant(client)
    for i in range(25):
        _seed_work(db, t["id"], f"/works/OL{i}W", title=f"Book {i}")
    resp = client.get("/api/v1/works?page=2&page_size=20", headers=_auth(t["api_key"]))
    data = resp.json()
    assert len(data["items"]) == 5


def test_list_works_page_size_over_100_returns_422(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/works?page_size=101", headers=_auth(t["api_key"]))
    assert resp.status_code == 422


def test_list_works_tenant_isolation(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    _seed_work(db, t1["id"], "/works/OL1W")
    _seed_work(db, t2["id"], "/works/OL2W")
    resp = client.get("/api/v1/works", headers=_auth(t1["api_key"]))
    assert resp.json()["total"] == 1


def test_list_works_requires_auth(client):
    resp = client.get("/api/v1/works")
    assert resp.status_code in (401, 422)


# ---------------------------------------------------------------------------
# GET /api/v1/works — filters (TASK-021)
# ---------------------------------------------------------------------------


def test_filter_by_author(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", author_names=["Tolkien"])
    _seed_work(db, t["id"], "/works/OL2W", author_names=["Herbert"])
    resp = client.get("/api/v1/works?author=tolkien", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["author_names"] == ["Tolkien"]


def test_filter_by_subject(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", subjects=["fantasy"])
    _seed_work(db, t["id"], "/works/OL2W", subjects=["science fiction"])
    resp = client.get("/api/v1/works?subject=fantasy", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 1


def test_filter_by_year_from(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", year=1950)
    _seed_work(db, t["id"], "/works/OL2W", year=2000)
    resp = client.get("/api/v1/works?year_from=1990", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 1


def test_filter_by_year_to(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", year=1950)
    _seed_work(db, t["id"], "/works/OL2W", year=2000)
    resp = client.get("/api/v1/works?year_to=1960", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 1


def test_filter_combined_author_and_year(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", author_names=["Tolkien"], year=1954)
    _seed_work(db, t["id"], "/works/OL2W", author_names=["Tolkien"], year=1990)
    _seed_work(db, t["id"], "/works/OL3W", author_names=["Herbert"], year=1954)
    resp = client.get("/api/v1/works?author=tolkien&year_to=1960", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 1


def test_filter_cannot_see_other_tenant_works(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    _seed_work(db, t2["id"], "/works/OL1W", author_names=["Tolkien"])
    resp = client.get("/api/v1/works?author=tolkien", headers=_auth(t1["api_key"]))
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/works/search (TASK-022)
# ---------------------------------------------------------------------------


def test_search_by_title_substring(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", title="The Fellowship of the Ring")
    _seed_work(db, t["id"], "/works/OL2W", title="Dune")
    resp = client.get("/api/v1/works/search?q=fellowship", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "The Fellowship of the Ring"


def test_search_by_author_name(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", author_names=["J.R.R. Tolkien"])
    _seed_work(db, t["id"], "/works/OL2W", author_names=["Frank Herbert"])
    resp = client.get("/api/v1/works/search?q=Tolkien", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 1


def test_search_no_matches_returns_empty(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", title="Dune")
    resp = client.get("/api/v1/works/search?q=zzznomatch", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_search_case_insensitive(client, db):
    t = _create_tenant(client)
    _seed_work(db, t["id"], "/works/OL1W", title="Dune")
    resp = client.get("/api/v1/works/search?q=DUNE", headers=_auth(t["api_key"]))
    assert resp.json()["total"] == 1


def test_search_without_q_returns_422(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/works/search", headers=_auth(t["api_key"]))
    assert resp.status_code == 422


def test_search_tenant_isolation(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    _seed_work(db, t2["id"], "/works/OL1W", title="Dune")
    resp = client.get("/api/v1/works/search?q=dune", headers=_auth(t1["api_key"]))
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/works/{work_id} (TASK-023)
# ---------------------------------------------------------------------------


def test_get_work_returns_200(client, db):
    t = _create_tenant(client)
    w = _seed_work(db, t["id"], "/works/OL1W", title="Dune")
    resp = client.get(f"/api/v1/works/{w.id}", headers=_auth(t["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dune"


def test_get_work_returns_all_fields(client, db):
    t = _create_tenant(client)
    w = _seed_work(db, t["id"], "/works/OL1W", title="Dune", author_names=["Herbert"], subjects=["sci-fi"], year=1965)
    resp = client.get(f"/api/v1/works/{w.id}", headers=_auth(t["api_key"]))
    data = resp.json()
    assert data["ol_work_key"] == "/works/OL1W"
    assert data["author_names"] == ["Herbert"]
    assert data["subjects"] == ["sci-fi"]
    assert data["first_publish_year"] == 1965


def test_get_work_not_found_returns_404(client):
    t = _create_tenant(client)
    resp = client.get("/api/v1/works/00000000-0000-0000-0000-000000000000", headers=_auth(t["api_key"]))
    assert resp.status_code == 404


def test_get_work_other_tenant_returns_404(client, db):
    t1 = _create_tenant(client, "t1")
    t2 = _create_tenant(client, "t2")
    w = _seed_work(db, t2["id"], "/works/OL1W")
    resp = client.get(f"/api/v1/works/{w.id}", headers=_auth(t1["api_key"]))
    assert resp.status_code == 404
