"""Live integration tests for OLClient (TASK-010, TASK-011, TASK-012).

These tests make real HTTP calls to the Open Library API.
They verify that the actual OL response shapes are correctly parsed end-to-end.
"""

import pytest

from app.services.ol_client import OLClient, OLNotFoundError

pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def ol_client():
    client = OLClient()
    yield client
    await client.aclose()


# ---------------------------------------------------------------------------
# TASK-010 — Author search against live OL
# ---------------------------------------------------------------------------

async def test_live_author_search_returns_results(ol_client):
    """Live author search for a well-known author returns ≥1 result."""
    results = await ol_client.search_works_by_author("tolkien", limit=5)
    assert len(results) >= 1


async def test_live_author_search_result_has_non_null_key(ol_client):
    """Every result from a live author search has a non-null key."""
    results = await ol_client.search_works_by_author("tolkien", limit=5)
    for w in results:
        assert w["key"], f"Work missing key: {w}"


async def test_live_author_search_fields_match_expected_schema(ol_client):
    """Live author search results contain all expected normalised fields."""
    results = await ol_client.search_works_by_author("tolkien", limit=3)
    expected_keys = {"key", "title", "author_key", "first_publish_year", "subject", "cover_i"}
    for w in results:
        assert set(w.keys()) == expected_keys, f"Unexpected fields: {set(w.keys())}"


async def test_live_author_search_author_key_is_list(ol_client):
    """author_key is always a list (never None or a string)."""
    results = await ol_client.search_works_by_author("tolkien", limit=10)
    for w in results:
        assert isinstance(w["author_key"], list), f"author_key is not a list: {w}"


async def test_live_author_search_subject_is_list(ol_client):
    """subject is always a list (never None)."""
    results = await ol_client.search_works_by_author("tolkien", limit=10)
    for w in results:
        assert isinstance(w["subject"], list), f"subject is not a list: {w}"


async def test_live_author_search_missing_optional_fields_do_not_raise(ol_client):
    """A large author search batch parses without raising even with missing optional fields."""
    results = await ol_client.search_works_by_author("tolkien", limit=50)
    assert len(results) >= 1  # just confirm it ran without raising


# ---------------------------------------------------------------------------
# TASK-011 — Subject search against live OL
# ---------------------------------------------------------------------------

async def test_live_subject_search_returns_results(ol_client):
    """Live subject search returns ≥1 result for a well-known subject."""
    results = await ol_client.search_works_by_subject("science fiction", limit=5)
    assert len(results) >= 1


async def test_live_subject_search_result_has_non_null_key(ol_client):
    """Every result from a live subject search has a non-null key."""
    results = await ol_client.search_works_by_subject("science fiction", limit=5)
    for w in results:
        assert w["key"], f"Work missing key: {w}"


async def test_live_subject_search_fields_match_author_search_schema(ol_client):
    """Subject search results have the same field set as author search results."""
    results = await ol_client.search_works_by_subject("fantasy", limit=3)
    expected_keys = {"key", "title", "author_key", "first_publish_year", "subject", "cover_i"}
    for w in results:
        assert set(w.keys()) == expected_keys, f"Field mismatch: {set(w.keys())}"


async def test_live_subject_search_author_key_is_list(ol_client):
    """author_key from subject search is always a list of /authors/ paths."""
    results = await ol_client.search_works_by_subject("fiction", limit=5)
    for w in results:
        assert isinstance(w["author_key"], list)


async def test_live_subject_search_author_keys_are_full_paths(ol_client):
    """author_key entries from subject search are full /authors/... paths (not bare OLIDs)."""
    results = await ol_client.search_works_by_subject("fiction", limit=5)
    for w in results:
        for key in w["author_key"]:
            assert key.startswith("/authors/"), f"Expected full path, got: {key}"


# ---------------------------------------------------------------------------
# TASK-012 — Author detail resolution against live OL
# ---------------------------------------------------------------------------

async def test_live_get_author_by_bare_olid(ol_client):
    """get_author with a bare OLID (from author search) returns a non-empty name."""
    result = await ol_client.get_author("OL26320A")
    assert result["name"]
    assert result["name"] != "Unknown"


async def test_live_get_author_by_full_path(ol_client):
    """get_author with a full /authors/... path (from subject search) returns the correct name."""
    result = await ol_client.get_author("/authors/OL22098A")
    assert result["name"]
    assert result["name"] != "Unknown"


async def test_live_get_author_consistent_across_key_formats(ol_client):
    """Bare OLID and full path for the same author return the same name."""
    bare = await ol_client.get_author("OL26320A")
    full = await ol_client.get_author("/authors/OL26320A")
    assert bare["name"] == full["name"]


async def test_live_get_author_fake_key_raises_not_found(ol_client):
    """A fabricated author key returns OLNotFoundError."""
    with pytest.raises(OLNotFoundError):
        await ol_client.get_author("OLxxxxxxFAKEKEY")
