import pytest


@pytest.mark.asyncio()
async def test_create_category_requires_admin_secret(test_client):
    response = await test_client.post(
        '/admin/categories',
        json={
            'name': 'Movies',
            'slug': 'movies',
            'description': 'Rank your favorite movies.',
            'items': ['Inception', 'Interstellar'],
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Missing admin authentication (bearer token or admin secret)'


@pytest.mark.asyncio()
async def test_create_category_creates_published_v1(test_client):
    response = await test_client.post(
        '/admin/categories',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'name': 'Veggies',
            'slug': 'veggies',
            'description': 'Rank vegetables',
            'items': ['Carrot', 'Broccoli'],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['slug'] == 'veggies'
    assert payload['version_number'] == 1
    assert payload['status'] == 'published'

    public_response = await test_client.get('/categories')
    slugs = {entry['slug'] for entry in public_response.json()}
    assert 'veggies' in slugs


@pytest.mark.asyncio()
async def test_create_category_rejects_duplicate_slug(test_client, seeded_category):
    response = await test_client.post(
        '/admin/categories',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'name': 'Candy Copy',
            'slug': seeded_category['slug'],
            'description': 'Duplicate slug attempt.',
            'items': ['A', 'B'],
        },
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Category slug already exists'


@pytest.mark.asyncio()
async def test_list_admin_categories_returns_versions(test_client, seeded_category):
    create_response = await test_client.post(
        f'/admin/categories/{seeded_category["slug"]}/versions',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'items': ['Sour Worms', 'Peanut Butter Cups', 'Gummy Bears', 'Blue Raspberry'],
        },
    )
    assert create_response.status_code == 201

    response = await test_client.get(
        '/admin/categories',
        headers={'x-admin-secret': 'test-admin-secret'},
    )

    assert response.status_code == 200
    payload = response.json()
    seeded_entries = [entry for entry in payload if entry['slug'] == seeded_category['slug']]
    assert [entry['version_number'] for entry in seeded_entries] == [2, 1]


@pytest.mark.asyncio()
async def test_create_category_version_publishes_with_full_item_set(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["slug"]}/versions',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'items': ['Sour Worms', 'Peanut Butter Cups', 'Blue Raspberry'],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['slug'] == seeded_category['slug']
    assert payload['version_number'] == 2
    assert payload['status'] == 'published'

    latest_detail = await test_client.get(f'/categories/{seeded_category["slug"]}')
    assert latest_detail.status_code == 200
    latest_items = [item['name'] for item in latest_detail.json()['items']]
    assert latest_items == ['Sour Worms', 'Peanut Butter Cups', 'Blue Raspberry']


@pytest.mark.asyncio()
async def test_create_category_version_requires_two_items(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["slug"]}/versions',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'items': ['Only One'],
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio()
async def test_add_items_rejects_published_version(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["id"]}/items',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={'items': ['Skittles']},
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Published versions are immutable; create a new version instead'
