# Tasks — Open Library Catalog Service

Implementation tasks derived from `specs/requirements.md`. Tasks are ordered by dependency — complete earlier tasks before starting later ones. Each task is sized for a single AI-assisted development session.

**Stack:** Python · FastAPI · SQLite · SQLAlchemy · httpx · FastAPI BackgroundTasks

---

## Task States

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Complete |
| `[!]` | Blocked |

---

## Milestone 1 — Project Foundation

> Repo is scaffolded, runnable with a single command, and the app boots without errors.

- [x] **TASK-001** — Initialize project structure and tooling
  - Description: Create the top-level directory layout (`app/`, `tests/`, `docker/`). Initialize `pyproject.toml` with dependencies: FastAPI, SQLAlchemy, httpx, pydantic-settings, uvicorn. Configure ruff for linting and black for formatting. Add a `Makefile` with `make run` and `make lint` targets.
  - Depends on: none
  - Spec reference: Deliverables — Python requirement, single-command startup
  - Test: `python -c "import fastapi, sqlalchemy, httpx"` succeeds; `make lint` exits 0 on the empty skeleton

- [x] **TASK-002** — Docker Compose setup (single service)
  - Description: Write a `docker-compose.yml` that defines a single `api` service built from a `Dockerfile`. The Dockerfile installs dependencies and runs uvicorn. Expose the API on port 8000. Update `make run` to invoke `docker compose up --build`.
  - Depends on: TASK-001
  - Spec reference: Deliverables — single-command startup (`docker compose up` or `make run`)
  - Test: `docker compose up --build` starts the service; `curl http://localhost:8000/health` returns HTTP 200

- [x] **TASK-003** — Application configuration and environment loading
  - Description: Implement `app/core/config.py` using pydantic-settings. Settings to load from environment: `DATABASE_URL` (default: `sqlite:///./catalog.db`), `SECRET_KEY` (required), `OL_BASE_URL` (default: `https://openlibrary.org`), `OL_MAX_CONCURRENT_REQUESTS` (default: 5). Provide a `.env.example` listing all variables.
  - Depends on: TASK-001
  - Spec reference: Architecture constraints — configurable deployment
  - Test: Instantiating `Settings()` with a test env returns correctly typed values; missing `SECRET_KEY` raises a `ValidationError`

- [x] **TASK-004** — Database connection and schema initialization
  - Description: Configure a SQLAlchemy `create_engine` (sync) pointed at `DATABASE_URL`, and a `SessionLocal` factory. Implement a FastAPI lifespan hook that calls `Base.metadata.create_all(engine)` on startup. Add a `get_db` dependency that yields a session and closes it on teardown.
  - Depends on: TASK-003
  - Spec reference: Tier 1 — Ingest & Store (persistent storage)
  - Test: Starting the app with a fresh SQLite file creates the DB file without error; a test injecting `get_db` can execute `SELECT 1` successfully

---

## Milestone 2 — Data Models & Schema

> All four SQLAlchemy models are defined; `create_all` creates the correct tables on startup.

- [x] **TASK-005** — Tenant model
  - Description: Define a `Tenant` SQLAlchemy model in `app/models/tenant.py` with fields: `id` (UUID PK, auto-generated), `name` (string, unique, not null), `api_key` (string, unique — store a hashed value), `created_at` (datetime, auto-set). Register with the shared `Base`.
  - Depends on: TASK-004
  - Spec reference: Architecture constraints — all operations scoped to a tenant
  - Test: After `create_all`, a `Tenant` row can be inserted and queried back; inserting a duplicate `name` raises an `IntegrityError`

