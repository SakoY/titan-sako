"""IngestionLog repository — create and update log rows."""

from sqlalchemy.orm import Session

from app.models.ingestion_log import IngestionLog


def create_log(db: Session, tenant_id: str, query_type: str, query_value: str) -> IngestionLog:
    """Create a new IngestionLog row with status='pending'."""
    log = IngestionLog(
        tenant_id=tenant_id,
        query_type=query_type,
        query_value=query_value,
        status="pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_log(db: Session, log_id: str, **fields) -> IngestionLog:
    """Update any combination of fields on an IngestionLog row."""
    log = db.query(IngestionLog).filter_by(id=log_id).one()
    for key, value in fields.items():
        setattr(log, key, value)
    db.commit()
    db.refresh(log)
    return log
