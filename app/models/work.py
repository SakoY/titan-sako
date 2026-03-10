import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (UniqueConstraint("tenant_id", "ol_work_key", name="uq_work_tenant_ol_key"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id"), nullable=False
    )
    ol_work_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    author_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    first_publish_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subjects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