- [x] **TASK-006** — Work model
  - Description: Define a `Work` SQLAlchemy model in `app/models/work.py` with fields: `id` (UUID PK), `tenant_id` (UUID FK → Tenant, not null), `ol_work_key` (string, not null), `title` (string), `author_names` (JSON), `first_publish_year` (int, nullable), `subjects` (JSON), `cover_image_url` (string, nullable), `ingested_at` (datetime). Add a unique constraint on `(tenant_id, ol_work_key)`.
  - Depends on: TASK-005
  - Spec reference: Tier 1 — Ingest & Store (stored fields)
  - Test: After `create_all`, a Work row round-trips all fields including JSON; inserting a duplicate `(tenant_id, ol_work_key)` raises `IntegrityError`

- [x] **TASK-007** — IngestionLog model
  - Description: Define an `IngestionLog` SQLAlchemy model in `app/models/ingestion_log.py` with fields: `id` (UUID PK), `tenant_id` (UUID FK → Tenant), `query_type` (string: `"author"` or `"subject"`), `query_value` (string), `status` (string: `pending`/`running`/`completed`/`failed`), `fetched_count` (int, default 0), `succeeded_count` (int, default 0), `failed_count` (int, default 0), `error_details` (text, nullable), `started_at` (datetime), `finished_at` (datetime, nullable).
  - Depends on: TASK-005
  - Spec reference: Tier 1 — Activity Log
  - Test: After `create_all`, all fields round-trip; a log row can be updated from `pending` to `completed` with `finished_at` set

- [x] **TASK-008** — ReadingList and ReadingListItem models
  - Description: Define `ReadingList` (`id`, `tenant_id` FK → Tenant, `patron_name_hash` string, `patron_email_hash` string, `submitted_at` datetime) and `ReadingListItem` (`id`, `reading_list_id` FK → ReadingList, `book_reference` string, `resolved_work_id` UUID FK → Work nullable, `resolution_status` string: `resolved`/`unresolved`) in `app/models/reading_list.py`. Add a unique constraint on `(tenant_id, patron_email_hash)` on `ReadingList`.
  - Depends on: TASK-006
  - Spec reference: Tier 2 — PII Handling (store hashes only; deduplicate by patron)
  - Test: After `create_all`, inserting a ReadingList with two items and querying back returns correct resolution statuses; a duplicate `(tenant_id, patron_email_hash)` raises `IntegrityError`

---

## Milestone 3 — Open Library API Client

> `OLClient` can fetch from the live Open Library API with retry and rate-limit handling.

- [x] **TASK-009** — Base HTTP client with retry and rate-limit handling
  - Description: Implement `app/services/ol_client.py` with an `OLClient` class wrapping `httpx.AsyncClient`. Configure: base URL from settings, an `asyncio.Semaphore` limiting concurrent requests to `OL_MAX_CONCURRENT_REQUESTS`, and exponential backoff retries (max 3) on `429` and `5xx` responses. Define custom exceptions: `OLNotFoundError`, `OLRateLimitError`, `OLClientError`.
  - Depends on: TASK-003
  - Spec reference: Tier 2 — Background Processing (handle OL rate limits gracefully)
  - Test: Unit tests using `httpx.MockTransport` verify: a `429` triggers retry; a `404` raises `OLNotFoundError`; concurrent requests beyond the semaphore limit are queued

- [x] **TASK-010** — Author search integration
  - Description: Implement `OLClient.search_works_by_author(author: str, limit: int, offset: int) -> list[dict]` calling `/search.json?author=...&limit=...&offset=...`. Parse and return only the fields needed: `key`, `title`, `author_key` (list), `first_publish_year`, `subject` (list), `cover_i` (int or None).
  - Depends on: TASK-009
  - Spec reference: Tier 1 — Ingest & Store (fetch works by author name)
  - Test: Integration test against live OL with a well-known author returns ≥1 result with a non-null `key`; missing optional fields default to `None` or `[]` without raising

- [x] **TASK-011** — Subject search integration
  - Description: Implement `OLClient.search_works_by_subject(subject: str, limit: int, offset: int) -> list[dict]` calling `/search.json?subject=...`. Return the same field shape as `search_works_by_author`.
  - Depends on: TASK-009
  - Spec reference: Tier 1 — Ingest & Store (fetch works by subject)
  - Test: Integration test with a well-known subject returns ≥1 result; same field parsing contract as TASK-010

