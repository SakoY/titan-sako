"""Tests for app/models/reading_list.py (TASK-008)."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.reading_list import ReadingList, ReadingListItem
from app.models.tenant import Tenant
from app.models.work import Work


@pytest.fixture()
def tenant(db):
    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def work(db, tenant):
    w = Work(tenant_id=tenant.id, ol_work_key="/works/OL1W", title="Dune")
    db.add(w)
    db.commit()
    return w


@pytest.fixture()
def reading_list(db, tenant):
    rl = ReadingList(
        tenant_id=tenant.id,
        patron_name_hash="name_hash_abc",
        patron_email_hash="email_hash_xyz",
    )
    db.add(rl)
    db.commit()
    return rl


def test_reading_list_auto_generates_uuid(db, reading_list):
    """ReadingList.id is auto-generated as a valid UUID string."""
    db.refresh(reading_list)
    uuid.UUID(reading_list.id)


def test_reading_list_submitted_at_auto_set(db, tenant):
    """submitted_at is automatically set on insert."""
    from datetime import datetime, timezone

    before = datetime.now(timezone.utc)
    rl = ReadingList(tenant_id=tenant.id, patron_name_hash="n", patron_email_hash="e")
    db.add(rl)
    db.commit()
    db.refresh(rl)
    after = datetime.now(timezone.utc)

    submitted = rl.submitted_at
    if submitted.tzinfo is None:
        submitted = submitted.replace(tzinfo=timezone.utc)
    assert before <= submitted <= after


def test_reading_list_round_trips_fields(db, tenant, reading_list):
    """All ReadingList fields survive a write-read round-trip."""
    rl_id = reading_list.id
    db.expunge(reading_list)

    fetched = db.query(ReadingList).filter_by(id=rl_id).one()
    assert fetched.patron_name_hash == "name_hash_abc"
    assert fetched.patron_email_hash == "email_hash_xyz"
    assert fetched.tenant_id == tenant.id


def test_reading_list_duplicate_patron_email_same_tenant_raises(db, tenant):
    """Duplicate (tenant_id, patron_email_hash) raises IntegrityError."""
    db.add(ReadingList(tenant_id=tenant.id, patron_name_hash="n1", patron_email_hash="same_hash"))
    db.commit()

    db.add(ReadingList(tenant_id=tenant.id, patron_name_hash="n2", patron_email_hash="same_hash"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_reading_list_same_email_hash_different_tenants_allowed(db):
    """Same patron_email_hash is allowed across different tenants."""
    t1 = Tenant(name="lib_a", api_key="key_a")
    t2 = Tenant(name="lib_b", api_key="key_b")
    db.add_all([t1, t2])
    db.commit()

    db.add(ReadingList(tenant_id=t1.id, patron_name_hash="n", patron_email_hash="shared_hash"))
    db.add(ReadingList(tenant_id=t2.id, patron_name_hash="n", patron_email_hash="shared_hash"))
    db.commit()  # should not raise

    assert db.query(ReadingList).count() == 2


def test_reading_list_item_resolved(db, reading_list, work):
    """A ReadingListItem can be stored with resolved status and a work FK."""
    item = ReadingListItem(
        reading_list_id=reading_list.id,
        book_reference="/works/OL1W",
        resolved_work_id=work.id,
        resolution_status="resolved",
    )
    db.add(item)
    db.commit()
    item_id = item.id
    db.expunge(item)

    fetched = db.query(ReadingListItem).filter_by(id=item_id).one()
    assert fetched.resolution_status == "resolved"
    assert fetched.resolved_work_id == work.id
    assert fetched.book_reference == "/works/OL1W"


def test_reading_list_item_unresolved(db, reading_list):
    """A ReadingListItem can be stored with unresolved status and no work FK."""
    item = ReadingListItem(
        reading_list_id=reading_list.id,
        book_reference="/works/OL999W",
        resolution_status="unresolved",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.resolution_status == "unresolved"
    assert item.resolved_work_id is None


def test_reading_list_item_default_status_is_unresolved(db, reading_list):
    """resolution_status defaults to 'unresolved' when not specified."""
    item = ReadingListItem(
        reading_list_id=reading_list.id,
        book_reference="/works/OL10W",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.resolution_status == "unresolved"


def test_reading_list_with_multiple_items_round_trips(db, reading_list, work):
    """A ReadingList with mixed resolved/unresolved items persists correctly."""
    items = [
        ReadingListItem(
            reading_list_id=reading_list.id,
            book_reference="/works/OL1W",
            resolved_work_id=work.id,
            resolution_status="resolved",
        ),
        ReadingListItem(
            reading_list_id=reading_list.id,
            book_reference="/works/OL2W",
            resolution_status="unresolved",
        ),
        ReadingListItem(
            reading_list_id=reading_list.id,
            book_reference="/works/OL3W",
            resolution_status="unresolved",
        ),
    ]
    db.add_all(items)
    db.commit()

    fetched = db.query(ReadingListItem).filter_by(reading_list_id=reading_list.id).all()
    assert len(fetched) == 3
    statuses = [i.resolution_status for i in fetched]
    assert statuses.count("resolved") == 1
    assert statuses.count("unresolved") == 2


def test_reading_list_item_reading_list_id_required(db):
    """Omitting reading_list_id raises IntegrityError."""
    db.add(ReadingListItem(book_reference="/works/OL1W"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_reading_list_tenant_isolation(db):
    """Two tenants can have distinct reading lists — no cross-tenant leakage."""
    t1 = Tenant(name="lib_a", api_key="key_a")
    t2 = Tenant(name="lib_b", api_key="key_b")
    db.add_all([t1, t2])
    db.commit()

    db.add(ReadingList(tenant_id=t1.id, patron_name_hash="n", patron_email_hash="e_t1"))
    db.add(ReadingList(tenant_id=t2.id, patron_name_hash="n", patron_email_hash="e_t2"))
    db.commit()

    t1_lists = db.query(ReadingList).filter_by(tenant_id=t1.id).all()
    t2_lists = db.query(ReadingList).filter_by(tenant_id=t2.id).all()
    assert len(t1_lists) == 1
    assert len(t2_lists) == 1
    assert t1_lists[0].patron_email_hash != t2_lists[0].patron_email_hash
