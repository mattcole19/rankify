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
    admin_secret: Annotated[str | None, Field(alias='ADMIN_SECRET')] = None  # Temporary
    supabase_url: Annotated[str | None, Field(alias='SUPABASE_URL')] = None
    supabase_anon_key: Annotated[str | None, Field(alias='SUPABASE_ANON_KEY')] = None
    admin_emails: Annotated[list[str], Field(alias='ADMIN_EMAILS')] = []
    allow_repeat_submissions: Annotated[bool | None, Field(alias='ALLOW_REPEAT_SUBMISSIONS')] = None
    sentry_dsn: Annotated[str | None, Field(alias='SENTRY_DSN')] = None
    sentry_environment: Annotated[str | None, Field(alias='SENTRY_ENVIRONMENT')] = None
    sentry_traces_sample_rate: Annotated[
        float, Field(alias='SENTRY_TRACES_SAMPLE_RATE')
    ] = 0.0

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    @field_validator('cors_allow_origins', mode='before')
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(',') if origin.strip()]

    @field_validator('database_url', mode='before')
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if value.startswith('postgres://'):
            return value.replace('postgres://', 'postgresql+psycopg://', 1)
        if value.startswith('postgresql://') and '+psycopg' not in value.split('://', 1)[0]:
            return value.replace('postgresql://', 'postgresql+psycopg://', 1)
        return value

    @field_validator('admin_emails', mode='before')
    @classmethod
    def _split_admin_emails(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [email.strip().lower() for email in value if email.strip()]
        return [email.strip().lower() for email in value.split(',') if email.strip()]

    @field_validator('sentry_traces_sample_rate')
    @classmethod
    def _validate_sentry_traces_sample_rate(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError('SENTRY_TRACES_SAMPLE_RATE must be between 0 and 1')
        return value

    @property
    def repeat_submissions_enabled(self) -> bool:
        if self.allow_repeat_submissions is not None:
            return self.allow_repeat_submissions
        return self.environment == 'local'


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
