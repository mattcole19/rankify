from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rankify.config import Settings, get_settings
from rankify.database import create_engine, dispose_engine
from rankify.logging import configure_logging
from rankify.routes.categories import router as categories_router
from rankify.routes.health import router as health_router
from rankify.routes.rankings import router as rankings_router


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def _lifespan(_: FastAPI):
        await create_engine(resolved_settings)
        yield
        await dispose_engine()

    app = FastAPI(title='Rankify API', lifespan=_lifespan)
    app.state.settings = resolved_settings
    allow_origins = resolved_settings.cors_allow_origins or ['*']
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=['*'],
        allow_headers=['*'],
        allow_credentials=False,
    )
    app.include_router(health_router)
    app.include_router(categories_router)
    app.include_router(rankings_router)
    return app


app = create_app()
