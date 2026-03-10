"""Tests for app/core/database.py (TASK-004)."""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import app.models.tenant  # noqa: F401 — registers Tenant with Base.metadata
from app.core.database import Base, get_db


@pytest.fixture()
def mem_engine():
    """Fresh in-memory engine — no tables pre-created."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


def test_init_db_creates_tables(mem_engine):
    """create_all registers all declared tables in the DB."""
    Base.metadata.create_all(bind=mem_engine)

    names = inspect(mem_engine).get_table_names()
    assert "tenants" in names


def test_init_db_is_idempotent(mem_engine):
    """Calling create_all twice does not raise."""
    Base.metadata.create_all(bind=mem_engine)
    Base.metadata.create_all(bind=mem_engine)  # second call is safe


def test_get_db_yields_usable_session(test_engine):
    """get_db yields a session that can execute queries against the DB."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        session.close()


def test_get_db_closes_on_teardown(test_engine):
    """get_db closes the session after the generator is exhausted."""
    import app.core.database as db_module
    from unittest.mock import patch, MagicMock

    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(db_module, "SessionLocal", mock_factory):
        gen = db_module.get_db()
        session = next(gen)
        assert session is mock_session
        try:
            next(gen)
        except StopIteration:
            pass

    mock_session.close.assert_called_once()


def test_get_db_closes_on_exception(test_engine):
    """get_db closes the session even when the consumer raises."""
    import app.core.database as db_module
    from unittest.mock import patch, MagicMock

    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(db_module, "SessionLocal", mock_factory):
        gen = db_module.get_db()
        next(gen)
        try:
            gen.throw(RuntimeError("simulated error"))
        except RuntimeError:
            pass

    mock_session.close.assert_called_once()
