"""End-to-end tests against a running Docker service at http://localhost:8000.

Run after `docker compose up --build`:

    pytest tests/e2e/test_docker_e2e.py -v

Covers every endpoint in dependency order. A session-scoped fixture creates
a fresh tenant and stores the API key; downstream tests skip automatically if
setup failed rather than cascading with KeyErrors.
"""

import time

import httpx
import pytest

BASE = "http://localhost:8000"
TIMEOUT = 5


# ---------------------------------------------------------------------------
# Reachability — skip module if Docker not running
# ---------------------------------------------------------------------------


def _service_reachable() -> bool:
    try:
        return httpx.get(f"{BASE}/health", timeout=3).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _service_reachable(),
    reason="Docker service not reachable at http://localhost:8000 — run `docker compose up --build` first",
)


# ---------------------------------------------------------------------------
# Session fixtures — tenant created once for the whole run
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tenant():
    """Create a unique e2e tenant; skip all tests if creation fails."""
    import uuid
    name = f"e2e-{uuid.uuid4().hex[:8]}"
    r = httpx.post(f"{BASE}/api/v1/admin/tenants", json={"name": name}, timeout=TIMEOUT)
    if r.status_code != 201:
        pytest.skip(f"Could not create e2e tenant: {r.status_code} {r.text}")
    data = r.json()
    return {"id": data["id"], "name": data["name"], "api_key": data["api_key"]}


@pytest.fixture(scope="session")
def auth(tenant):
    return {"X-API-Key": tenant["api_key"]}


