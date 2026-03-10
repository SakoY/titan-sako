"""Tests for app/services/reading_list.py (TASK-028)."""

import pytest

from app.models.tenant import Tenant
from app.models.work import Work
from app.services.reading_list import resolve_book_references


@pytest.fixture()
def tenant(db):
    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()
    return t


def _seed_work(db, tenant_id, key):
    w = Work(tenant_id=tenant_id, ol_work_key=key, title="T")
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def test_resolve_known_reference(db, tenant):
    w = _seed_work(db, tenant.id, "/works/OL1W")
    result = resolve_book_references(db, tenant.id, ["/works/OL1W"])
    assert result["/works/OL1W"] is not None
    assert result["/works/OL1W"].id == w.id


def test_resolve_unknown_reference_returns_none(db, tenant):
    result = resolve_book_references(db, tenant.id, ["/works/OLunknownW"])
    assert result["/works/OLunknownW"] is None


def test_resolve_other_tenant_reference_returns_none(db):
    t1 = Tenant(name="t1", api_key="k1")
    t2 = Tenant(name="t2", api_key="k2")
    db.add_all([t1, t2])
    db.commit()
    _seed_work(db, t2.id, "/works/OL1W")
    result = resolve_book_references(db, t1.id, ["/works/OL1W"])
    assert result["/works/OL1W"] is None


def test_resolve_mixed_references(db, tenant):
    _seed_work(db, tenant.id, "/works/OL1W")
    result = resolve_book_references(db, tenant.id, ["/works/OL1W", "/works/OLmissW"])
    assert result["/works/OL1W"] is not None
    assert result["/works/OLmissW"] is None


def test_resolve_empty_list_returns_empty_dict(db, tenant):
    result = resolve_book_references(db, tenant.id, [])
    assert result == {}


def test_resolve_multiple_known_references(db, tenant):
    _seed_work(db, tenant.id, "/works/OL1W")
    _seed_work(db, tenant.id, "/works/OL2W")
    result = resolve_book_references(db, tenant.id, ["/works/OL1W", "/works/OL2W"])
    assert result["/works/OL1W"] is not None
    assert result["/works/OL2W"] is not None
