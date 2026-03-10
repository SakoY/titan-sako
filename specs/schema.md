# Schema

This file defines the data models used by the system. Fill this in alongside `specs/api.md` — API response shapes should match these models. These specs are inputs to implementation tasks.

---

## Overview

- **Storage type:** _e.g., relational database, document store, key-value store_
- **Storage system:** _TBD — see `architecture.md`_
- **Primary identifiers:** _e.g., UUID v4, auto-increment integer_
- **Timestamps:** _All records include `createdAt` and `updatedAt` in ISO 8601 format_
- **Soft deletes:** _e.g., Yes — records include `deletedAt` / No — hard deletes_

---

## Conventions

- Field names: _e.g., camelCase / snake_case_
- Booleans: _e.g., prefixed with `is` or `has`_
- Enums: _e.g., uppercase strings stored as TEXT_
- Required fields: marked with `*`
- Nullable fields: marked with `?`

---

## Models

---

### Entity: `User`

Represents an authenticated user of the system.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string | Primary key, unique | Unique identifier |
| `email` * | string | Unique, max 255 | User's email address |
| `name` | string? | Max 255 | Display name |
| `createdAt` * | timestamp | Auto-set on insert | When the record was created |
| `updatedAt` * | timestamp | Auto-set on update | When the record was last modified |

**Indexes:**
- Primary: `id`
- Unique: `email`

**Relationships:**
- _e.g., User has many Items_

---

### Entity: `_EntityName_`

> Describe what this entity represents.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` * | string | Primary key | Unique identifier |
| `userId` * | string | Foreign key → User.id | Owner of this record |
| `fieldName` * | string | Max 500 | _Description_ |
| `status` * | enum | `ACTIVE`, `ARCHIVED` | Current state |
| `createdAt` * | timestamp | Auto-set | Creation time |
| `updatedAt` * | timestamp | Auto-set | Last modified time |

**Indexes:**
- Primary: `id`
- Index: `userId`

**Relationships:**
- _EntityName_ belongs to `User`

---

## Enumerations

### `Status`
| Value | Meaning |
|-------|---------|
| `ACTIVE` | Record is active and visible |
| `ARCHIVED` | Record is hidden but retained |

---

## Migrations

> Describe your migration strategy once a database is chosen.

- _Tool: TBD_
- _Convention: e.g., sequential numbered files, timestamp-prefixed files_
- _Rollback policy: e.g., all migrations must have a down migration_

---

## Seed Data

> Describe any data that must exist for the system to function.

- _e.g., Default roles or permission sets_
- _e.g., System configuration records_