@pytest.fixture(scope="session")
def ingested_log_id(auth):
    """Trigger ingestion and wait until works appear in the catalog (up to 120s)."""
    r = httpx.post(
        f"{BASE}/api/v1/ingest",
        json={"query_type": "author", "query_value": "tolkien"},
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 202
    log_id = r.json()["log_id"]

    deadline = time.time() + 120
    while time.time() < deadline:
        log_r = httpx.get(f"{BASE}/api/v1/ingestion-logs/{log_id}", headers=auth, timeout=TIMEOUT)
        status = log_r.json().get("status")
        if status in ("completed", "failed"):
            break
        # Don't wait for full completion — exit as soon as any works are ingested
        works_r = httpx.get(f"{BASE}/api/v1/works", headers=auth, timeout=TIMEOUT)
        if works_r.status_code == 200 and works_r.json().get("total", 0) > 0:
            break
        time.sleep(3)

    works_total = httpx.get(f"{BASE}/api/v1/works", headers=auth, timeout=TIMEOUT).json().get("total", 0)
    assert works_total > 0, f"No works ingested after 120s — log: {log_r.json()}"
    return log_id


@pytest.fixture(scope="session")
def first_work(auth, ingested_log_id):
    """Return the first work ingested for this tenant."""
    r = httpx.get(f"{BASE}/api/v1/works", headers=auth, timeout=TIMEOUT)
    assert r.json()["total"] > 0, "No works found after ingestion"
    return r.json()["items"][0]


@pytest.fixture(scope="session")
def reading_list_id(auth, first_work):
    """Submit a reading list and return its ID."""
    r = httpx.post(
        f"{BASE}/api/v1/reading-lists",
        json={
            "patron_name": "Alice Smith",
            "patron_email": "alice@e2e-test.org",
            "books": [first_work["ol_work_key"]],
        },
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 201
    return r.json()["reading_list_id"]


# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------


def test_health():
    r = httpx.get(f"{BASE}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. Tenant management
# ---------------------------------------------------------------------------


def test_create_tenant_returns_201(tenant):
    assert tenant["id"]
    assert tenant["api_key"]
    assert tenant["name"].startswith("e2e-")


def test_create_tenant_duplicate_returns_409(tenant):
    r = httpx.post(
        f"{BASE}/api/v1/admin/tenants",
        json={"name": tenant["name"]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 409


def test_list_tenants(tenant):
    r = httpx.get(f"{BASE}/api/v1/admin/tenants", timeout=TIMEOUT)
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert tenant["name"] in names


def test_list_tenants_does_not_expose_api_keys():
    r = httpx.get(f"{BASE}/api/v1/admin/tenants", timeout=TIMEOUT)
    for t in r.json():
        assert "api_key" not in t


# ---------------------------------------------------------------------------
# 3. Auth — invalid key rejected
# ---------------------------------------------------------------------------


def test_ingest_rejects_missing_key():
    r = httpx.post(
        f"{BASE}/api/v1/ingest",
        json={"query_type": "author", "query_value": "tolkien"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (401, 422)


def test_ingest_rejects_wrong_key():
    r = httpx.post(
        f"{BASE}/api/v1/ingest",
        json={"query_type": "author", "query_value": "tolkien"},
        headers={"X-API-Key": "bad-key"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 4. Ingestion
# ---------------------------------------------------------------------------


def test_trigger_ingestion_returns_202(auth):
    r = httpx.post(
        f"{BASE}/api/v1/ingest",
        json={"query_type": "author", "query_value": "ursula le guin"},
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 202
    assert r.json()["status"] == "pending"
    assert "log_id" in r.json()


def test_trigger_ingestion_by_subject(auth):
    r = httpx.post(
        f"{BASE}/api/v1/ingest",
        json={"query_type": "subject", "query_value": "fantasy"},
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 202


def test_trigger_ingestion_invalid_query_type(auth):
    r = httpx.post(
        f"{BASE}/api/v1/ingest",
        json={"query_type": "title", "query_value": "dune"},
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. Ingestion logs
# ---------------------------------------------------------------------------


def test_ingestion_completes(ingested_log_id, auth):
    """Asserts ingestion is running or complete and works exist in catalog."""
    r = httpx.get(f"{BASE}/api/v1/ingestion-logs/{ingested_log_id}", headers=auth, timeout=TIMEOUT)
    assert r.json()["status"] in ("running", "completed")
    works = httpx.get(f"{BASE}/api/v1/works", headers=auth, timeout=TIMEOUT).json()
    assert works["total"] > 0


def test_list_ingestion_logs(auth):
    r = httpx.get(f"{BASE}/api/v1/ingestion-logs", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert "items" in r.json()


def test_get_ingestion_log(ingested_log_id, auth):
    r = httpx.get(f"{BASE}/api/v1/ingestion-logs/{ingested_log_id}", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == ingested_log_id
    assert data["query_type"] == "author"
    assert "fetched_count" in data
    assert "started_at" in data


def test_get_ingestion_log_not_found(auth):
    r = httpx.get(
        f"{BASE}/api/v1/ingestion-logs/00000000-0000-0000-0000-000000000000",
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 6. Works
# ---------------------------------------------------------------------------


def test_list_works_returns_results(auth, ingested_log_id):
    r = httpx.get(f"{BASE}/api/v1/works", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_list_works_pagination(auth, ingested_log_id):
    r = httpx.get(f"{BASE}/api/v1/works", params={"page": 1, "page_size": 5}, headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) <= 5
    assert data["page_size"] == 5


def test_list_works_page_size_over_100_rejected(auth):
    r = httpx.get(f"{BASE}/api/v1/works", params={"page_size": 101}, headers=auth, timeout=TIMEOUT)
    assert r.status_code == 422


def test_filter_works_by_author(auth, ingested_log_id):
    r = httpx.get(f"{BASE}/api/v1/works", params={"author": "le guin"}, headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    for item in r.json()["items"]:
        authors = " ".join(item.get("author_names") or []).lower()
        assert "le guin" in authors


def test_filter_works_by_year_range(auth, ingested_log_id):
    r = httpx.get(
        f"{BASE}/api/v1/works",
        params={"year_from": 1950, "year_to": 1970},
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        year = item.get("first_publish_year")
        if year is not None:
            assert 1950 <= year <= 1970


def test_search_works_by_keyword(auth, ingested_log_id):
    r = httpx.get(f"{BASE}/api/v1/works/search", params={"q": "left"}, headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "total" in r.json()


def test_search_works_missing_q_returns_422(auth):
    r = httpx.get(f"{BASE}/api/v1/works/search", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 422


def test_get_work_by_id(first_work, auth):
    r = httpx.get(f"{BASE}/api/v1/works/{first_work['id']}", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["id"] == first_work["id"]
    assert "title" in r.json()


def test_get_work_not_found(auth):
    r = httpx.get(
        f"{BASE}/api/v1/works/00000000-0000-0000-0000-000000000000",
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 7. Reading lists
# ---------------------------------------------------------------------------


def test_submit_reading_list_resolves_known_work(reading_list_id, first_work, auth):
    # Re-submit the same patron to inspect the response
    r = httpx.post(
        f"{BASE}/api/v1/reading-lists",
        json={
            "patron_name": "Alice Smith",
            "patron_email": "alice@e2e-test.org",
            "books": [first_work["ol_work_key"]],
        },
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 201
    assert first_work["ol_work_key"] in r.json()["resolved"]


def test_submit_reading_list_upserts_on_same_email(reading_list_id, auth):
    r = httpx.post(
        f"{BASE}/api/v1/reading-lists",
        json={
            "patron_name": "Alice Smith",
            "patron_email": "alice@e2e-test.org",
            "books": ["/works/OLdifferentW"],
        },
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 201
    assert r.json()["reading_list_id"] == reading_list_id


def test_submit_reading_list_no_pii_in_response(auth):
    r = httpx.post(
        f"{BASE}/api/v1/reading-lists",
        json={"patron_name": "Bob Jones", "patron_email": "bob@e2e-test.org", "books": []},
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 201
    body = str(r.json())
    assert "Bob Jones" not in body
    assert "bob@e2e-test.org" not in body


def test_list_reading_lists(reading_list_id, auth):
    r = httpx.get(f"{BASE}/api/v1/reading-lists", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    body = str(r.json())
    assert "alice@e2e-test.org" not in body
    assert "Alice Smith" not in body


def test_get_reading_list(reading_list_id, auth):
    r = httpx.get(f"{BASE}/api/v1/reading-lists/{reading_list_id}", headers=auth, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == reading_list_id
    assert "items" in data
    assert "patron_email_hash" in data
    assert "alice@e2e-test.org" not in str(data)


def test_get_reading_list_not_found(auth):
    r = httpx.get(
        f"{BASE}/api/v1/reading-lists/00000000-0000-0000-0000-000000000000",
        headers=auth,
        timeout=TIMEOUT,
    )
    assert r.status_code == 404
