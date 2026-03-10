"""Reading list service — book reference resolution."""

from sqlalchemy.orm import Session

from app.models.work import Work


def resolve_book_references(
    db: Session,
    tenant_id: str,
    references: list[str],
) -> dict[str, Work | None]:
    """
    Look up each reference against Work rows for the tenant.
    References are matched against ol_work_key.
    Returns a mapping of reference → Work (or None if not found for this tenant).
    """
    if not references:
        return {}

    works = (
        db.query(Work)
        .filter(Work.tenant_id == tenant_id, Work.ol_work_key.in_(references))
        .all()
    )
    work_by_key = {w.ol_work_key: w for w in works}
    return {ref: work_by_key.get(ref) for ref in references}
