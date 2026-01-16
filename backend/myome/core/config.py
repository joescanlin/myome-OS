"""Application configuration using Pydantic Settings"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Myome"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database (supports PostgreSQL or SQLite for testing)
    database_url: str = Field(
        default="postgresql+asyncpg://myome:myome@localhost:5432/myome"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis (for caching and Celery)
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Security
    secret_key: str = Field(
        default="CHANGE-THIS-IN-PRODUCTION-USE-OPENSSL-RAND-HEX-32"
    )
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    refresh_token_expire_days: int = 30

    # Encryption (for hereditary artifacts)
    encryption_algorithm: str = "AES-256-GCM"

    # Data retention
    time_series_retention_years: int = 100  # Lifetime data

    # Sensor polling intervals (seconds)
    wearable_poll_interval: int = 60
    environmental_poll_interval: int = 300

    # Analytics
    correlation_min_samples: int = 30
    alert_significance_threshold: float = 0.01

    # OAuth - Whoop
    whoop_client_id: str = Field(default="")
    whoop_client_secret: str = Field(default="")
    whoop_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/oauth/callback/whoop"
    )

    # OAuth - Withings
    withings_client_id: str = Field(default="")
    withings_client_secret: str = Field(default="")
    withings_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/oauth/callback/withings"
    )

    # Frontend URL (for OAuth redirects back to UI)
    frontend_url: str = Field(default="http://localhost:3001")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
