from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from rankify.config import Settings, get_settings
from rankify.database import create_engine, dispose_engine
from rankify.logging import configure_logging
from rankify.routes.health import router as health_router


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
    app.include_router(health_router)
    return app


app = create_app()
