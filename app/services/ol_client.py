"""Open Library API client with rate limiting and retry logic."""

import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fields requested from OL search endpoint (author search)
_SEARCH_FIELDS = "key,title,author_key,first_publish_year,subject,cover_i"


class OLClientError(Exception):
    """Base exception for OL client errors."""


class OLNotFoundError(OLClientError):
    """Raised when OL returns 404."""


class OLRateLimitError(OLClientError):
    """Raised when OL returns 429 and retries are exhausted."""


def build_cover_url(cover_id: int | None) -> str | None:
    """Convert an OL cover_i integer to the CDN URL. Returns None if cover_id is None."""
    if cover_id is None:
        return None
    return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


def _parse_search_work(raw: dict) -> dict:
    """
    Normalise a doc from /search.json (author search).
    Returns: key, title, author_key (list of bare OLIDs), first_publish_year, subject, cover_i.
    """
    return {
        "key": raw.get("key"),
        "title": raw.get("title"),
        "author_key": raw.get("author_key") or [],
        "first_publish_year": raw.get("first_publish_year"),
        "subject": raw.get("subject") or [],
        "cover_i": raw.get("cover_i"),
    }


def _parse_subject_work(raw: dict) -> dict:
    """
    Normalise a work entry from /subjects/{subject}.json.
    The shape differs from /search.json:
      - authors is a list of {key: "/authors/OL...", name: "..."}
      - cover field is cover_id (not cover_i)
    Returns the same normalised shape as _parse_search_work for uniform downstream use.
    """
    author_keys = [a["key"] for a in raw.get("authors") or [] if "key" in a]
    return {
        "key": raw.get("key"),
        "title": raw.get("title"),
        "author_key": author_keys,
        "first_publish_year": raw.get("first_publish_year"),
        "subject": raw.get("subject") or [],
        "cover_i": raw.get("cover_id"),  # subjects endpoint uses cover_id
    }


class OLClient:
    """Async HTTP client for the Open Library API."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.OL_BASE_URL,
            timeout=10.0,
        )
        self._semaphore = asyncio.Semaphore(settings.OL_MAX_CONCURRENT_REQUESTS)

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """
        Execute a GET request with exponential backoff retry on 429 / 5xx.
        Raises OLNotFoundError on 404, OLRateLimitError if retries exhausted on 429.
        """
        max_retries = 3
        delay = 1.0

        async with self._semaphore:
            for attempt in range(max_retries):
                response = await self._client.get(path, params=params)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 404:
                    raise OLNotFoundError(f"Not found: {path}")

                if response.status_code == 429:
                    if attempt == max_retries - 1:
                        raise OLRateLimitError(f"Rate limited after {max_retries} retries: {path}")
                    logger.warning("OL rate limit hit, retrying in %.1fs (attempt %d)", delay, attempt + 1)
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                if response.status_code >= 500:
                    if attempt == max_retries - 1:
                        raise OLClientError(f"OL server error {response.status_code} after {max_retries} retries: {path}")
                    logger.warning("OL server error %d, retrying in %.1fs (attempt %d)", response.status_code, delay, attempt + 1)
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                raise OLClientError(f"Unexpected status {response.status_code}: {path}")

        # Should never reach here
        raise OLClientError(f"Request failed after {max_retries} retries: {path}")

    async def search_works_by_author(self, author: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        Fetch works by author name via GET /search.json?author=...
        Returns a normalised list of work dicts.
        """
        data = await self._get(
            "/search.json",
            params={"author": author, "limit": limit, "offset": offset, "fields": _SEARCH_FIELDS},
        )
        return [_parse_search_work(doc) for doc in data.get("docs", [])]

    async def search_works_by_subject(self, subject: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        Fetch works by subject via GET /subjects/{subject}.json (OpenAPI spec endpoint).
        Subject must be slug-formatted (spaces → underscores), e.g. "science_fiction".
        Returns a normalised list of work dicts in the same shape as search_works_by_author.
        """
        slug = subject.lower().replace(" ", "_")
        data = await self._get(
            f"/subjects/{slug}.json",
            params={"limit": limit, "offset": offset},
        )
        return [_parse_subject_work(w) for w in data.get("works", [])]

    async def get_author(self, author_key: str) -> dict:
        """
        Fetch an author's detail page. Returns at minimum {"name": str}.
        Missing or malformed name falls back to "Unknown".
        Raises OLNotFoundError on 404.
        """
        # author_key may be:
        #   "OL26320A"           -> /authors/OL26320A.json
        #   "/authors/OL26320A"  -> /authors/OL26320A.json  (no .json suffix from search results)
        if author_key.startswith("/authors/"):
            path = author_key + ".json"
        elif author_key.startswith("/"):
            path = author_key  # already a full path with extension
        else:
            path = f"/authors/{author_key}.json"
        data = await self._get(path)
        name = data.get("name") or "Unknown"
        return {"name": name}

    async def aclose(self) -> None:
        await self._client.aclose()
