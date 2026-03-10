# Schema

Data models for the Open Library Catalog Service.

---

## Overview

- **Storage type:** Relational database
- **Storage system:** SQLite (via SQLAlchemy sync engine); `Base.metadata.create_all()` on startup — no Alembic
- **Primary identifiers:** UUID v4 (string), auto-generated at insert
- **Timestamps:** UTC `datetime` stored as `DateTime(timezone=True)`, auto-set on insert
- **Soft deletes:** None — hard deletes (no `deleted_at`)

---

## Conventions

- Field names: `snake_case`
- Enums: lowercase strings stored as `TEXT` (e.g., `"pending"`, `"completed"`)
- JSON fields: stored as SQLAlchemy `JSON` column; Python `list` or `dict`
- Required fields: marked with `*`
- Nullable fields: marked with `?`
- All `id` fields are UUID v4 strings

---

## Models

---

### `Tenant`

A library or organisation that uses the service. All other records are scoped to a tenant.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string (UUID) | Primary key, auto-generated | Unique identifier |
| `name` * | string | Unique, not null | Human-readable tenant name |
| `api_key` * | string | Unique, not null | HMAC-SHA256 hash of the plaintext key |
| `created_at` * | datetime (UTC) | Auto-set on insert | When the tenant was created |

**Indexes:** Primary `id`; Unique `name`; Unique `api_key`

**Relationships:** Tenant has many `Work`, `IngestionLog`, `ReadingList`

**Notes:** The plaintext API key is returned once on creation and never stored. The DB stores only the hash produced by `hash_pii(plaintext_key, SECRET_KEY)`.

---

### `Work`

A book/work record fetched from Open Library and stored per tenant.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string (UUID) | Primary key, auto-generated | Unique identifier |
| `tenant_id` * | string (UUID) | FK → `Tenant.id`, not null | Owning tenant |
| `ol_work_key` * | string | Not null | Open Library work key (e.g. `/works/OL1W`) |
| `title` ? | string | Nullable | Work title |
| `author_names` ? | JSON (list[str]) | Nullable | Resolved author names |
| `first_publish_year` ? | integer | Nullable | Year of first publication |
| `subjects` ? | JSON (list[str]) | Nullable | Subject tags |
| `cover_image_url` ? | string | Nullable | CDN URL, e.g. `https://covers.openlibrary.org/b/id/{id}-M.jpg` |
| `ingested_at` * | datetime (UTC) | Auto-set on insert/update | Last upsert time |

**Indexes:** Primary `id`; Unique `(tenant_id, ol_work_key)`

**Relationships:** Work belongs to `Tenant`; Work referenced by `ReadingListItem.resolved_work_id`

---

### `IngestionLog`

Tracks every ingestion job triggered by a tenant.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string (UUID) | Primary key, auto-generated | Unique identifier |
| `tenant_id` * | string (UUID) | FK → `Tenant.id`, not null | Owning tenant |
| `query_type` * | string | `"author"` or `"subject"` | Type of OL search |
| `query_value` * | string | Not null | Search term |
| `status` * | string | `"pending"`, `"running"`, `"completed"`, `"failed"` | Current state |
| `fetched_count` * | integer | Default 0 | Total works fetched from OL |
| `succeeded_count` * | integer | Default 0 | Works successfully upserted |
| `failed_count` * | integer | Default 0 | Works that failed to ingest |
| `error_details` ? | text | Nullable | Error message if status is `"failed"` |
| `started_at` * | datetime (UTC) | Auto-set on insert | When the job was created |
| `finished_at` ? | datetime (UTC) | Nullable | When the job completed or failed |

**Indexes:** Primary `id`

**Relationships:** IngestionLog belongs to `Tenant`

---

### `ReadingList`

A patron's reading list, submitted via the API. PII is hashed before storage.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string (UUID) | Primary key, auto-generated | Unique identifier |
| `tenant_id` * | string (UUID) | FK → `Tenant.id`, not null | Owning tenant |
| `patron_name_hash` * | string | Not null | HMAC-SHA256 of patron's name |
| `patron_email_hash` * | string | Not null | HMAC-SHA256 of patron's email |
| `submitted_at` * | datetime (UTC) | Auto-set on insert | When the list was submitted |

**Indexes:** Primary `id`; Unique `(tenant_id, patron_email_hash)`

**Relationships:** ReadingList belongs to `Tenant`; ReadingList has many `ReadingListItem`

**Notes:** A second submission from the same patron (matched by `patron_email_hash`) upserts the existing row and replaces all items. Plaintext name and email are never persisted.

---

### `ReadingListItem`

A single book entry within a reading list.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string (UUID) | Primary key, auto-generated | Unique identifier |
| `reading_list_id` * | string (UUID) | FK → `ReadingList.id`, not null | Parent list |
| `book_reference` * | string | Not null | OL work key submitted by patron |
| `resolved_work_id` ? | string (UUID) | FK → `Work.id`, nullable | Matched `Work` row, if found |
| `resolution_status` * | string | `"resolved"` or `"unresolved"` | Whether the reference matched a local Work |

**Indexes:** Primary `id`

**Relationships:** ReadingListItem belongs to `ReadingList`; optionally references `Work`

---

## Enumerations

### `IngestionLog.status`
| Value | Meaning |
|-------|---------|
| `pending` | Job created, not yet started |
| `running` | Background task is actively ingesting |
| `completed` | All pages processed successfully |
| `failed` | Unrecoverable error; see `error_details` |

### `ReadingListItem.resolution_status`
| Value | Meaning |
|-------|---------|
| `resolved` | `book_reference` matched a `Work` row for this tenant |
| `unresolved` | No matching `Work` found; patron may need to trigger ingestion |

---

## Migrations

- **Tool:** None — `Base.metadata.create_all(engine)` is called on every startup
- **Trade-off:** Suitable for development; for production use Alembic with versioned migration files
- **Rollback:** Drop and recreate (dev); Alembic `downgrade` (prod)

---

## Seed Data

None required. Tenants are created via `POST /api/v1/admin/tenants` before any other operations.
