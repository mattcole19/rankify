import asyncio

from sqlalchemy import select

from rankify.config import get_settings
from rankify.database import create_engine, dispose_engine, get_session_factory
from rankify.db.models import Category, Item

SEED_DATA = [
    {
        'slug': 'programming-languages',
        'name': 'Programming Languages',
        'description': 'Rank the languages you enjoy using the most.',
        'items': ['Python', 'TypeScript', 'Go', 'Rust', 'C#'],
    },
    {
        'slug': 'ice-cream-flavors',
        'name': 'Ice Cream Flavors',
        'description': 'Classic cone debate, settled by rankings.',
        'items': ['Vanilla', 'Chocolate', 'Strawberry', 'Mint Chip', 'Cookie Dough'],
    },
]


async def run() -> None:
    settings = get_settings()
    await create_engine(settings)

    async with get_session_factory()() as session:
        existing = await session.scalar(select(Category.id).limit(1))
        if existing is not None:
            print('Seed skipped: categories already exist.')
            await dispose_engine()
            return

        for category_payload in SEED_DATA:
            category = Category(
                slug=category_payload['slug'],
                name=category_payload['name'],
                description=category_payload['description'],
            )
            session.add(category)
            await session.flush()

            for index, item_name in enumerate(category_payload['items']):
                session.add(Item(category_id=category.id, name=item_name, display_order=index))

        await session.commit()

    await dispose_engine()
    print('Seed complete.')


if __name__ == '__main__':
    asyncio.run(run())
