"""Ingestion trigger endpoint."""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.repositories.log_repo import create_log
from app.services.ingestion import run_ingestion
from app.services.ol_client import OLClient

router = APIRouter(prefix="/api/v1", tags=["ingestion"])

_VALID_QUERY_TYPES = {"author", "subject"}


class IngestRequest(BaseModel):
    query_type: str  # "author" | "subject"
    query_value: str


class IngestAccepted(BaseModel):
    log_id: str
    status: str = "pending"


@router.post("/ingest", response_model=IngestAccepted, status_code=202)
def trigger_ingestion(
    body: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """
    Start a catalog ingestion job for the authenticated tenant.
    Returns 202 immediately with a log_id to poll for progress.
    The actual ingestion runs in the background via FastAPI BackgroundTasks.
    """
    if body.query_type not in _VALID_QUERY_TYPES:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail=f"query_type must be one of: {sorted(_VALID_QUERY_TYPES)}",
        )

    log = create_log(db, tenant.id, body.query_type, body.query_value)

    ol_client = OLClient()
    background_tasks.add_task(
        run_ingestion,
        db,
        ol_client,
        tenant.id,
        body.query_type,
        body.query_value,
        log.id,
    )

    return IngestAccepted(log_id=log.id)
