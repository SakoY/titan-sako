"""Reading list endpoints — submit and retrieve."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_tenant
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_pii
from app.models.reading_list import ReadingList, ReadingListItem
from app.models.tenant import Tenant
from app.services.reading_list import resolve_book_references

router = APIRouter(prefix="/api/v1", tags=["reading-lists"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ReadingListSubmit(BaseModel):
    patron_name: str
    patron_email: str
    books: list[str]


class ReadingListSubmitted(BaseModel):
    reading_list_id: str
    resolved: list[str]
    unresolved: list[str]


class ReadingListItemOut(BaseModel):
    id: str
    book_reference: str
    resolved_work_id: str | None
    resolution_status: str


class ReadingListDetail(BaseModel):
    id: str
    patron_name_hash: str
    patron_email_hash: str
    submitted_at: datetime
    items: list[ReadingListItemOut]


class ReadingListSummary(BaseModel):
    id: str
    patron_name_hash: str
    patron_email_hash: str
    submitted_at: datetime
    item_count: int


class ReadingListPage(BaseModel):
    items: list[ReadingListSummary]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# POST /api/v1/reading-lists
# ---------------------------------------------------------------------------


@router.post("/reading-lists", response_model=ReadingListSubmitted, status_code=201)
def submit_reading_list(
    body: ReadingListSubmit,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """
    Accept a patron reading list. Hashes PII before storage.
    Upserts on (tenant_id, patron_email_hash) — a second submission from the
    same patron replaces their items rather than creating a duplicate row.
    """
    name_hash = hash_pii(body.patron_name, settings.SECRET_KEY)
    email_hash = hash_pii(body.patron_email, settings.SECRET_KEY)

    # Upsert ReadingList
    reading_list = (
        db.query(ReadingList)
        .filter_by(tenant_id=tenant.id, patron_email_hash=email_hash)
        .first()
    )
    if reading_list is None:
        reading_list = ReadingList(
            tenant_id=tenant.id,
            patron_name_hash=name_hash,
            patron_email_hash=email_hash,
        )
        db.add(reading_list)
        db.flush()
    else:
        reading_list.patron_name_hash = name_hash
        # Delete existing items before re-inserting
        db.query(ReadingListItem).filter_by(reading_list_id=reading_list.id).delete()

    # Resolve references
    resolution = resolve_book_references(db, tenant.id, body.books)

    resolved_refs = []
    unresolved_refs = []
    for ref in body.books:
        work = resolution.get(ref)
        item = ReadingListItem(
            reading_list_id=reading_list.id,
            book_reference=ref,
            resolved_work_id=work.id if work else None,
            resolution_status="resolved" if work else "unresolved",
        )
        db.add(item)
        if work:
            resolved_refs.append(ref)
        else:
            unresolved_refs.append(ref)

    db.commit()
    db.refresh(reading_list)

    return ReadingListSubmitted(
        reading_list_id=reading_list.id,
        resolved=resolved_refs,
        unresolved=unresolved_refs,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/reading-lists
# ---------------------------------------------------------------------------


@router.get("/reading-lists", response_model=ReadingListPage)
def list_reading_lists(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """List reading lists for the tenant."""
    q = db.query(ReadingList).filter_by(tenant_id=tenant.id)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    summaries = []
    for rl in rows:
        item_count = db.query(ReadingListItem).filter_by(reading_list_id=rl.id).count()
        summaries.append(ReadingListSummary(
            id=rl.id,
            patron_name_hash=rl.patron_name_hash,
            patron_email_hash=rl.patron_email_hash,
            submitted_at=rl.submitted_at,
            item_count=item_count,
        ))
    return ReadingListPage(items=summaries, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /api/v1/reading-lists/{reading_list_id}
# ---------------------------------------------------------------------------


@router.get("/reading-lists/{reading_list_id}", response_model=ReadingListDetail)
def get_reading_list(
    reading_list_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(require_tenant),
):
    """Return a reading list with all items. 404 if not found or wrong tenant."""
    rl = db.query(ReadingList).filter_by(id=reading_list_id, tenant_id=tenant.id).first()
    if rl is None:
        raise HTTPException(status_code=404, detail="Reading list not found")

    items = db.query(ReadingListItem).filter_by(reading_list_id=rl.id).all()
    return ReadingListDetail(
        id=rl.id,
        patron_name_hash=rl.patron_name_hash,
        patron_email_hash=rl.patron_email_hash,
        submitted_at=rl.submitted_at,
        items=[
            ReadingListItemOut(
                id=item.id,
                book_reference=item.book_reference,
                resolved_work_id=item.resolved_work_id,
                resolution_status=item.resolution_status,
            )
            for item in items
        ],
    )
