import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReadingList(Base):
    __tablename__ = "reading_lists"
    __table_args__ = (
        UniqueConstraint("tenant_id", "patron_email_hash", name="uq_reading_list_tenant_patron"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id"), nullable=False
    )
    patron_name_hash: Mapped[str] = mapped_column(String, nullable=False)
    patron_email_hash: Mapped[str] = mapped_column(String, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ReadingListItem(Base):
    __tablename__ = "reading_list_items"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    reading_list_id: Mapped[str] = mapped_column(
        String, ForeignKey("reading_lists.id"), nullable=False
    )
    book_reference: Mapped[str] = mapped_column(String, nullable=False)
    resolved_work_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("works.id"), nullable=True
    )
    resolution_status: Mapped[str] = mapped_column(
        String, nullable=False, default="unresolved"
    )  # "resolved" | "unresolved"