- [x] **TASK-012** — Author detail resolution integration
  - Description: Implement `OLClient.get_author(author_key: str) -> dict` fetching `/authors/{key}.json`. Return a dict with at minimum `name` (string). Handle missing or malformed `name` field by returning `{"name": "Unknown"}`. Raise `OLNotFoundError` on 404.
  - Depends on: TASK-009
  - Spec reference: Tier 1 — Ingest & Store (resolve author info via follow-up requests)
  - Test: Integration test with a known author key returns a non-empty `name`; a fabricated key raises `OLNotFoundError`

- [x] **TASK-013** — Cover image URL construction utility
  - Description: Implement a pure function `build_cover_url(cover_id: int | None) -> str | None` in `app/services/ol_client.py` that converts an Open Library `cover_i` integer to the covers CDN URL (`https://covers.openlibrary.org/b/id/{cover_id}-M.jpg`). Returns `None` if `cover_id` is `None`.
  - Depends on: TASK-009
  - Spec reference: Tier 1 — Ingest & Store (cover image URL if available)
  - Test: Known integer input produces the expected URL string; `None` input returns `None`

---

## Milestone 4 — Catalog Ingestion Logic

> Core ingestion functions work correctly with mocked OL responses.

- [x] **TASK-014** — Work upsert repository function
  - Description: Implement `app/repositories/work_repo.py` with `upsert_work(db, tenant_id, work_data: dict) -> Work` that inserts a new `Work` row or updates an existing one matched on `(tenant_id, ol_work_key)`. Set `ingested_at` to the current UTC time on every upsert.
  - Depends on: TASK-006
  - Spec reference: Tier 1 — Ingest & Store (store locally)
  - Test: Calling `upsert_work` twice with the same `ol_work_key` results in exactly one DB row; the second call updates `title` if it changed

- [x] **TASK-015** — Single-work ingestion pipeline
  - Description: Implement `app/services/ingestion.py` with `ingest_single_work(db, ol_client, tenant_id, raw_work: dict) -> dict` that: resolves author names via `OLClient.get_author` for any `author_key` values in the raw work dict, builds a cover URL, assembles the full work dict, and calls `upsert_work`. Returns `{"status": "success", "ol_work_key": ...}` or `{"status": "failed", "error": ...}`.
  - Depends on: TASK-013, TASK-014
  - Spec reference: Tier 1 — Ingest & Store (follow-up requests for missing fields)
  - Test: With a mocked `OLClient`, author keys trigger `get_author` calls; the resulting `Work` row has a populated `author_names` list; an `OLClientError` during author resolution returns status `"failed"`

- [x] **TASK-016** — Batch ingestion orchestrator
  - Description: Implement `run_ingestion(db, ol_client, tenant_id, query_type, query_value, log_id)` in `app/services/ingestion.py`. Paginate through OL search results (page size 50, stop when results are exhausted or 500 works reached), call `ingest_single_work` for each, and update the `IngestionLog` row after each page with running counts. Mark the log `completed` or `failed` on exit.
  - Depends on: TASK-015, TASK-007
  - Spec reference: Tier 1 — Ingest & Store, Activity Log
  - Test: With mocked OL returning two pages of 3 works each, the log row shows `fetched_count=6`; a simulated failure on one work increments `failed_count` without aborting the batch

---

## Milestone 5 — Tenant Auth & Ingestion API

> Tenants can authenticate and trigger catalog ingestion non-blocking via BackgroundTasks.

- [ ] **TASK-017** — Tenant authentication dependency
  - Description: Implement a FastAPI dependency `require_tenant(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> Tenant` in `app/api/deps.py`. Look up the Tenant by matching a hashed form of `x_api_key` against `Tenant.api_key`. Raise `HTTP 401` if the header is missing or the key doesn't match any tenant.
  - Depends on: TASK-005, TASK-004
  - Spec reference: Architecture constraints — all API operations scoped to a specific tenant
  - Test: Request without header → 401; invalid key → 401; valid key → injects correct `Tenant` object

