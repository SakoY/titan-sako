"""Ingestion log endpoints — list and detail."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_tenant
from app.core.database import get_db
from app.models.ingestion_log import IngestionLog
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/v1", tags=["logs"])


class LogSummary(BaseModel):
    id: str
    tenant_id: str
    query_type: str
    query_value: str
    status: str
    fetched_count: int
    succeeded_count: int
    failed_count: int
    error_details: str | None
    started_at: datetime
    finished_at: datetime | None


class LogPage(BaseModel):
    items: list[LogSummary]
    total: int
    page: int
    page_size: int


def _to_summary(log: IngestionLog) -> LogSummary:
    return LogSummary(
        id=log.id,
        tenant_id=log.tenant_id,
        query_type=log.query_type,
        query_value=log.query_value,
        status=log.status,
        fetched_count=log.fetched_count,
        succeeded_count=log.succeeded_count,
        failed_count=log.failed_count,
        error_details=log.error_details,
        started_at=log.started_at,
        finished_at=log.finished_at,
    )


@router.get("/ingestion-logs", response_model=LogPage)
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """List ingestion logs for the tenant, newest first."""
    q = (
        db.query(IngestionLog)
        .filter(IngestionLog.tenant_id == tenant.id)
        .order_by(IngestionLog.started_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return LogPage(items=[_to_summary(log) for log in items], total=total, page=page, page_size=page_size)


@router.get("/ingestion-logs/{log_id}", response_model=LogSummary)
def get_log(
    log_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """Return a single ingestion log. 404 if not found or belongs to another tenant."""
    log = db.query(IngestionLog).filter_by(id=log_id, tenant_id=tenant.id).first()
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return _to_summary(log)
