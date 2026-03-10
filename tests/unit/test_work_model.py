"""Tests for app/models/work.py (TASK-006)."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant
from app.models.work import Work


@pytest.fixture()
def tenant(db):
    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()
    return t


def test_work_auto_generates_uuid_id(db, tenant):
    """Work.id is auto-generated as a valid UUID string."""
    w = Work(tenant_id=tenant.id, ol_work_key="/works/OL1W", title="Book")
    db.add(w)
    db.commit()
    db.refresh(w)

    uuid.UUID(w.id)  # raises if not valid


def test_work_round_trips_all_fields(db, tenant):
    """All Work fields survive a write-read round-trip including JSON columns."""
    w = Work(
        tenant_id=tenant.id,
        ol_work_key="/works/OL42W",
        title="Dune",
        author_names=["Frank Herbert"],
        first_publish_year=1965,
        subjects=["science fiction", "desert"],
        cover_image_url="https://covers.openlibrary.org/b/id/1-M.jpg",
    )
    db.add(w)
    db.commit()
    work_id = w.id
    db.expunge(w)

    fetched = db.query(Work).filter_by(id=work_id).one()
    assert fetched.title == "Dune"
    assert fetched.author_names == ["Frank Herbert"]
    assert fetched.first_publish_year == 1965
    assert fetched.subjects == ["science fiction", "desert"]
    assert fetched.cover_image_url == "https://covers.openlibrary.org/b/id/1-M.jpg"
    assert fetched.tenant_id == tenant.id


def test_work_nullable_fields_accept_none(db, tenant):
    """title, author_names, first_publish_year, subjects, cover_image_url are all nullable."""
    w = Work(tenant_id=tenant.id, ol_work_key="/works/OL99W")
    db.add(w)
    db.commit()
    db.refresh(w)

    assert w.title is None
    assert w.author_names is None
    assert w.first_publish_year is None
    assert w.subjects is None
    assert w.cover_image_url is None


def test_work_ingested_at_auto_set(db, tenant):
    """ingested_at is automatically set to a UTC datetime on insert."""
    before = datetime.now(timezone.utc)
    w = Work(tenant_id=tenant.id, ol_work_key="/works/OL2W")
    db.add(w)
    db.commit()
    db.refresh(w)
    after = datetime.now(timezone.utc)

    ingested = w.ingested_at
    if ingested.tzinfo is None:
        ingested = ingested.replace(tzinfo=timezone.utc)
    assert before <= ingested <= after


def test_work_duplicate_tenant_ol_work_key_raises(db, tenant):
    """Duplicate (tenant_id, ol_work_key) raises IntegrityError."""
    db.add(Work(tenant_id=tenant.id, ol_work_key="/works/OL1W", title="First"))
    db.commit()

    db.add(Work(tenant_id=tenant.id, ol_work_key="/works/OL1W", title="Second"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_work_same_ol_work_key_different_tenants_allowed(db):
    """Same ol_work_key is allowed for different tenants."""
    t1 = Tenant(name="lib_a", api_key="key_a")
    t2 = Tenant(name="lib_b", api_key="key_b")
    db.add_all([t1, t2])
    db.commit()

    db.add(Work(tenant_id=t1.id, ol_work_key="/works/OL1W", title="Copy A"))
    db.add(Work(tenant_id=t2.id, ol_work_key="/works/OL1W", title="Copy B"))
    db.commit()  # should not raise

    assert db.query(Work).count() == 2


def test_work_json_author_names_multiple_entries(db, tenant):
    """author_names stores and retrieves a list with multiple entries."""
    w = Work(
        tenant_id=tenant.id,
        ol_work_key="/works/OL3W",
        author_names=["Author A", "Author B", "Author C"],
    )
    db.add(w)
    db.commit()
    work_id = w.id
    db.expunge(w)

    fetched = db.query(Work).filter_by(id=work_id).one()
    assert len(fetched.author_names) == 3
    assert "Author B" in fetched.author_names


def test_work_tenant_id_required(db):
    """Omitting tenant_id raises IntegrityError."""
    db.add(Work(ol_work_key="/works/OL5W"))
    with pytest.raises(IntegrityError):
        db.commit()
