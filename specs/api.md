# API Specification

This file defines the contracts for all external-facing interfaces. Fill this in before implementing any API endpoints. These specs are inputs to `tasks.md` and AI prompt templates.

---

## Overview

- **Style:** _e.g., REST / GraphQL / gRPC / Message-based_
- **Base URL:** `https://api.example.com/v1` _(update when known)_
- **Versioning strategy:** _e.g., URI versioning (/v1/), header-based_
- **Authentication:** _e.g., Bearer token, API key, OAuth 2.0_
- **Content type:** _e.g., application/json_

---

## Authentication

> Describe how clients authenticate with the API.

- _Method: e.g., JWT in Authorization header_
- _Token lifetime: e.g., 1 hour access token, 30-day refresh token_
- _Error response on auth failure: e.g., 401 Unauthorized_

---

## Error Format

> Define a standard error response shape so all endpoints are consistent.

```
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested item could not be found.",
    "details": {}
  }
}
```

---

## Endpoints

### Resource: _ResourceName_

---

#### GET /resource

**Description:** _What this endpoint returns._

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Max results to return |
| `offset` | integer | No | Pagination offset |

**Response 200:**
```
{
  "items": [ ... ],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

**Error Responses:**
- `401` — Unauthorized
- `500` — Internal server error

---

#### POST /resource

**Description:** _What this endpoint creates._

**Request Body:**
```
{
  "field1": "string",
  "field2": 0
}
```

**Response 201:**
```
{
  "id": "string",
  "field1": "string",
  "field2": 0,
  "createdAt": "ISO 8601 timestamp"
}
```

**Error Responses:**
- `400` — Validation error
- `401` — Unauthorized
- `409` — Conflict (already exists)

---

#### GET /resource/:id

**Description:** _Fetch a single resource by ID._

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique resource identifier |

**Response 200:**
```
{
  "id": "string",
  "field1": "string",
  "createdAt": "ISO 8601 timestamp"
}
```

**Error Responses:**
- `401` — Unauthorized
- `404` — Not found

---

#### PATCH /resource/:id

**Description:** _Partially update a resource._

**Request Body:** _(all fields optional)_
```
{
  "field1": "string"
}
```

**Response 200:** _(updated resource)_

---

#### DELETE /resource/:id

**Description:** _Delete a resource._

**Response 204:** No content

---

## Webhooks (if applicable)

> Describe any outbound event notifications the system sends.

### Event: `resource.created`

**Payload:**
```
{
  "event": "resource.created",
  "timestamp": "ISO 8601",
  "data": { ... }
}
```

---

## Rate Limiting

- _Limit: e.g., 100 requests per minute per API key_
- _Headers returned: e.g., X-RateLimit-Limit, X-RateLimit-Remaining_
- _Error on exceed: 429 Too Many Requests_
