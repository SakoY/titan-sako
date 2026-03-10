"""Work repository — upsert and query operations."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.work import Work


def upsert_work(db: Session, tenant_id: str, work_data: dict) -> Work:
    """
    Insert a new Work row or update an existing one matched on (tenant_id, ol_work_key).
    Sets ingested_at to the current UTC time on every upsert.
    Returns the persisted Work instance.
    """
    ol_work_key = work_data["key"]

    work = (
        db.query(Work)
        .filter_by(tenant_id=tenant_id, ol_work_key=ol_work_key)
        .first()
    )

    now = datetime.now(timezone.utc)

    if work is None:
        work = Work(
            tenant_id=tenant_id,
            ol_work_key=ol_work_key,
            title=work_data.get("title"),
            author_names=work_data.get("author_names"),
            first_publish_year=work_data.get("first_publish_year"),
            subjects=work_data.get("subjects"),
            cover_image_url=work_data.get("cover_image_url"),
            ingested_at=now,
        )
        db.add(work)
    else:
        work.title = work_data.get("title")
        work.author_names = work_data.get("author_names")
        work.first_publish_year = work_data.get("first_publish_year")
        work.subjects = work_data.get("subjects")
        work.cover_image_url = work_data.get("cover_image_url")
        work.ingested_at = now

    db.commit()
    db.refresh(work)
    return work
