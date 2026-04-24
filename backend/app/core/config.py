"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe, validated configuration.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # App
    APP_NAME: str = "URL Shortener"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    BASE_URL: str = Field(default="http://localhost:8000")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CACHE_DEFAULT_TTL: int = Field(default=86400)  # 24 hours

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=10)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)

    # Short ID generation
    SHORT_ID_LENGTH: int = 7
    SHORT_ID_MAX_RETRIES: int = 5

    # CORS — stored as raw comma-separated string; split via the property below.
    # Kept as str (not List[str]) because pydantic-settings tries to json.loads()
    # list-typed env vars before validators run, which breaks `a,b,c` input.
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Split CORS_ORIGINS into a clean list at access time."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
