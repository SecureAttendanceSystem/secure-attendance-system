import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings

TEST_DATABASE_URL = "postgresql+psycopg://test:test_password@db:5432/test"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    # The test process never uses the developer's Supabase connection.
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def app(settings):
    from app.main import create_app

    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
