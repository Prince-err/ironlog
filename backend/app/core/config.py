"""Iron Log application configuration via pydantic-settings.

Reads gym/backend/.env (working directory must be gym/backend/ when running
uvicorn).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    database_url: str = "sqlite:///./ironlog.db"
    # Dev-only demo identity (mirrors the study app's X-Demo-Student-ID
    # pattern). Replace with real auth before production.
    demo_user_email: str = "demo@ironlog.app"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
