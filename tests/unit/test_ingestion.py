"""Tests for app/services/ingestion.py (TASK-015, TASK-016)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.ingestion_log import IngestionLog
from app.models.tenant import Tenant
from app.models.work import Work
from app.services.ingestion import ingest_single_work, run_ingestion
from app.services.ol_client import OLClientError


@pytest.fixture()
def tenant(db):
    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def log(db, tenant):
    entry = IngestionLog(
        tenant_id=tenant.id,
        query_type="author",
        query_value="Tolkien",
        status="pending",
    )
    db.add(entry)
    db.commit()
    return entry


def _make_raw_work(key="/works/OL1W", title="Dune", author_keys=None, cover_i=None):
    return {
        "key": key,
        "title": title,
        "author_key": author_keys or ["OL1A"],
        "first_publish_year": 1965,
        "subject": ["science fiction"],
        "cover_i": cover_i,
    }


def _mock_ol_client(author_name="Frank Herbert", fail_author_keys=None):
    """Return a mock OLClient where get_author succeeds unless the key is in fail_author_keys."""
    fail_author_keys = fail_author_keys or []

    async def get_author(key):
        if key in fail_author_keys:
            raise OLClientError(f"Failed to fetch {key}")
        return {"name": author_name}

    client = MagicMock()
    client.get_author = get_author
    client.search_works_by_author = AsyncMock(return_value=[])
    client.search_works_by_subject = AsyncMock(return_value=[])
    return client


# ---------------------------------------------------------------------------
# TASK-015 — ingest_single_work
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_single_work_success(db, tenant):
    """Successful ingestion inserts a Work row and returns status=success."""
    client = _mock_ol_client(author_name="Frank Herbert")
    raw = _make_raw_work()

    result = await ingest_single_work(db, client, tenant.id, raw)

    assert result["status"] == "success"
    assert result["ol_work_key"] == "/works/OL1W"
    assert db.query(Work).filter_by(tenant_id=tenant.id).count() == 1


@pytest.mark.asyncio
async def test_ingest_single_work_resolves_author_names(db, tenant):
    """Author keys are resolved to names and stored in author_names."""
    client = _mock_ol_client(author_name="Isaac Asimov")
    raw = _make_raw_work(author_keys=["OL1A", "OL2A"])

    await ingest_single_work(db, client, tenant.id, raw)

    w = db.query(Work).filter_by(tenant_id=tenant.id).one()
    assert w.author_names == ["Isaac Asimov", "Isaac Asimov"]


@pytest.mark.asyncio
async def test_ingest_single_work_author_error_falls_back_to_unknown(db, tenant):
    """OLClientError during author resolution stores 'Unknown' instead of raising."""
    client = _mock_ol_client(fail_author_keys=["OL1A"])
    raw = _make_raw_work(author_keys=["OL1A"])

    result = await ingest_single_work(db, client, tenant.id, raw)

    assert result["status"] == "success"
    w = db.query(Work).filter_by(tenant_id=tenant.id).one()
    assert w.author_names == ["Unknown"]


@pytest.mark.asyncio
async def test_ingest_single_work_builds_cover_url(db, tenant):
    """cover_i is converted to a CDN URL and stored."""
    client = _mock_ol_client()
    raw = _make_raw_work(cover_i=14625765)

    await ingest_single_work(db, client, tenant.id, raw)

    w = db.query(Work).filter_by(tenant_id=tenant.id).one()
    assert w.cover_image_url == "https://covers.openlibrary.org/b/id/14625765-M.jpg"


@pytest.mark.asyncio
async def test_ingest_single_work_no_cover_i_stores_none(db, tenant):
    """None cover_i results in None cover_image_url."""
    client = _mock_ol_client()
    raw = _make_raw_work(cover_i=None)

    await ingest_single_work(db, client, tenant.id, raw)

    w = db.query(Work).filter_by(tenant_id=tenant.id).one()
    assert w.cover_image_url is None


@pytest.mark.asyncio
async def test_ingest_single_work_returns_failed_on_unexpected_error(db, tenant):
    """An unexpected exception returns status=failed with an error message."""
    client = MagicMock()
    client.get_author = AsyncMock(side_effect=RuntimeError("unexpected"))

    result = await ingest_single_work(db, client, tenant.id, _make_raw_work())

    assert result["status"] == "failed"
    assert "unexpected" in result["error"]


@pytest.mark.asyncio
async def test_ingest_single_work_multiple_authors(db, tenant):
    """Multiple author keys each trigger a get_author call."""
    calls = []

    async def get_author(key):
        calls.append(key)
        return {"name": f"Author-{key}"}

    client = MagicMock()
    client.get_author = get_author
    raw = _make_raw_work(author_keys=["OL1A", "OL2A", "OL3A"])

    await ingest_single_work(db, client, tenant.id, raw)

    assert calls == ["OL1A", "OL2A", "OL3A"]
    w = db.query(Work).filter_by(tenant_id=tenant.id).one()
    assert len(w.author_names) == 3


# ---------------------------------------------------------------------------
# TASK-016 — run_ingestion
# ---------------------------------------------------------------------------

def _page(works: list[dict]):
    """Return an AsyncMock that yields works once then empty."""
    return AsyncMock(side_effect=[works, []])


@pytest.mark.asyncio
async def test_run_ingestion_marks_log_running_then_completed(db, tenant, log):
    """run_ingestion sets status=running during execution, completed on success."""
    client = _mock_ol_client()
    client.search_works_by_author = _page([_make_raw_work()])

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    assert log.status == "completed"
    assert log.finished_at is not None


@pytest.mark.asyncio
async def test_run_ingestion_counts_successes(db, tenant, log):
    """fetched_count and succeeded_count reflect the number of works ingested."""
    client = _mock_ol_client()
    works = [_make_raw_work(key=f"/works/OL{i}W") for i in range(3)]
    client.search_works_by_author = _page(works)

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    assert log.fetched_count == 3
    assert log.succeeded_count == 3
    assert log.failed_count == 0


@pytest.mark.asyncio
async def test_run_ingestion_counts_failures_without_aborting(db, tenant, log):
    """A failing work increments failed_count but does not abort the rest of the batch."""
    call_count = 0

    async def get_author(key):
        nonlocal call_count
        call_count += 1
        raise OLClientError("boom")

    client = MagicMock()
    client.get_author = get_author
    works = [_make_raw_work(key=f"/works/OL{i}W") for i in range(3)]
    client.search_works_by_author = _page(works)

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    # All 3 works attempted; author resolution fails → "Unknown" stored → still "success"
    assert log.fetched_count == 3
    assert log.status == "completed"


@pytest.mark.asyncio
async def test_run_ingestion_two_pages(db, tenant, log):
    """Two full pages of results are both fetched and ingested.

    Pages must be exactly _PAGE_SIZE (50) to avoid the early-stop condition
    (len(works) < limit). The third call returns [] to signal end of results.
    """
    page1 = [_make_raw_work(key=f"/works/OL{i}W") for i in range(50)]
    page2 = [_make_raw_work(key=f"/works/OL{i}W") for i in range(50, 100)]

    client = _mock_ol_client()
    client.search_works_by_author = AsyncMock(side_effect=[page1, page2, []])

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    assert log.fetched_count == 100
    assert log.succeeded_count == 100
    assert db.query(Work).filter_by(tenant_id=tenant.id).count() == 100


@pytest.mark.asyncio
async def test_run_ingestion_stops_when_page_is_empty(db, tenant, log):
    """Ingestion stops as soon as OL returns an empty page."""
    client = _mock_ol_client()
    client.search_works_by_author = AsyncMock(return_value=[])

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    assert log.fetched_count == 0
    assert log.status == "completed"


@pytest.mark.asyncio
async def test_run_ingestion_stops_at_max_works(db, tenant, log):
    """Ingestion stops after accumulating 500 works even if more pages exist."""
    # Simulate a large dataset: always returns a full page
    big_page = [_make_raw_work(key=f"/works/OL{i}W") for i in range(50)]
    client = _mock_ol_client()
    client.search_works_by_author = AsyncMock(return_value=big_page)

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    assert log.fetched_count == 500


@pytest.mark.asyncio
async def test_run_ingestion_subject_query_calls_subject_search(db, tenant, log):
    """query_type='subject' dispatches to search_works_by_subject."""
    log.query_type = "subject"
    log.query_value = "fantasy"
    db.commit()

    client = _mock_ol_client()
    client.search_works_by_subject = _page([_make_raw_work()])

    await run_ingestion(db, client, tenant.id, "subject", "fantasy", log.id)

    client.search_works_by_subject.assert_called()
    db.refresh(log)
    assert log.status == "completed"


@pytest.mark.asyncio
async def test_run_ingestion_marks_failed_on_search_error(db, tenant, log):
    """An exception from the search call marks the log as failed."""
    client = _mock_ol_client()
    client.search_works_by_author = AsyncMock(side_effect=RuntimeError("OL is down"))

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.refresh(log)
    assert log.status == "failed"
    assert "OL is down" in log.error_details
    assert log.finished_at is not None


@pytest.mark.asyncio
async def test_run_ingestion_log_counts_update_after_each_page(db, tenant, log):
    """Log counts are persisted progressively after each page.

    Both pages must be full (_PAGE_SIZE=50) so the loop doesn't early-stop.
    """
    snapshots = []
    original_commit = db.commit

    page1 = [_make_raw_work(key=f"/works/OL{i}W") for i in range(50)]
    page2 = [_make_raw_work(key=f"/works/OL{i}W") for i in range(50, 100)]

    def tracking_commit():
        original_commit()
        refreshed = db.query(IngestionLog).filter_by(id=log.id).one()
        if refreshed.status == "running":
            snapshots.append(refreshed.fetched_count)

    db.commit = tracking_commit

    client = _mock_ol_client()
    client.search_works_by_author = AsyncMock(side_effect=[page1, page2, []])

    await run_ingestion(db, client, tenant.id, "author", "tolkien", log.id)

    db.commit = original_commit
    db.refresh(log)
    assert log.fetched_count == 100
    assert 50 in snapshots   # snapshot after page 1
    assert 100 in snapshots  # snapshot after page 2
