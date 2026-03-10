"""Unit tests for app/services/ol_client.py (TASK-009 through TASK-013).

These tests use httpx.MockTransport — zero live network calls.
They test: retry/error protocol, semaphore queuing, field normalisation, path construction.
Live integration tests are in tests/integration/test_ol_client.py.
"""

import asyncio
import json

import httpx
import pytest

from app.services.ol_client import (
    OLClient,
    OLClientError,
    OLNotFoundError,
    OLRateLimitError,
    build_cover_url,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_response(docs: list[dict], status: int = 200) -> httpx.Response:
    body = json.dumps({"docs": docs, "numFound": len(docs)}).encode()
    return httpx.Response(status, content=body)


def _subject_response(works: list[dict], status: int = 200) -> httpx.Response:
    body = json.dumps({"works": works, "work_count": len(works)}).encode()
    return httpx.Response(status, content=body)


def _author_response(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(data).encode())


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://openlibrary.org",
    )


# Real response shapes confirmed against live OL API

# /search.json doc (author search)
_SAMPLE_SEARCH_DOC = {
    "key": "/works/OL27448W",
    "title": "The Lord of the Rings",
    "author_key": ["OL26320A"],
    "first_publish_year": 1954,
    "subject": ["Fantasy fiction", "Fiction"],
    "cover_i": 14625765,
}

_MINIMAL_SEARCH_DOC = {"key": "/works/OL1W"}  # all optional fields absent

# /subjects/{subject}.json work entry (different shape from search)
_SAMPLE_SUBJECT_WORK = {
    "key": "/works/OL138052W",
    "title": "Alice's Adventures in Wonderland",
    "authors": [{"key": "/authors/OL22098A", "name": "Lewis Carroll"}],
    "first_publish_year": 1865,
    "subject": ["Fantasy fiction", "Children's literature"],
    "cover_id": 10527843,  # note: cover_id not cover_i
}

_MINIMAL_SUBJECT_WORK = {"key": "/works/OL2W"}  # all optional fields absent


# ---------------------------------------------------------------------------
# TASK-013 — build_cover_url (pure function)
# ---------------------------------------------------------------------------

def test_build_cover_url_known_id():
    assert build_cover_url(14625765) == "https://covers.openlibrary.org/b/id/14625765-M.jpg"


def test_build_cover_url_none_returns_none():
    assert build_cover_url(None) is None


def test_build_cover_url_zero():
    # 0 is a valid id per OL (they use -1 as sentinel, not 0)
    assert build_cover_url(0) == "https://covers.openlibrary.org/b/id/0-M.jpg"


# ---------------------------------------------------------------------------
# TASK-009 — HTTP error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_404_raises_not_found_immediately_no_retry():
    """404 raises OLNotFoundError after exactly 1 attempt (no retry)."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(404)

    client = OLClient(http_client=_mock_client(handler))
    with pytest.raises(OLNotFoundError):
        await client.get_author("OL99FAKE")

    assert call_count == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_429_retries_three_times_then_raises():
    """Three consecutive 429s exhaust retries and raise OLRateLimitError."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429)

    async def fast_sleep(_): pass

    client = OLClient(http_client=_mock_client(handler))
    with pytest.raises(OLRateLimitError):
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(asyncio, "sleep", fast_sleep)
            await client.get_author("OL1A")

    assert call_count == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_429_then_200_succeeds_on_second_attempt():
    """A single 429 followed by 200 succeeds without raising."""
    responses = [httpx.Response(429), _author_response({"name": "Tolkien"})]
    idx = 0

    def handler(request):
        nonlocal idx
        r = responses[idx]; idx += 1; return r

    async def fast_sleep(_): pass

    client = OLClient(http_client=_mock_client(handler))
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(asyncio, "sleep", fast_sleep)
        result = await client.get_author("OL26320A")

    assert result["name"] == "Tolkien"
    await client.aclose()


