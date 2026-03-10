"""Tests for app/models/ingestion_log.py (TASK-007)."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.ingestion_log import IngestionLog
from app.models.tenant import Tenant


@pytest.fixture()
def tenant(db):
    t = Tenant(name="acme", api_key="hk")
    db.add(t)
    db.commit()
    return t


def _make_log(db, tenant, **kwargs):
    defaults = dict(tenant_id=tenant.id, query_type="author", query_value="Tolkien")
    defaults.update(kwargs)
    log = IngestionLog(**defaults)
    db.add(log)
    db.commit()
    return log


def test_ingestion_log_auto_generates_uuid(db, tenant):
    """id is auto-generated as a valid UUID string."""
    log = _make_log(db, tenant)
    db.refresh(log)
    uuid.UUID(log.id)


def test_ingestion_log_defaults_on_insert(db, tenant):
    """status defaults to 'pending', counts default to 0, finished_at defaults to None."""
    log = _make_log(db, tenant)
    db.refresh(log)

    assert log.status == "pending"
    assert log.fetched_count == 0
    assert log.succeeded_count == 0
    assert log.failed_count == 0
    assert log.finished_at is None
    assert log.error_details is None


def test_ingestion_log_started_at_auto_set(db, tenant):
    """started_at is automatically set to a UTC datetime on insert."""
    before = datetime.now(timezone.utc)
    log = _make_log(db, tenant)
    db.refresh(log)
    after = datetime.now(timezone.utc)

    started = log.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    assert before <= started <= after


def test_ingestion_log_round_trips_all_fields(db, tenant):
    """All fields survive a write-read round-trip."""
    log = _make_log(db, tenant, query_type="subject", query_value="science fiction")
    log_id = log.id
    db.expunge(log)

    fetched = db.query(IngestionLog).filter_by(id=log_id).one()
    assert fetched.query_type == "subject"
    assert fetched.query_value == "science fiction"
    assert fetched.tenant_id == tenant.id


def test_ingestion_log_status_transition_to_completed(db, tenant):
    """A log row can be updated from pending to completed with finished_at set."""
    log = _make_log(db, tenant)
    log_id = log.id

    log.status = "completed"
    log.fetched_count = 10
    log.succeeded_count = 9
    log.failed_count = 1
    log.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.expunge(log)

    fetched = db.query(IngestionLog).filter_by(id=log_id).one()
    assert fetched.status == "completed"
    assert fetched.fetched_count == 10
    assert fetched.succeeded_count == 9
    assert fetched.failed_count == 1
    assert fetched.finished_at is not None


def test_ingestion_log_status_transition_to_failed(db, tenant):
    """A log can transition to failed with error_details populated."""
    log = _make_log(db, tenant)
    log_id = log.id

    log.status = "failed"
    log.error_details = "OL API returned 503"
    log.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.expunge(log)

    fetched = db.query(IngestionLog).filter_by(id=log_id).one()
    assert fetched.status == "failed"
    assert fetched.error_details == "OL API returned 503"
    assert fetched.finished_at is not None


def test_ingestion_log_running_status(db, tenant):
    """status can be set to 'running' during an active ingestion."""
    log = _make_log(db, tenant)
    log_id = log.id

    log.status = "running"
    log.fetched_count = 50
    db.commit()
    db.expunge(log)

    fetched = db.query(IngestionLog).filter_by(id=log_id).one()
    assert fetched.status == "running"
    assert fetched.fetched_count == 50
    assert fetched.finished_at is None


def test_ingestion_log_tenant_id_required(db):
    """Omitting tenant_id raises IntegrityError."""
    db.add(IngestionLog(query_type="author", query_value="test"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_multiple_logs_per_tenant(db, tenant):
    """Multiple ingestion log rows can exist for the same tenant."""
    _make_log(db, tenant, query_value="Tolkien")
    _make_log(db, tenant, query_value="Herbert")

    logs = db.query(IngestionLog).filter_by(tenant_id=tenant.id).all()
    assert len(logs) == 2
    values = {l.query_value for l in logs}
    assert values == {"Tolkien", "Herbert"}
