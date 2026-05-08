from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rankify.config import Settings
from rankify.observability import instrument_sqlalchemy_engine

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


async def create_engine(settings: Settings) -> None:
    global engine, session_factory
    engine = create_async_engine(settings.database_url, echo=False)
    instrument_sqlalchemy_engine(
        engine,
        slow_query_ms=settings.observability_slow_db_query_ms,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def dispose_engine() -> None:
    if engine is not None:
        await engine.dispose()


def get_engine() -> AsyncEngine:
    if engine is None:
        raise RuntimeError('Engine is not initialized yet')
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if session_factory is None:
        raise RuntimeError('Session factory is not initialized yet')
    return session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def ping_database() -> bool:
    current_engine = get_engine()
    try:
        async with current_engine.connect() as connection:
            await connection.execute(text('SELECT 1'))
        return True
    except Exception:
        return False