- [ ] **TASK-018** — Tenant management endpoints (admin)
  - Description: Add `POST /api/v1/admin/tenants` (no auth required for bootstrapping) that creates a new Tenant, generates a random API key, stores its hash, and returns the plaintext key once. Add `GET /api/v1/admin/tenants` listing all tenants (id, name, created_at — no keys).
  - Depends on: TASK-017
  - Spec reference: Architecture constraints — multi-tenant setup
  - Test: POST creates a tenant and returns a plaintext key; the DB stores only the hashed form; a second POST with the same name returns 409

- [ ] **TASK-019** — Async ingestion trigger endpoint
  - Description: Add `POST /api/v1/ingest` (tenant-scoped via `require_tenant`) accepting `{"query_type": "author"|"subject", "query_value": string}`. Create an `IngestionLog` row with `status=pending`, then dispatch `run_ingestion` via FastAPI `BackgroundTasks`. Return `202 Accepted` with the `log_id` immediately — do not wait for ingestion to finish.
  - Depends on: TASK-016, TASK-017
  - Spec reference: Tier 2 — Background Processing (must not block API responses)
  - Test: POST returns 202 within 200ms regardless of OL response time; after the background task completes, the `IngestionLog` row transitions from `pending` to `completed`

---

## Milestone 6 — Retrieval API

> Patrons and staff can list, filter, search, and inspect stored books for their tenant.

- [ ] **TASK-020** — Work list endpoint with pagination
  - Description: Add `GET /api/v1/works` (tenant-scoped) returning a paginated list of Works for the tenant. Response shape: `{"items": [...], "total": int, "page": int, "page_size": int}`. Accept `page` (default 1) and `page_size` (default 20, max 100) query params. Each item includes: `id`, `title`, `author_names`, `first_publish_year`, `subjects`, `cover_image_url`.
  - Depends on: TASK-017, TASK-006
  - Spec reference: Tier 1 — Retrieval API (list all stored books with pagination)
  - Test: After ingesting 25 works, `page=1&page_size=20` returns 20 items and `total=25`; `page=2` returns 5 items; `page_size=101` returns 422

- [ ] **TASK-021** — Work filter query params
  - Description: Extend `GET /api/v1/works` to accept optional filter params: `author` (case-insensitive substring match against `author_names` JSON), `subject` (case-insensitive substring match against `subjects` JSON), `year_from` (int), `year_to` (int). Active filters are AND-combined.
  - Depends on: TASK-020
  - Spec reference: Tier 1 — Retrieval API (filter by author, subject, or publish year range)
  - Test: Filter by `author` returns only matching rows; combined `author` + `year_from` excludes out-of-range works; a tenant cannot see another tenant's works even if they match the filter

- [ ] **TASK-022** — Keyword search endpoint
  - Description: Add `GET /api/v1/works/search?q=<keyword>` (tenant-scoped) performing a case-insensitive search across `title` and `author_names`. Return paginated results in the same shape as the list endpoint. The `q` parameter is required; return 422 if absent.
  - Depends on: TASK-020
  - Spec reference: Tier 1 — Retrieval API (search stored books by keyword — title or author)
  - Test: Search for a known substring of an ingested title returns that work; a search with no matches returns `{"items": [], "total": 0, ...}`; results never include works from a different tenant

