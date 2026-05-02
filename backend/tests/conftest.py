import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from rankify.config import Settings, reset_settings_cache
from rankify.database import get_engine, get_session_factory
from rankify.db.base import Base
from rankify.db.models import Category, Item
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
    os.environ['ADMIN_SECRET'] = 'test-admin-secret'
    reset_settings_cache()
    return Settings()


@pytest.fixture()
async def test_client(settings: Settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        engine = get_engine()
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://testserver') as client:
            yield client


@pytest.fixture()
async def seeded_category() -> dict[str, int | str]:
    async with get_session_factory()() as session:
        existing = await session.scalar(select(Category).where(Category.slug == 'test-candy'))
        if existing is None:
            category = Category(
                slug='test-candy', name='Test Candy', description='A seeded test category.'
            )
            session.add(category)
            await session.flush()

            session.add_all(
                [
                    Item(category_id=category.id, name='Sour Worms', display_order=0),
                    Item(category_id=category.id, name='Peanut Butter Cups', display_order=1),
                    Item(category_id=category.id, name='Gummy Bears', display_order=2),
                ]
            )
            await session.commit()
            return {'id': category.id, 'slug': category.slug}

        return {'id': existing.id, 'slug': existing.slug}
