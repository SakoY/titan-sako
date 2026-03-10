"""Tests for app/models/tenant.py (TASK-005)."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant


def test_tenant_auto_generates_uuid_id(db):
    """Tenant.id is auto-generated as a valid UUID string."""
    t = Tenant(name="acme", api_key="hashed_key")
    db.add(t)
    db.commit()
    db.refresh(t)

    assert t.id is not None
    uuid.UUID(t.id)  # raises ValueError if not a valid UUID


def test_tenant_id_unique_per_instance(db):
    """Each Tenant gets a distinct auto-generated ID."""
    t1 = Tenant(name="alpha", api_key="key_1")
    t2 = Tenant(name="beta", api_key="key_2")
    db.add_all([t1, t2])
    db.commit()

    assert t1.id != t2.id


def test_tenant_created_at_auto_set(db):
    """created_at is automatically set to a UTC datetime on insert."""
    before = datetime.now(timezone.utc)
    t = Tenant(name="lib", api_key="hashed")
    db.add(t)
    db.commit()
    db.refresh(t)
    after = datetime.now(timezone.utc)

    # SQLite strips timezone info; compare naive timestamps
    created = t.created_at.replace(tzinfo=timezone.utc) if t.created_at.tzinfo is None else t.created_at
    assert before <= created <= after


def test_tenant_round_trips_all_fields(db):
    """All Tenant fields survive a write-read round-trip."""
    t = Tenant(name="round-trip", api_key="hashed_val_xyz")
    db.add(t)
    db.commit()
    db.expunge(t)

    fetched = db.query(Tenant).filter_by(name="round-trip").one()
    assert fetched.name == "round-trip"
    assert fetched.api_key == "hashed_val_xyz"
    assert fetched.id is not None
    assert fetched.created_at is not None


def test_tenant_duplicate_name_raises_integrity_error(db):
    """Inserting two Tenants with the same name raises IntegrityError."""
    db.add(Tenant(name="duplicate", api_key="key_a"))
    db.commit()

    db.add(Tenant(name="duplicate", api_key="key_b"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_tenant_duplicate_api_key_raises_integrity_error(db):
    """Inserting two Tenants with the same api_key raises IntegrityError."""
    db.add(Tenant(name="tenant_x", api_key="shared_hash"))
    db.commit()

    db.add(Tenant(name="tenant_y", api_key="shared_hash"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_tenant_name_required(db):
    """Omitting name raises IntegrityError (NOT NULL constraint)."""
    db.add(Tenant(api_key="some_hash"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_tenant_api_key_required(db):
    """Omitting api_key raises IntegrityError (NOT NULL constraint)."""
    db.add(Tenant(name="no_key_tenant"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_tenant_explicit_id_is_respected(db):
    """A caller-provided id is stored as-is."""
    custom_id = str(uuid.uuid4())
    t = Tenant(id=custom_id, name="custom_id_tenant", api_key="hk")
    db.add(t)
    db.commit()
    db.refresh(t)

    assert t.id == custom_id


def test_multiple_tenants_are_independent(db):
    """Multiple distinct tenants can coexist."""
    tenants = [Tenant(name=f"lib_{i}", api_key=f"key_{i}") for i in range(5)]
    db.add_all(tenants)
    db.commit()

    stored = db.query(Tenant).all()
    assert len(stored) == 5
    names = {t.name for t in stored}
    assert names == {"lib_0", "lib_1", "lib_2", "lib_3", "lib_4"}
