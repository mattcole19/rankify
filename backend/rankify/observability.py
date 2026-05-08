from __future__ import annotations

import time
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

logger = structlog.get_logger(__name__)


@dataclass
class RequestDBStats:
    query_count: int = 0
    query_time_ms: float = 0.0
    max_query_time_ms: float = 0.0
    slow_queries: list[dict[str, Any]] = field(default_factory=list)


_request_db_stats: ContextVar[RequestDBStats | None] = ContextVar(
    'request_db_stats', default=None
)


def _normalize_sql(statement: str) -> str:
    compact = ' '.join(statement.split())
    return compact if len(compact) <= 220 else f'{compact[:217]}...'


def start_request_db_stats() -> Token[RequestDBStats | None]:
    return _request_db_stats.set(RequestDBStats())


def finish_request_db_stats(token: Token[RequestDBStats | None]) -> None:
    _request_db_stats.reset(token)


def get_request_db_stats() -> RequestDBStats | None:
    return _request_db_stats.get()


def instrument_sqlalchemy_engine(engine: AsyncEngine, *, slow_query_ms: int) -> None:
    sync_engine = engine.sync_engine
    if getattr(sync_engine, '_rankify_observability_instrumented', False):
        return

    @event.listens_for(sync_engine, 'before_cursor_execute')
    def _before_cursor_execute(
        _conn: Any,
        _cursor: Any,
        _statement: str,
        _parameters: Any,
        context: Any,
        _executemany: bool,
    ) -> None:
        context._query_start_time = time.perf_counter()

    @event.listens_for(sync_engine, 'after_cursor_execute')
    def _after_cursor_execute(
        _conn: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        context: Any,
        _executemany: bool,
    ) -> None:
        start_time = getattr(context, '_query_start_time', None)
        if start_time is None:
            return

        duration_ms = (time.perf_counter() - start_time) * 1000
        stats = get_request_db_stats()
        if stats is None:
            return

        stats.query_count += 1
        stats.query_time_ms += duration_ms
        stats.max_query_time_ms = max(stats.max_query_time_ms, duration_ms)
        if duration_ms >= slow_query_ms and len(stats.slow_queries) < 5:
            stats.slow_queries.append(
                {
                    'duration_ms': round(duration_ms, 2),
                    'sql': _normalize_sql(statement),
                }
            )

    sync_engine._rankify_observability_instrumented = True


async def log_request_observability(
    request: Request,
    *,
    request_id: str,
    status_code: int,
    duration_ms: float,
    slow_request_ms: int,
) -> None:
    stats = get_request_db_stats() or RequestDBStats()

    payload: dict[str, Any] = {
        'request_id': request_id,
        'method': request.method,
        'path': request.url.path,
        'status_code': status_code,
        'duration_ms': round(duration_ms, 2),
        'db_query_count': stats.query_count,
        'db_query_time_ms': round(stats.query_time_ms, 2),
        'db_max_query_time_ms': round(stats.max_query_time_ms, 2),
        'slow_query_count': len(stats.slow_queries),
    }
    if stats.slow_queries:
        payload['slow_queries'] = stats.slow_queries

    if duration_ms >= slow_request_ms:
        logger.warning('http_request_slow', **payload)
    else:
        logger.info('http_request', **payload)
