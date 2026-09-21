"""Weather Station API — Configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://weather:password@localhost:5432/weatherdb"

    # Security
    api_secret_key: str = "change-me-in-production"

    # CORS
    allowed_origins: str = "*"

    # App
    app_name: str = "Weather Station API"
    app_version: str = "1.0.0"
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
