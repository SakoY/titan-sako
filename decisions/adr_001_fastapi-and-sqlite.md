# ADR 001 — Use FastAPI and SQLite as the API Framework and Data Store

**Date:** 2026-03-10
**Status:** Accepted
**Deciders:** Engineering team

---

## Context

The Open Library Catalog Service is a multi-tenant catalog API that ingests book data from the Open Library API, stores it locally, and exposes search, browsing, and reading list submission endpoints. The service needs to be straightforward for reviewers to clone and run without installing or configuring any external infrastructure.

The two central technology choices that shape the entire implementation are:
1. The **API framework** — which determines how routes, background tasks, and dependency injection are handled.
2. The **data store** — which determines where catalog data is persisted and how it is queried.

These choices are tightly linked because the goal is a self-contained service that starts with a single command (`docker compose up`) and requires no external processes.

---

## Decision Drivers

- **Zero external dependencies at runtime** — reviewers should be able to clone the repo, copy `.env.example`, and have the service fully running without installing a database, message broker, or any other infrastructure.
- **Built-in background task support** — catalog ingestion must be non-blocking (return 202 immediately, process in the background). The framework needs to support this without requiring an external queue or worker process.
- **Rapid API development** — the surface area of the API (auth dependency, route handlers, request/response validation) should be expressible concisely so the implementation stays focused on business logic.
- **Optimized for local evaluation** — this project is designed to be reviewed and assessed locally, not deployed to production. Simplicity and clarity take precedence over operational scale.
- **Developer familiarity** — the Python ecosystem is required by the project spec; choices within it should minimize ramp-up time.

---

## Options Considered

### Option A — FastAPI + SQLite (chosen)

FastAPI is a Python web framework built on Starlette and Pydantic. It provides async-native routing, automatic OpenAPI documentation, a `BackgroundTasks` mechanism for dispatching non-blocking work within the same process, and a dependency injection system that makes per-request resources (like DB sessions and tenant auth) composable and testable.

SQLite is a file-based relational database embedded directly in the Python standard library via the `sqlite3` module. SQLAlchemy's sync engine works against SQLite with no additional installation. A fresh DB file is created automatically on startup via `Base.metadata.create_all`.

**Pros:**
- Single-command startup with no external processes required
- `BackgroundTasks` handles async ingestion in-process with no broker configuration
- Automatic OpenAPI docs at `/docs` with zero extra code
- Pydantic-native request/response validation and typed settings via `pydantic-settings`
- SQLite creates the DB file on first run — no migration tooling or schema setup needed for local use
- In-memory SQLite in tests provides full DB fidelity with no test infrastructure overhead
- Minimal Docker image — just `python:3.12-slim` with pip dependencies

**Cons:**
- `BackgroundTasks` shares the uvicorn worker process — a long-running ingestion task can affect API response latency under load
- SQLite does not support concurrent writes from multiple processes; horizontal scaling would require switching databases
- No built-in retry queue, dead-letter handling, or durable task persistence if the process crashes mid-ingestion

---

### Option B — Flask + PostgreSQL

Flask is a minimal WSGI framework. PostgreSQL is a production-grade relational database.

**Pros:**
- PostgreSQL is production-ready: supports concurrent writes, connection pooling, and horizontal read scaling
- Mature ecosystem for migrations (Alembic) and connection management

**Cons:**
- Requires a running PostgreSQL instance — adds Docker Compose complexity and setup friction for reviewers
- Flask has no native background task primitive; async ingestion would require Celery + Redis or a similar broker, adding further external dependencies
- More infrastructure to configure correctly before the first request can succeed

---

### Option C — FastAPI + PostgreSQL + Celery/Redis

Full production stack: FastAPI for the API layer, PostgreSQL for persistence, and Celery with Redis as the background task system.

**Pros:**
- Durable task queue with retry, dead-letter, and worker scaling
- PostgreSQL concurrency handles multi-process and multi-tenant write load
- Closest to a real production deployment pattern

**Cons:**
- Three additional external services (PostgreSQL, Redis, Celery worker) must be orchestrated before the service is usable
- Significantly more Docker Compose configuration, environment variables, and startup ordering concerns
- Overkill for a project scoped to local evaluation — the operational complexity obscures the business logic being assessed

---

## Decision

We chose **Option A — FastAPI + SQLite** because it best satisfies the primary driver: a service that is immediately runnable locally with no external infrastructure.

FastAPI's `BackgroundTasks` gives us non-blocking ingestion dispatch without adding a broker or worker process. SQLite gives us full relational persistence — foreign keys, unique constraints, filtered queries — without requiring a database server. Together they allow the entire service to boot from a single `docker compose up` command.

The trade-offs are accepted explicitly: this design is optimized for local evaluation and simplicity, not production throughput. The concurrency limitations of SQLite and the in-process nature of `BackgroundTasks` are acceptable constraints for the scope of this project.

---

## Consequences

### Positive
- Reviewers can run the full service in under a minute with no external dependencies
- Tests use in-memory SQLite — fast, fully isolated, no test database setup required
- `BackgroundTasks` integration is native to FastAPI — no worker configuration, no broker healthchecks, no serialization format decisions
- The Docker image is small and builds quickly (`python:3.12-slim` + pip)
- Automatic OpenAPI documentation at `/docs` without any additional effort

### Negative
- SQLite's write serialization means the service cannot scale horizontally without a database swap
- `BackgroundTasks` tasks are not durable — if the uvicorn process restarts mid-ingestion, the in-flight task is lost and the `IngestionLog` row will remain in `running` status indefinitely
- No built-in visibility into background task queue depth or worker health beyond the `IngestionLog` API

### Risks
- **Mid-ingestion process crash:** An `IngestionLog` row left in `running` status after a crash provides no automatic recovery path. Mitigation: a startup check that resets stale `running` logs to `failed` would address this in a follow-up task.
- **Ingestion blocking the API:** A very large ingestion batch running in the same uvicorn worker could introduce latency on concurrent API requests. Mitigation: the `OL_MAX_CONCURRENT_REQUESTS` semaphore limits OL API call rate, bounding the per-task CPU and I/O footprint.
- **Production migration:** If this service were promoted to production, both SQLite and `BackgroundTasks` would need to be replaced. SQLite → PostgreSQL is a well-understood migration path with SQLAlchemy (change the connection URL and remove `check_same_thread`). `BackgroundTasks` → Celery/Kafka requires more significant refactoring of the ingestion dispatch layer.

---

## Links

- Related specs: [specs/requirements.md](../specs/requirements.md)
- Architecture overview: [architecture.md](../architecture.md)
- Task list: [tasks.md](../tasks.md)
- FastAPI BackgroundTasks documentation: https://fastapi.tiangolo.com/tutorial/background-tasks/
