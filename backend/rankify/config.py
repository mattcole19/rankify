from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or `.env`."""

    environment: Annotated[str, Field(alias='ENVIRONMENT')] = 'local'
    database_url: Annotated[str, Field(alias='DATABASE_URL')] = (
        'postgresql+psycopg://rankify:rankify@localhost:5432/rankify'
    )
    cors_allow_origins: Annotated[list[str], Field(alias='CORS_ALLOW_ORIGINS')] = [
        'http://localhost:5173'
    ]

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    @field_validator('cors_allow_origins', mode='before')
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(',') if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
