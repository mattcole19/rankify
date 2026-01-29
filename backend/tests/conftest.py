import os

import pytest
from httpx import ASGITransport, AsyncClient

from rankify.config import Settings, reset_settings_cache
from rankify.main import create_app


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture()
def settings(tmp_path) -> Settings:
    test_db = tmp_path / 'test.db'
    os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{test_db}'
    os.environ['ENVIRONMENT'] = 'test'
    reset_settings_cache()
    return Settings()


@pytest.fixture()
async def test_client(settings: Settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://testserver') as client:
            yield client
