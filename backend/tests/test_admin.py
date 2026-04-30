import pytest


@pytest.mark.asyncio()
async def test_create_category_requires_admin_secret(test_client):
    response = await test_client.post(
        '/admin/categories',
        json={'name': 'Movies', 'slug': 'movies', 'description': 'Rank your favorite movies.'},
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Missing admin secret'


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
