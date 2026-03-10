"""Works retrieval endpoints — list, filter, search, detail."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.work import Work

router = APIRouter(prefix="/api/v1", tags=["works"])


class WorkItem(BaseModel):
    id: str
    ol_work_key: str
    title: str | None
    author_names: list[str] | None
    first_publish_year: int | None
    subjects: list[str] | None
    cover_image_url: str | None


class WorkPage(BaseModel):
    items: list[WorkItem]
    total: int
    page: int
    page_size: int


def _to_item(w: Work) -> WorkItem:
    return WorkItem(
        id=w.id,
        ol_work_key=w.ol_work_key,
        title=w.title,
        author_names=w.author_names,
        first_publish_year=w.first_publish_year,
        subjects=w.subjects,
        cover_image_url=w.cover_image_url,
    )


@router.get("/works/search", response_model=WorkPage)
def search_works(
    q: str = Query(..., description="Keyword to search in title and author_names"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """
    Case-insensitive keyword search across title and author_names.
    Must be registered before /works/{work_id} to avoid route shadowing.
    """
    from sqlalchemy import cast, String
    term = f"%{q}%"
    base_q = (
        db.query(Work)
        .filter(Work.tenant_id == tenant.id)
        .filter(
            Work.title.ilike(term)
            | cast(Work.author_names, String).ilike(term)
        )
    )
    total = base_q.count()
    items = base_q.offset((page - 1) * page_size).limit(page_size).all()
    return WorkPage(items=[_to_item(w) for w in items], total=total, page=page, page_size=page_size)


@router.get("/works", response_model=WorkPage)
def list_works(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    author: str | None = Query(None, description="Case-insensitive substring match on author_names"),
    subject: str | None = Query(None, description="Case-insensitive substring match on subjects"),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """List works for the tenant with optional filters."""
    from sqlalchemy import cast, String

    q = db.query(Work).filter(Work.tenant_id == tenant.id)

    if author is not None:
        q = q.filter(cast(Work.author_names, String).ilike(f"%{author}%"))
    if subject is not None:
        q = q.filter(cast(Work.subjects, String).ilike(f"%{subject}%"))
    if year_from is not None:
        q = q.filter(Work.first_publish_year >= year_from)
    if year_to is not None:
        q = q.filter(Work.first_publish_year <= year_to)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return WorkPage(items=[_to_item(w) for w in items], total=total, page=page, page_size=page_size)


@router.get("/works/{work_id}", response_model=WorkItem)
def get_work(
    work_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """Return a single work by ID. 404 if not found or belongs to another tenant."""
    work = db.query(Work).filter_by(id=work_id, tenant_id=tenant.id).first()
    if work is None:
        raise HTTPException(status_code=404, detail="Work not found")
    return _to_item(work)
