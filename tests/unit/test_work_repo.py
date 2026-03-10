"""Tests for app/repositories/work_repo.py (TASK-014)."""

from datetime import datetime, timezone

import pytest

from app.models.tenant import Tenant
from app.models.work import Work
from app.repositories.work_repo import upsert_work


@pytest.fixture()
def tenant(db):
    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()
    return t


def _work_data(**overrides) -> dict:
    base = {
        "key": "/works/OL1W",
        "title": "Dune",
        "author_names": ["Frank Herbert"],
        "first_publish_year": 1965,
        "subjects": ["science fiction"],
        "cover_image_url": "https://covers.openlibrary.org/b/id/1-M.jpg",
    }
    return {**base, **overrides}


def test_upsert_work_inserts_new_row(db, tenant):
    """First upsert for a key inserts a new Work row."""
    upsert_work(db, tenant.id, _work_data())
    assert db.query(Work).filter_by(tenant_id=tenant.id).count() == 1


def test_upsert_work_returns_work_instance(db, tenant):
    """upsert_work returns a persisted Work instance."""
    w = upsert_work(db, tenant.id, _work_data())
    assert isinstance(w, Work)
    assert w.id is not None
    assert w.ol_work_key == "/works/OL1W"


def test_upsert_work_second_call_does_not_create_duplicate(db, tenant):
    """Calling upsert_work twice with the same key results in exactly one row."""
    upsert_work(db, tenant.id, _work_data())
    upsert_work(db, tenant.id, _work_data(title="Updated"))
    assert db.query(Work).filter_by(tenant_id=tenant.id).count() == 1


def test_upsert_work_updates_title_on_second_call(db, tenant):
    """Second upsert with a changed title updates the existing row."""
    upsert_work(db, tenant.id, _work_data(title="Original"))
    w = upsert_work(db, tenant.id, _work_data(title="Revised"))
    assert w.title == "Revised"


def test_upsert_work_updates_author_names_on_second_call(db, tenant):
    """Second upsert updates author_names."""
    upsert_work(db, tenant.id, _work_data(author_names=["Old Author"]))
    w = upsert_work(db, tenant.id, _work_data(author_names=["New Author A", "New Author B"]))
    assert w.author_names == ["New Author A", "New Author B"]


def test_upsert_work_sets_ingested_at_on_insert(db, tenant):
    """ingested_at is set to current UTC time on insert."""
    before = datetime.now(timezone.utc)
    w = upsert_work(db, tenant.id, _work_data())
    after = datetime.now(timezone.utc)

    ingested = w.ingested_at
    if ingested.tzinfo is None:
        ingested = ingested.replace(tzinfo=timezone.utc)
    assert before <= ingested <= after


def test_upsert_work_refreshes_ingested_at_on_update(db, tenant):
    """ingested_at is updated on every upsert call."""
    w1 = upsert_work(db, tenant.id, _work_data())
    first_ingested = w1.ingested_at

    w2 = upsert_work(db, tenant.id, _work_data(title="V2"))
    second_ingested = w2.ingested_at

    assert second_ingested >= first_ingested


def test_upsert_work_different_tenants_create_separate_rows(db):
    """Same ol_work_key for different tenants creates two independent rows."""
    t1 = Tenant(name="lib_a", api_key="k1")
    t2 = Tenant(name="lib_b", api_key="k2")
    db.add_all([t1, t2])
    db.commit()

    upsert_work(db, t1.id, _work_data(title="Copy A"))
    upsert_work(db, t2.id, _work_data(title="Copy B"))

    assert db.query(Work).count() == 2
    assert db.query(Work).filter_by(tenant_id=t1.id).one().title == "Copy A"
    assert db.query(Work).filter_by(tenant_id=t2.id).one().title == "Copy B"


def test_upsert_work_persists_all_fields(db, tenant):
    """All work_data fields are correctly written to the DB."""
    data = _work_data(
        title="Foundation",
        author_names=["Isaac Asimov"],
        first_publish_year=1951,
        subjects=["science fiction", "robots"],
        cover_image_url="https://covers.openlibrary.org/b/id/99-M.jpg",
    )
    work_id = upsert_work(db, tenant.id, data).id
    db.expunge_all()

    fetched = db.query(Work).filter_by(id=work_id).one()
    assert fetched.title == "Foundation"
    assert fetched.author_names == ["Isaac Asimov"]
    assert fetched.first_publish_year == 1951
    assert fetched.subjects == ["science fiction", "robots"]
    assert fetched.cover_image_url == "https://covers.openlibrary.org/b/id/99-M.jpg"


def test_upsert_work_nullable_fields_accept_none(db, tenant):
    """cover_image_url and other optional fields can be None."""
    w = upsert_work(db, tenant.id, _work_data(cover_image_url=None, first_publish_year=None))
    assert w.cover_image_url is None
    assert w.first_publish_year is None
