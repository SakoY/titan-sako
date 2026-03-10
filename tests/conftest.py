"""Shared fixtures for the entire test suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def test_engine():
    """In-memory SQLite engine with all tables created."""
    import app.models.tenant  # noqa: F401
    import app.models.work  # noqa: F401
    import app.models.ingestion_log  # noqa: F401
    import app.models.reading_list  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(test_engine):
    """SQLAlchemy session bound to the in-memory test DB."""
    Session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_engine):
    """FastAPI TestClient with the test DB injected via dependency override."""
    Session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
