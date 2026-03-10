from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
import app.models.tenant  # noqa: F401 — registers Tenant with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Open Library Catalog Service", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
