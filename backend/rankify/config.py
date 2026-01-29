from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or `.env`."""

    environment: Annotated[str, Field(alias='ENVIRONMENT')] = 'local'
    database_url: Annotated[str, Field(alias='DATABASE_URL')] = (
        'postgresql+psycopg://rankify:rankify@localhost:5432/rankify'
    )

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