- [ ] **TASK-023** — Single work detail endpoint
  - Description: Add `GET /api/v1/works/{work_id}` (tenant-scoped) returning all stored fields for the work. Return 404 if the work does not exist or belongs to a different tenant.
  - Depends on: TASK-020
  - Spec reference: Tier 1 — Retrieval API (get a single book's full detail)
  - Test: Valid `work_id` from the correct tenant returns 200 with all fields; a `work_id` from another tenant returns 404; a nonexistent UUID returns 404

---

## Milestone 7 — Activity Logging

> Every ingestion operation is logged and queryable via API.

- [ ] **TASK-024** — IngestionLog repository functions
  - Description: Implement `app/repositories/log_repo.py` with: `create_log(db, tenant_id, query_type, query_value) -> IngestionLog` (creates a `pending` row) and `update_log(db, log_id, **fields)` (updates any combination of `status`, `fetched_count`, `succeeded_count`, `failed_count`, `error_details`, `finished_at`).
  - Depends on: TASK-007
  - Spec reference: Tier 1 — Activity Log (record every ingestion operation)
  - Test: `create_log` returns a row with `status="pending"` and `finished_at=None`; `update_log` with `status="completed"` persists correctly

- [ ] **TASK-025** — Ingestion log list endpoint
  - Description: Add `GET /api/v1/ingestion-logs` (tenant-scoped) returning a paginated list of `IngestionLog` rows for the tenant, ordered by `started_at` descending. Include all log fields in the response.
  - Depends on: TASK-024, TASK-017
  - Spec reference: Tier 1 — Activity Log (expose log via API)
  - Test: After two ingestion runs, GET returns exactly two logs for that tenant in descending time order; a different tenant's logs are not included

- [ ] **TASK-026** — Ingestion log detail and status endpoint
  - Description: Add `GET /api/v1/ingestion-logs/{log_id}` (tenant-scoped) returning full detail of a single log including `error_details`. Returns 404 if not found or belongs to another tenant. This endpoint is poll-friendly for checking background task progress.
  - Depends on: TASK-025
  - Spec reference: Tier 1 — Activity Log; Tier 2 — Background Processing (visibility into progress)
  - Test: GET on a running log returns `status="running"` with current counts; after completion returns `status="completed"` with `finished_at` set; another tenant's `log_id` returns 404

---

## Milestone 8 — PII & Reading Lists

> Patrons can submit reading lists; PII is hashed before storage and never exposed in responses.

- [ ] **TASK-027** — PII hashing utility
  - Description: Implement `hash_pii(value: str, secret_key: str) -> str` in `app/core/security.py` using HMAC-SHA256 keyed with `SECRET_KEY` from settings. The function must be deterministic (same input + key → same output) and irreversible.
  - Depends on: TASK-003
  - Spec reference: Tier 2 — PII Handling (hash name and email before storing)
  - Test: Same input + key always returns the same output; different inputs return different outputs; the output contains no recognizable substring of the original; changing the key changes the output

- [ ] **TASK-028** — Book reference resolver
  - Description: Implement `resolve_book_references(db, tenant_id, references: list[str]) -> dict[str, Work | None]` in `app/services/reading_list.py`. Given OL work IDs or ISBNs, look up each against locally stored `Work` rows for the tenant. Returns a mapping of reference → `Work` or `None` if not found. References matching another tenant's works resolve to `None`.
  - Depends on: TASK-006
  - Spec reference: Tier 2 — PII Handling (response confirms which books resolved)
  - Test: Known Work rows resolve to Work objects; unknown references map to `None`; a reference matching a different tenant's work returns `None`

- [ ] **TASK-029** — Reading list submission endpoint
  - Description: Add `POST /api/v1/reading-lists` (tenant-scoped) accepting `{"patron_name": str, "patron_email": str, "books": [str]}`. Hash name and email with `hash_pii` before storing. If a `ReadingList` with the same `(tenant_id, patron_email_hash)` already exists, upsert rather than duplicate. Store `ReadingListItem` rows with resolution status from `resolve_book_references`. Return `{"reading_list_id": ..., "resolved": [...], "unresolved": [...]}`.
  - Depends on: TASK-027, TASK-028, TASK-008
  - Spec reference: Tier 2 — PII Handling (submit reading lists; deduplicate; confirm resolution)
  - Test: Submitting the same patron email twice results in one `ReadingList` DB row; the DB contains no plaintext name or email anywhere; response lists resolved and unresolved books; another tenant cannot see this reading list

- [ ] **TASK-030** — Reading list retrieval endpoints
  - Description: Add `GET /api/v1/reading-lists` (tenant-scoped) returning paginated `ReadingList` rows (id, patron_name_hash, patron_email_hash, submitted_at, item_count). Add `GET /api/v1/reading-lists/{id}` returning the list with all `ReadingListItem` rows and their resolution status.
  - Depends on: TASK-029
  - Spec reference: Tier 2 — PII Handling
  - Test: GET returns only the current tenant's reading lists; detail endpoint returns correct item statuses; no plaintext PII appears in any response field

---

## Milestone 9 — Tests & Hardening

> Service is fully tested, has a health endpoint, and is documented for local setup.

- [ ] **TASK-031** — Test infrastructure: fixtures and test database
  - Description: Set up pytest with a shared `conftest.py` in `tests/`. Create fixtures for: an in-memory SQLite test DB with all tables created (`test_db`), a `TestClient` wrapping the FastAPI app with the test DB injected, a default `Tenant` fixture with a known API key, and `Work` factory helpers that insert test rows.
  - Depends on: TASK-017
  - Spec reference: All tiers — foundational test infrastructure
  - Test: Running `pytest tests/` on an empty test suite exits 0; all fixtures initialize without error

- [ ] **TASK-032** — Unit tests: OLClient
  - Description: Write unit tests in `tests/unit/test_ol_client.py` using `httpx.MockTransport` covering: successful author search response parsing, successful subject search response parsing, author detail resolution (including missing name fallback), cover URL construction, 429 retry behavior, and 404 → `OLNotFoundError` mapping.
  - Depends on: TASK-031, TASK-013
  - Spec reference: Tier 1 — Ingest & Store; Tier 2 — rate limit handling
  - Test: All tests pass with zero live network calls; the retry path is exercised at least once

- [ ] **TASK-033** — Unit tests: ingestion pipeline
  - Description: Write unit tests in `tests/unit/test_ingestion.py` for `ingest_single_work` and `run_ingestion` with mocked `OLClient` and the test DB. Cover: successful multi-author resolution, partial failure (one work's author lookup raises `OLClientError`), two-page pagination, and `IngestionLog` count accuracy.
  - Depends on: TASK-031, TASK-016
  - Spec reference: Tier 1 — Ingest & Store, Activity Log
  - Test: Log counts exactly match the number of successes and failures injected; pagination stops when results are exhausted

- [ ] **TASK-034** — Integration tests: Retrieval API
  - Description: Write integration tests in `tests/integration/test_retrieval.py` using `TestClient` + test DB. Cover: pagination boundary conditions, all filter combinations, keyword search with mixed case, single-work 404 on wrong tenant.
  - Depends on: TASK-031, TASK-023
  - Spec reference: Tier 1 — Retrieval API
  - Test: A test explicitly asserts tenant A cannot retrieve tenant B's works via any retrieval endpoint; all filter and pagination tests pass

- [ ] **TASK-035** — Integration tests: PII and reading lists
  - Description: Write integration tests in `tests/integration/test_reading_lists.py` for `POST /api/v1/reading-lists` and retrieval endpoints. Cover: deduplication on repeated patron email submission, resolution report accuracy, absence of plaintext PII in all API responses, and tenant isolation.
  - Depends on: TASK-031, TASK-030
  - Spec reference: Tier 2 — PII Handling
  - Test: A DB-level assertion confirms no stored column contains the raw patron email string; all PII tests pass

- [ ] **TASK-036** — Health check endpoint
  - Description: Add `GET /health` returning `{"status": "ok"}` with HTTP 200. No auth required and no DB access — pure liveness check used by Docker Compose.
  - Depends on: TASK-002
  - Spec reference: Deliverables — service is runnable and testable locally
  - Test: `/health` returns 200 before the DB is initialized; Docker Compose `healthcheck` passes within 10 seconds of startup

- [ ] **TASK-037** — README and API documentation
  - Description: Write `README.md` with: ASCII architecture diagram (API → BackgroundTasks → SQLite, API → Open Library); key design decisions (tenant isolation, PII hashing, BackgroundTasks trade-offs); setup and run instructions (`make run` + `.env.example`); curl-based reference for every endpoint; and a "What I would do differently" section.
  - Depends on: TASK-036
  - Spec reference: Deliverables — README.md
  - Test: Following the README from scratch on a clean machine (with Docker) produces a running service that responds correctly to the first example curl command

---

## Milestone 10 — Tier 3 Backlog (Differentiators)

> Pick any that interest you — depth on one is better than surface-level on all.

- [ ] **TASK-038** — WorkVersion model
  - Description: Define a `WorkVersion` SQLAlchemy model in `app/models/work_version.py` with fields: `id` (UUID PK), `work_id` (UUID FK → Work), `version_number` (int), `snapshot` (JSON — full metadata at that version), `changed_fields` (JSON — diff from the previous version), `recorded_at` (datetime). Add a unique constraint on `(work_id, version_number)`.
  - Depends on: TASK-006
  - Spec reference: Tier 3 — Version Management
  - Test: After `create_all`, two versions for the same work insert without error; a duplicate `version_number` for the same work raises `IntegrityError`

- [ ] **TASK-039** — Versioned upsert logic
  - Description: Modify `upsert_work` in `app/repositories/work_repo.py` to compare incoming metadata against the current `Work` row before updating. If any tracked field differs (including regression to `None`), write a new `WorkVersion` with the diff in `changed_fields` and increment `version_number`. Skip version creation if no fields changed.
  - Depends on: TASK-038, TASK-014
  - Spec reference: Tier 3 — Version Management (create new version on change; handle regression)
  - Test: Upserting identical metadata creates no new `WorkVersion`; changing one field creates one version with that field in `changed_fields`; regressing a field from non-null to `None` is captured as a change

- [ ] **TASK-040** — Version history API endpoints
  - Description: Add `GET /api/v1/works/{work_id}/versions` (tenant-scoped) returning all `WorkVersion` records in ascending version order. Add `GET /api/v1/works/{work_id}/versions/{version_number}` returning the full snapshot for that version.
  - Depends on: TASK-039, TASK-017
  - Spec reference: Tier 3 — Version Management (expose version history via API)
  - Test: After two re-ingestions that change metadata, the versions endpoint returns two entries with accurate `changed_fields` and `recorded_at` timestamps; a nonexistent version number returns 404

- [ ] **TASK-041** — Per-tenant request rate limiter middleware
  - Description: Implement a FastAPI middleware in `app/middleware/rate_limit.py` using an in-process sliding-window counter (dict keyed by `tenant_id`, reset each minute) enforcing a configurable `TENANT_RATE_LIMIT_RPM`. Requests over the limit receive HTTP 429 with a `Retry-After` header.
  - Depends on: TASK-017
  - Spec reference: Tier 3 — Noisy Neighbor Throttling (per-tenant resource limiting)
  - Test: Sending N+1 requests in one window for the same tenant returns 429 on the last; a different tenant in the same window is unaffected

- [ ] **TASK-042** — Per-tenant consumption metrics endpoint
  - Description: Add `GET /api/v1/admin/tenants/{tenant_id}/metrics` returning: total `Work` rows stored, total `IngestionLog` rows, total OL API calls made (tracked via a module-level counter incremented in `OLClient`), and current rate-limit window usage.
  - Depends on: TASK-041
  - Spec reference: Tier 3 — Noisy Neighbor Throttling (visibility into per-tenant consumption)
  - Test: After a known ingestion run, `total_works` and `total_ingestion_logs` match expected counts; `ol_api_calls` reflects the number of actual HTTP calls made to OL

---

## Completed

> Move tasks here once done, for a record of what was built and when.

<!-- Example:
- [x] **TASK-001** — Initialize project structure and tooling
  - Completed: YYYY-MM-DD
-->
