# API Specification

REST API for the Open Library Catalog Service.

---

## Overview

- **Style:** REST
- **Base URL:** `http://localhost:8000` (local)
- **Versioning:** URI prefix — all tenant-facing endpoints are under `/api/v1/`
- **Authentication:** `X-API-Key` header containing the plaintext API key issued at tenant creation
- **Content type:** `application/json`

---

## Authentication

All endpoints except `/health` and `POST /api/v1/admin/tenants` require the `X-API-Key` header.

- The plaintext key is issued once at tenant creation and never stored.
- The server hashes the incoming key (HMAC-SHA256 keyed with `SECRET_KEY`) and matches against the stored hash.
- Missing or invalid key → `401 Unauthorized`.
- Missing required header (FastAPI validation) → `422 Unprocessable Entity`.

---

## Error Format

FastAPI default validation errors use the standard FastAPI shape. Application errors:

```json
{ "detail": "Human-readable error message." }
```

---

## Endpoints

---

### Admin — Tenant Management

#### POST /api/v1/admin/tenants

Create a new tenant. No auth required (bootstrapping). Returns the plaintext API key once — it cannot be retrieved again.

**Request Body:**
```json
{ "name": "string" }
```

**Response 201:**
```json
{
  "id": "uuid",
  "name": "string",
  "api_key": "plaintext-key-returned-once",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Errors:** `409` — Tenant name already exists

---

#### GET /api/v1/admin/tenants

List all tenants. No auth required. API keys are never returned.

**Response 200:**
```json
[
  { "id": "uuid", "name": "string", "created_at": "2024-01-01T00:00:00Z" }
]
```

---

### Ingestion

#### POST /api/v1/ingest

Trigger a catalog ingestion job for the authenticated tenant. Returns immediately; ingestion runs in the background via FastAPI `BackgroundTasks`.

**Auth:** `X-API-Key`

**Request Body:**
```json
{ "query_type": "author", "query_value": "tolkien" }
```

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `query_type` | string | `"author"`, `"subject"` | OL search type |
| `query_value` | string | any | Search term |

**Response 202:**
```json
{ "log_id": "uuid", "status": "pending" }
```

**Errors:** `401` — Invalid key · `422` — Invalid `query_type`

---

### Works — Retrieval

All works endpoints are tenant-scoped. A tenant can only see its own works.

#### GET /api/v1/works

List works for the tenant with optional filtering and pagination.

**Auth:** `X-API-Key`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (≥ 1) |
| `page_size` | integer | 20 | Items per page (1–100) |
| `author` | string | — | Case-insensitive substring match on `author_names` |
| `subject` | string | — | Case-insensitive substring match on `subjects` |
| `year_from` | integer | — | Minimum `first_publish_year` (inclusive) |
| `year_to` | integer | — | Maximum `first_publish_year` (inclusive) |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "ol_work_key": "/works/OL1W",
      "title": "Dune",
      "author_names": ["Frank Herbert"],
      "first_publish_year": 1965,
      "subjects": ["science fiction"],
      "cover_image_url": "https://covers.openlibrary.org/b/id/12345-M.jpg"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**Errors:** `401` — Invalid key · `422` — `page_size` > 100

---

#### GET /api/v1/works/search

Keyword search across `title` and `author_names`. Case-insensitive substring match.

**Auth:** `X-API-Key`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Keyword |
| `page` | integer | No | Default 1 |
| `page_size` | integer | No | Default 20, max 100 |

**Response 200:** Same shape as `GET /api/v1/works`.

**Errors:** `401` — Invalid key · `422` — Missing `q`

---

#### GET /api/v1/works/{work_id}

Return full detail for a single work.

**Auth:** `X-API-Key`

**Response 200:**
```json
{
  "id": "uuid",
  "ol_work_key": "/works/OL1W",
  "title": "Dune",
  "author_names": ["Frank Herbert"],
  "first_publish_year": 1965,
  "subjects": ["science fiction"],
  "cover_image_url": null
}
```

**Errors:** `401` — Invalid key · `404` — Not found or belongs to a different tenant

---

### Ingestion Logs

#### GET /api/v1/ingestion-logs

List ingestion logs for the tenant, ordered by `started_at` descending.

**Auth:** `X-API-Key`

**Query Parameters:** `page` (default 1), `page_size` (default 20, max 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "query_type": "author",
      "query_value": "tolkien",
      "status": "completed",
      "fetched_count": 50,
      "succeeded_count": 50,
      "failed_count": 0,
      "error_details": null,
      "started_at": "2024-01-01T10:00:00Z",
      "finished_at": "2024-01-01T10:00:45Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20
}
```

---

#### GET /api/v1/ingestion-logs/{log_id}

Return a single ingestion log. Useful for polling background job progress.

**Auth:** `X-API-Key`

**Response 200:** Single log object (same fields as items above).

**Errors:** `401` — Invalid key · `404` — Not found or belongs to a different tenant

---

### Reading Lists

#### POST /api/v1/reading-lists

Submit a patron reading list. PII (name, email) is hashed before storage. If the patron has submitted before (matched by email hash), the existing list is upserted and items replaced.

**Auth:** `X-API-Key`

**Request Body:**
```json
{
  "patron_name": "Alice Smith",
  "patron_email": "alice@example.com",
  "books": ["/works/OL1W", "/works/OL2W"]
}
```

**Response 201:**
```json
{
  "reading_list_id": "uuid",
  "resolved": ["/works/OL1W"],
  "unresolved": ["/works/OL2W"]
}
```

`resolved` — books matched against locally stored `Work` rows for this tenant.
`unresolved` — books not found locally; trigger ingestion to populate the catalog first.

**Errors:** `401` — Invalid key · `422` — Missing required fields

---

#### GET /api/v1/reading-lists

List reading lists for the tenant.

**Auth:** `X-API-Key`

**Query Parameters:** `page` (default 1), `page_size` (default 20, max 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "patron_name_hash": "abc123...",
      "patron_email_hash": "def456...",
      "submitted_at": "2024-01-01T09:00:00Z",
      "item_count": 3
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

No plaintext PII is ever returned. Hashes are HMAC-SHA256 hex strings (64 chars).

---

#### GET /api/v1/reading-lists/{reading_list_id}

Return a reading list with all items and their resolution status.

**Auth:** `X-API-Key`

**Response 200:**
```json
{
  "id": "uuid",
  "patron_name_hash": "abc123...",
  "patron_email_hash": "def456...",
  "submitted_at": "2024-01-01T09:00:00Z",
  "items": [
    {
      "id": "uuid",
      "book_reference": "/works/OL1W",
      "resolved_work_id": "uuid",
      "resolution_status": "resolved"
    },
    {
      "id": "uuid",
      "book_reference": "/works/OLmissW",
      "resolved_work_id": null,
      "resolution_status": "unresolved"
    }
  ]
}
```

**Errors:** `401` — Invalid key · `404` — Not found or belongs to a different tenant

---

### Health

#### GET /health

Liveness check. No auth required. No DB access.

**Response 200:**
```json
{ "status": "ok" }
```

---

## Rate Limiting

No rate limits are enforced on incoming requests. The OL HTTP client limits outbound concurrency via `asyncio.Semaphore(OL_MAX_CONCURRENT_REQUESTS)` (default: 5) and retries with exponential backoff on OL `429` and `5xx` responses (max 3 attempts).
