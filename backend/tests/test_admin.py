import pytest


@pytest.mark.asyncio()
async def test_create_category_requires_admin_secret(test_client):
    response = await test_client.post(
        '/admin/categories',
        json={'name': 'Movies', 'slug': 'movies', 'description': 'Rank your favorite movies.'},
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Missing admin authentication (bearer token or admin secret)'


@pytest.mark.asyncio()
async def test_create_category_rejects_invalid_admin_secret(test_client):
    response = await test_client.post(
        '/admin/categories',
        headers={'x-admin-secret': 'not-right'},
        json={'name': 'Movies', 'slug': 'movies', 'description': 'Rank your favorite movies.'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Invalid admin secret'


@pytest.mark.asyncio()
async def test_create_category_creates_record(test_client):
    response = await test_client.post(
        '/admin/categories',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'name': 'Movies',
            'slug': 'movies',
            'description': 'Rank your favorite movies.',
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['id'] > 0
    assert payload['name'] == 'Movies'
    assert payload['slug'] == 'movies'
    assert payload['version_number'] == 1
    assert payload['status'] == 'published'


@pytest.mark.asyncio()
async def test_create_category_rejects_duplicate_slug(test_client, seeded_category):
    response = await test_client.post(
        '/admin/categories',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={
            'name': 'Candy Copy',
            'slug': seeded_category['slug'],
            'description': 'Duplicate slug attempt.',
        },
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Category slug already exists'


@pytest.mark.asyncio()
async def test_add_items_to_category_appends_display_order(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["id"]}/items',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={'items': ['Skittles', 'Twix']},
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]['name'] == 'Skittles'
    assert payload[0]['display_order'] == 3
    assert payload[1]['name'] == 'Twix'
    assert payload[1]['display_order'] == 4


@pytest.mark.asyncio()
async def test_add_items_requires_admin_secret(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["id"]}/items',
        json={'items': ['Skittles']},
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Missing admin authentication (bearer token or admin secret)'


@pytest.mark.asyncio()
async def test_add_items_requires_existing_category(test_client):
    response = await test_client.post(
        '/admin/categories/99999/items',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={'items': ['Skittles']},
    )

    assert response.status_code == 404
    assert response.json()['detail'] == 'Category not found'


@pytest.mark.asyncio()
async def test_add_items_rejects_existing_item_names_case_insensitive(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["id"]}/items',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={'items': ['sour worms']},
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Items already exist in category: sour worms'


@pytest.mark.asyncio()
async def test_create_category_version_adds_new_items_and_increments_version(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["slug"]}/versions',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={'new_items': ['Blue Raspberry']},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['slug'] == seeded_category['slug']
    assert payload['version_number'] == 2
    assert payload['status'] == 'published'


@pytest.mark.asyncio()
async def test_create_category_version_rejects_duplicate_new_items(test_client, seeded_category):
    response = await test_client.post(
        f'/admin/categories/{seeded_category["slug"]}/versions',
        headers={'x-admin-secret': 'test-admin-secret'},
        json={'new_items': ['Sour Worms']},
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Items already exist in category: sour worms'
