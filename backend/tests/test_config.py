import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_read_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Backend")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("CORS_ORIGINS", '["https://attendance.example.com"]')
    settings = Settings()
    assert settings.app_name == "Test Backend"
    assert settings.environment == "production"
    assert settings.log_level == "WARNING"
    assert settings.cors_origins == ["https://attendance.example.com"]


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(ValidationError):
        Settings()


def test_settings_do_not_reveal_database_password(settings):
    assert "test_password" not in repr(settings)
    assert settings.database_url.get_secret_value().endswith("@db:5432/test")


@pytest.mark.parametrize(
    "url",
    ["not-a-url", "sqlite:///test.db", "postgresql+psycopg2://user:pass@db/test"],
)
def test_settings_reject_invalid_or_unsupported_database_url(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_supabase_connection_urls_use_installed_driver(monkeypatch, scheme):
    monkeypatch.setenv("DATABASE_URL", f"{scheme}://user:pass@db:5432/test")
    settings = Settings()
    assert settings.database_url.get_secret_value() == "postgresql+psycopg://user:pass@db:5432/test"


@pytest.mark.parametrize(
    "origins",
    [["*"], ["http://localhost:3000/"], ["https://example.com/path"], ["file:///tmp"]],
)
def test_settings_require_explicit_browser_origins(origins):
    with pytest.raises(ValidationError):
        Settings(cors_origins=origins)


def test_empty_origin_list_disables_browser_access():
    assert Settings(cors_origins=[]).cors_origins == []
