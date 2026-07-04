async def test_local_dev_origin_regex_is_allowed(client):
    response = await client.get('/api/health', headers={'Origin': 'http://127.0.0.1:59999'})

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://127.0.0.1:59999'


async def test_unknown_origin_is_not_allowed(client):
    response = await client.get('/api/health', headers={'Origin': 'https://evil.example'})

    assert response.status_code == 200
    assert 'access-control-allow-origin' not in response.headers
