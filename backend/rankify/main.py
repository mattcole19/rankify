from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rankify.config import Settings, get_settings
from rankify.database import create_engine, dispose_engine
from rankify.logging import configure_logging
from rankify.observability import (
    finish_request_db_stats,
    get_request_db_stats,
    log_request_observability,
    start_request_db_stats,
)
from rankify.routes.admin import router as admin_router
from rankify.routes.categories import router as categories_router
from rankify.routes.health import router as health_router
from rankify.routes.rankings import router as rankings_router
from rankify.telemetry import configure_sentry


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    resolved_settings = settings or get_settings()
    configure_sentry(resolved_settings)

    @asynccontextmanager
    async def _lifespan(_: FastAPI):
        await create_engine(resolved_settings)
        yield
        await dispose_engine()

    app = FastAPI(title='Rankify API', lifespan=_lifespan)
    logger = structlog.get_logger(__name__)
    app.state.settings = resolved_settings
    allow_origins = resolved_settings.cors_allow_origins or ['*']
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=['*'],
        allow_headers=['*'],
        allow_credentials=False,
    )

    @app.middleware('http')
    async def request_observability_middleware(request, call_next):
        request_id = request.headers.get('x-request-id') or str(uuid4())
        request.state.request_id = request_id
        start_time = perf_counter()
        db_stats_token = start_request_db_stats()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration_ms = (perf_counter() - start_time) * 1000
            await log_request_observability(
                request,
                request_id=request_id,
                status_code=status_code,
                duration_ms=duration_ms,
                slow_request_ms=resolved_settings.observability_slow_request_ms,
            )
            logger.exception(
                'http_request_exception',
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            finish_request_db_stats(db_stats_token)
            raise

        duration_ms = (perf_counter() - start_time) * 1000
        await log_request_observability(
            request,
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            slow_request_ms=resolved_settings.observability_slow_request_ms,
        )

        response.headers['X-Request-Id'] = request_id
        db_stats = get_request_db_stats()
        if db_stats is not None:
            response.headers['Server-Timing'] = (
                f'app;dur={duration_ms:.2f}, db;dur={db_stats.query_time_ms:.2f}'
            )
        else:
            response.headers['Server-Timing'] = f'app;dur={duration_ms:.2f}'
        finish_request_db_stats(db_stats_token)
        return response

    app.include_router(health_router)
    app.include_router(admin_router)
    app.include_router(categories_router)
    app.include_router(rankings_router)
    return app


app = create_app()
