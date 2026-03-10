from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
import app.models.tenant  # noqa: F401 — registers Tenant with Base.metadata
import app.models.work  # noqa: F401 — registers Work with Base.metadata
import app.models.ingestion_log  # noqa: F401 — registers IngestionLog with Base.metadata
import app.models.reading_list  # noqa: F401 — registers ReadingList/ReadingListItem with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Open Library Catalog Service", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
