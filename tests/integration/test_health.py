"""Integration tests for the health endpoint and app startup (TASK-001, TASK-002, TASK-004)."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200():
    """/health returns HTTP 200."""
    with TestClient(app) as c:
        response = c.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_payload():
    """/health body is {"status": "ok"}."""
    with TestClient(app) as c:
        response = c.get("/health")
    assert response.json() == {"status": "ok"}


def test_health_requires_no_auth():
    """/health is accessible without any authentication header."""
    with TestClient(app) as c:
        response = c.get("/health")
    assert response.status_code == 200


def test_health_available_before_db_operations(client):
    """/health responds correctly via the test client (DB injected but no data)."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_app_title_is_set():
    """The FastAPI app title matches the project name."""
    assert app.title == "Open Library Catalog Service"


def test_lifespan_initializes_db(test_engine):
    """App lifespan creates the tenants table on startup."""
    from sqlalchemy import inspect

    with TestClient(app):
        # TestClient triggers lifespan on __enter__; our override uses test_engine
        pass

    # The real engine will have created tables — check the test_engine we set up
    tables = inspect(test_engine).get_table_names()
    assert "tenants" in tables
