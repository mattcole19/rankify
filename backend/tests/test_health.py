import pytest


@pytest.mark.asyncio()
async def test_health_endpoint_reports_ok(test_client):
    response = await test_client.get('/health')

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert payload['database'] == 'up'
    assert 'version' in payload
