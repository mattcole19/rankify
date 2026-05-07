import pytest
from sqlalchemy import func, select

from rankify.database import get_session_factory
from rankify.db.models import Category, Item, RankingSubmission


@pytest.mark.asyncio()
async def test_list_categories_returns_seeded_category(test_client, seeded_category):
    response = await test_client.get('/categories')

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['slug'] == seeded_category['slug']
    assert payload[0]['item_count'] == 3


@pytest.mark.asyncio()
async def test_submit_ranking_and_fetch_community_ranking(test_client, seeded_category):
    category_response = await test_client.get(f'/categories/{seeded_category["slug"]}')
    assert category_response.status_code == 200
    category_payload = category_response.json()
    ordered_item_ids = [item['id'] for item in category_payload['items']]

    submit_response = await test_client.post(
        '/rankings',
        json={
            'category_id': seeded_category['id'],
            'ordered_item_ids': ordered_item_ids,
            'anon_id': 'anon-test-user',
        },
    )
    assert submit_response.status_code == 201
    submit_payload = submit_response.json()
    assert submit_payload['anon_id'] == 'anon-test-user'

    community_response = await test_client.get(
        f'/categories/{seeded_category["slug"]}/community-ranking'
    )
    assert community_response.status_code == 200
    community_payload = community_response.json()

    assert community_payload['total_submissions'] == 1
    assert len(community_payload['items']) == 3
    assert community_payload['items'][0]['item_id'] == ordered_item_ids[0]
    assert community_payload['items'][0]['average_rank'] == 1.0


@pytest.mark.asyncio()
async def test_submit_ranking_rejects_partial_rankings(test_client, seeded_category):
    category_response = await test_client.get(f'/categories/{seeded_category["slug"]}')
    ordered_item_ids = [item['id'] for item in category_response.json()['items']]

    response = await test_client.post(
        '/rankings',
        json={
            'category_id': seeded_category['id'],
            'ordered_item_ids': ordered_item_ids[:2],
            'anon_id': 'anon-partial',
        },
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'ranking must include every item in the category'


@pytest.mark.asyncio()
async def test_submit_ranking_rejects_existing_submission_for_same_anon_id(
    test_client, seeded_category
):
    category_response = await test_client.get(f'/categories/{seeded_category["slug"]}')
    ordered_item_ids = [item['id'] for item in category_response.json()['items']]

    first_response = await test_client.post(
        '/rankings',
        json={
            'category_id': seeded_category['id'],
            'ordered_item_ids': ordered_item_ids,
            'anon_id': 'anon-stable-user',
        },
    )
    assert first_response.status_code == 201

    second_response = await test_client.post(
        '/rankings',
        json={
            'category_id': seeded_category['id'],
            'ordered_item_ids': list(reversed(ordered_item_ids)),
            'anon_id': 'anon-stable-user',
        },
    )
    assert second_response.status_code == 409
    assert second_response.json()['detail'] == 'ranking already submitted for this category'

    async with get_session_factory()() as session:
        submission_count = await session.scalar(
            select(func.count(RankingSubmission.id)).where(
                RankingSubmission.category_id == seeded_category['id'],
                RankingSubmission.anon_id == 'anon-stable-user',
            )
        )
    assert submission_count == 1


@pytest.mark.asyncio()
async def test_submit_ranking_requires_anon_id(test_client, seeded_category):
    category_response = await test_client.get(f'/categories/{seeded_category["slug"]}')
    ordered_item_ids = [item['id'] for item in category_response.json()['items']]

    response = await test_client.post(
        '/rankings',
        json={
            'category_id': seeded_category['id'],
            'ordered_item_ids': ordered_item_ids,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio()
async def test_list_categories_hides_categories_with_less_than_two_items(test_client, seeded_category):
    async with get_session_factory()() as session:
        category = Category(slug='single-item', name='Single Item', description='not rankable yet')
        session.add(category)
        await session.flush()
        session.add(Item(category_id=category.id, name='Only Option', display_order=0))
        await session.commit()

    response = await test_client.get('/categories')

    assert response.status_code == 200
    payload = response.json()
    slugs = {entry['slug'] for entry in payload}
    assert seeded_category['slug'] in slugs
    assert 'single-item' not in slugs


@pytest.mark.asyncio()
async def test_category_endpoints_resolve_latest_published_version_by_slug(test_client, seeded_category):
    async with get_session_factory()() as session:
        version_two = Category(
            slug=seeded_category['slug'],
            name='Test Candy',
            description='Second version',
            version_number=2,
            status='published',
        )
        session.add(version_two)
        await session.flush()
        session.add_all(
            [
                Item(category_id=version_two.id, name='Sour Worms', display_order=0),
                Item(category_id=version_two.id, name='Peanut Butter Cups', display_order=1),
                Item(category_id=version_two.id, name='Gummy Bears', display_order=2),
                Item(category_id=version_two.id, name='Blue Raspberry', display_order=3),
            ]
        )
        session.add(RankingSubmission(category_id=version_two.id, anon_id='anon-v2'))
        await session.commit()

    detail_response = await test_client.get(f'/categories/{seeded_category["slug"]}')
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload['description'] == 'Second version'
    assert len(detail_payload['items']) == 4

    ranking_response = await test_client.get(
        f'/categories/{seeded_category["slug"]}/community-ranking'
    )
    assert ranking_response.status_code == 200
    ranking_payload = ranking_response.json()
    assert ranking_payload['total_submissions'] == 1

    version_detail_response = await test_client.get(f'/categories/{seeded_category["slug"]}?version=1')
    assert version_detail_response.status_code == 200
    version_detail_payload = version_detail_response.json()
    assert version_detail_payload['description'] == 'A seeded test category.'
    assert len(version_detail_payload['items']) == 3

    versions_response = await test_client.get(f'/categories/{seeded_category["slug"]}/versions')
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()
    assert [entry['version_number'] for entry in versions_payload] == [2, 1]
