from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """Read container environment variables supplied by Docker Compose."""

    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True)

    app_name: str = "Secure Attendance API"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"} or not url.host or not url.database:
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL with a host and database"
            )
        # Supabase supplies plain PostgreSQL URIs; use our installed Psycopg 3 driver.
        normalized = url.set(drivername="postgresql+psycopg")
        return SecretStr(normalized.render_as_string(hide_password=False))

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or "*" in origin
                or url.username is not None
                or url.password is not None
                or url.path
                or url.query
                or url.fragment
            ):
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins without paths")
            # Accessing port also validates malformed port numbers.
            _ = url.port
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