@pytest.mark.asyncio
async def test_5xx_retries_three_times_then_raises():
    """Three 503s exhaust retries and raise OLClientError."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(503)

    async def fast_sleep(_): pass

    client = OLClient(http_client=_mock_client(handler))
    with pytest.raises(OLClientError):
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(asyncio, "sleep", fast_sleep)
            await client.get_author("OL1A")

    assert call_count == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_unexpected_4xx_raises_immediately():
    """A 400 raises OLClientError without retry."""
    def handler(request):
        return httpx.Response(400)

    client = OLClient(http_client=_mock_client(handler))
    with pytest.raises(OLClientError):
        await client.get_author("OL1A")
    await client.aclose()


# ---------------------------------------------------------------------------
# TASK-009 — Semaphore concurrency limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semaphore_limits_concurrency_and_queues_excess():
    """Requests beyond semaphore limit are queued; all complete; max concurrency not exceeded."""
    concurrency_limit = 2
    active = 0
    max_active = 0
    completed = 0

    async def slow_handler(request):
        nonlocal active, max_active, completed
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        completed += 1
        return _search_response([_SAMPLE_SEARCH_DOC])

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(slow_handler),
        base_url="https://openlibrary.org",
    )
    client = OLClient(http_client=http_client)
    client._semaphore = asyncio.Semaphore(concurrency_limit)

    results = await asyncio.gather(*[client.search_works_by_author("tolkien") for _ in range(5)])

    assert completed == 5
    assert max_active <= concurrency_limit
    assert all(len(r) == 1 for r in results)
    await client.aclose()


# ---------------------------------------------------------------------------
# TASK-010 — Author search: /search.json response parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_by_author_parses_all_fields():
    """Author search correctly maps all fields from /search.json doc shape."""
    def handler(request):
        return _search_response([_SAMPLE_SEARCH_DOC])

    client = OLClient(http_client=_mock_client(handler))
    results = await client.search_works_by_author("tolkien", limit=1)

    w = results[0]
    assert w["key"] == "/works/OL27448W"
    assert w["title"] == "The Lord of the Rings"
    assert w["author_key"] == ["OL26320A"]
    assert w["first_publish_year"] == 1954
    assert w["subject"] == ["Fantasy fiction", "Fiction"]
    assert w["cover_i"] == 14625765
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_author_missing_fields_default_safely():
    """Missing optional fields in /search.json doc default to None/[] without raising."""
    def handler(request):
        return _search_response([_MINIMAL_SEARCH_DOC])

    client = OLClient(http_client=_mock_client(handler))
    w = (await client.search_works_by_author("nobody"))[0]

    assert w["title"] is None
    assert w["author_key"] == []
    assert w["first_publish_year"] is None
    assert w["subject"] == []
    assert w["cover_i"] is None
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_author_passes_limit_and_offset_params():
    """limit and offset are forwarded as query params to /search.json."""
    received = {}

    def handler(request):
        received.update(dict(request.url.params))
        return _search_response([])

    client = OLClient(http_client=_mock_client(handler))
    await client.search_works_by_author("tolkien", limit=25, offset=50)

    assert received["limit"] == "25"
    assert received["offset"] == "50"
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_author_empty_docs_returns_empty_list():
    def handler(request):
        return _search_response([])

    client = OLClient(http_client=_mock_client(handler))
    assert await client.search_works_by_author("nobody") == []
    await client.aclose()


# ---------------------------------------------------------------------------
# TASK-011 — Subject search: /subjects/{subject}.json response parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_by_subject_hits_subjects_endpoint():
    """/subjects/{subject}.json is called, not /search.json."""
    def handler(request):
        assert "/subjects/" in str(request.url)
        assert "/search.json" not in str(request.url)
        return _subject_response([_SAMPLE_SUBJECT_WORK])

    client = OLClient(http_client=_mock_client(handler))
    await client.search_works_by_subject("science fiction")
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_subject_slugifies_query():
    """Spaces in subject are converted to underscores in the URL path."""
    def handler(request):
        assert "science_fiction" in str(request.url)
        return _subject_response([])

    client = OLClient(http_client=_mock_client(handler))
    await client.search_works_by_subject("science fiction")
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_subject_parses_authors_and_cover_id():
    """/subjects/ works use authors[].key and cover_id — normalised to same shape as author search."""
    def handler(request):
        return _subject_response([_SAMPLE_SUBJECT_WORK])

    client = OLClient(http_client=_mock_client(handler))
    w = (await client.search_works_by_subject("fantasy"))[0]

    assert w["key"] == "/works/OL138052W"
    assert w["title"] == "Alice's Adventures in Wonderland"
    assert w["author_key"] == ["/authors/OL22098A"]
    assert w["first_publish_year"] == 1865
    assert w["cover_i"] == 10527843   # mapped from cover_id
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_subject_missing_fields_default_safely():
    """Missing optional fields in subject work default to None/[] without raising."""
    def handler(request):
        return _subject_response([_MINIMAL_SUBJECT_WORK])

    client = OLClient(http_client=_mock_client(handler))
    w = (await client.search_works_by_subject("fantasy"))[0]

    assert w["title"] is None
    assert w["author_key"] == []
    assert w["first_publish_year"] is None
    assert w["subject"] == []
    assert w["cover_i"] is None
    await client.aclose()


@pytest.mark.asyncio
async def test_search_by_subject_output_shape_matches_author_search():
    """Both search methods return dicts with the same set of keys."""
    def search_handler(request):
        return _search_response([_SAMPLE_SEARCH_DOC])

    def subject_handler(request):
        return _subject_response([_SAMPLE_SUBJECT_WORK])

    c1 = OLClient(http_client=_mock_client(search_handler))
    c2 = OLClient(http_client=_mock_client(subject_handler))

    author_result = (await c1.search_works_by_author("tolkien"))[0]
    subject_result = (await c2.search_works_by_subject("fantasy"))[0]

    assert set(author_result.keys()) == set(subject_result.keys())
    await c1.aclose()
    await c2.aclose()


# ---------------------------------------------------------------------------
# TASK-012 — Author detail: key path normalisation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_author_bare_olid_constructs_correct_path():
    """Bare OLID 'OL26320A' → /authors/OL26320A.json."""
    def handler(request):
        assert str(request.url).endswith("/authors/OL26320A.json")
        return _author_response({"name": "J.R.R. Tolkien"})

    client = OLClient(http_client=_mock_client(handler))
    assert (await client.get_author("OL26320A")) == {"name": "J.R.R. Tolkien"}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_author_path_prefix_appends_json_extension():
    """'/authors/OL26320A' (no .json, as returned by subjects endpoint) → appends .json."""
    def handler(request):
        assert str(request.url).endswith("/authors/OL26320A.json")
        return _author_response({"name": "J.R.R. Tolkien"})

    client = OLClient(http_client=_mock_client(handler))
    assert (await client.get_author("/authors/OL26320A"))["name"] == "J.R.R. Tolkien"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_author_missing_name_key_returns_unknown():
    """Response with no 'name' key returns {"name": "Unknown"}."""
    def handler(request):
        return _author_response({"bio": "some bio"})

    client = OLClient(http_client=_mock_client(handler))
    assert await client.get_author("OL1A") == {"name": "Unknown"}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_author_null_name_returns_unknown():
    """Response with null 'name' falls back to "Unknown"."""
    def handler(request):
        return _author_response({"name": None})

    client = OLClient(http_client=_mock_client(handler))
    assert await client.get_author("OL1A") == {"name": "Unknown"}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_author_404_raises_ol_not_found_error():
    def handler(request):
        return httpx.Response(404)

    client = OLClient(http_client=_mock_client(handler))
    with pytest.raises(OLNotFoundError):
        await client.get_author("OLxxxxxxFAKE")
    await client.aclose()
