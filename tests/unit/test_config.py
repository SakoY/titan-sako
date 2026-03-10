"""Tests for app/core/config.py (TASK-003)."""

import pytest
from pydantic import ValidationError


def test_settings_loads_required_fields(monkeypatch):
    """Settings instantiates correctly when all required env vars are present."""
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("OL_BASE_URL", "https://openlibrary.org")

    # Re-import to pick up monkeypatched env
    from importlib import reload
    import app.core.config as config_module

    reload(config_module)
    s = config_module.Settings()

    assert s.SECRET_KEY == "test-secret"
    assert s.DATABASE_URL == "sqlite:///./test.db"
    assert s.OL_BASE_URL == "https://openlibrary.org"
    assert s.OL_MAX_CONCURRENT_REQUESTS == 5


def test_settings_missing_secret_key_raises(monkeypatch):
    """Missing SECRET_KEY raises a ValidationError."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("OL_BASE_URL", "https://openlibrary.org")

    from importlib import reload
    import app.core.config as config_module

    with pytest.raises(ValidationError):
        config_module.Settings(_env_file=None)


def test_settings_missing_database_url_raises(monkeypatch):
    """Missing DATABASE_URL raises a ValidationError."""
    monkeypatch.setenv("SECRET_KEY", "s")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("OL_BASE_URL", "https://openlibrary.org")

    from importlib import reload
    import app.core.config as config_module

    with pytest.raises(ValidationError):
        config_module.Settings(_env_file=None)


def test_settings_missing_ol_base_url_raises(monkeypatch):
    """Missing OL_BASE_URL raises a ValidationError."""
    monkeypatch.setenv("SECRET_KEY", "s")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.delenv("OL_BASE_URL", raising=False)

    from importlib import reload
    import app.core.config as config_module

    with pytest.raises(ValidationError):
        config_module.Settings(_env_file=None)


def test_settings_ol_max_concurrent_requests_default(monkeypatch):
    """OL_MAX_CONCURRENT_REQUESTS defaults to 5 when not set."""
    monkeypatch.setenv("SECRET_KEY", "s")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("OL_BASE_URL", "https://openlibrary.org")
    monkeypatch.delenv("OL_MAX_CONCURRENT_REQUESTS", raising=False)

    from importlib import reload
    import app.core.config as config_module

    s = config_module.Settings(_env_file=None)
    assert s.OL_MAX_CONCURRENT_REQUESTS == 5


def test_settings_ol_max_concurrent_requests_overridable(monkeypatch):
    """OL_MAX_CONCURRENT_REQUESTS can be overridden via env."""
    monkeypatch.setenv("SECRET_KEY", "s")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("OL_BASE_URL", "https://openlibrary.org")
    monkeypatch.setenv("OL_MAX_CONCURRENT_REQUESTS", "10")

    from importlib import reload
    import app.core.config as config_module

    s = config_module.Settings(_env_file=None)
    assert s.OL_MAX_CONCURRENT_REQUESTS == 10


def test_settings_returns_typed_values(monkeypatch):
    """Settings fields are correctly typed (str vs int)."""
    monkeypatch.setenv("SECRET_KEY", "my-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./catalog.db")
    monkeypatch.setenv("OL_BASE_URL", "https://openlibrary.org")
    monkeypatch.setenv("OL_MAX_CONCURRENT_REQUESTS", "3")

    from importlib import reload
    import app.core.config as config_module

    s = config_module.Settings(_env_file=None)
    assert isinstance(s.SECRET_KEY, str)
    assert isinstance(s.DATABASE_URL, str)
    assert isinstance(s.OL_BASE_URL, str)
    assert isinstance(s.OL_MAX_CONCURRENT_REQUESTS, int)
