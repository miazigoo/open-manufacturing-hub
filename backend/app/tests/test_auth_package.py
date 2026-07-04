from httpx import ASGITransport, AsyncClient

from app.main import app


async def install_auth(client: AsyncClient) -> None:
    response = await client.post('/api/packages/omh-package-auth/install', json={'install_demo_data': False})
    assert response.status_code == 200, response.text


async def bootstrap_admin(client: AsyncClient, username: str = 'admin', password: str = 'admin') -> list[str]:
    response = await client.post('/api/auth/bootstrap', json={'username': username, 'display_name': 'Admin', 'password': password})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['username'] == username
    assert len(body['recovery_keys']) == 5
    return body['recovery_keys']


async def login(client: AsyncClient, username: str = 'admin', password: str = 'admin') -> None:
    response = await client.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200, response.text


async def test_auth_package_disabled_keeps_core_api_public(client):
    state = await client.get('/api/auth/state')
    assert state.status_code == 200
    assert state.json()['requires_login'] is False

    connectors = await client.get('/api/connectors')
    assert connectors.status_code == 200, connectors.text


async def test_auth_install_requires_bootstrap_then_login_session_and_logout(client):
    await install_auth(client)

    state = await client.get('/api/auth/state')
    assert state.status_code == 200
    assert state.json()['bootstrap_required'] is True

    protected = await client.get('/api/connectors')
    assert protected.status_code == 401

    await bootstrap_admin(client)
    second_bootstrap = await client.post('/api/auth/bootstrap', json={'username': 'second', 'password': 'second'})
    assert second_bootstrap.status_code == 400

    blocked = await client.get('/api/connectors')
    assert blocked.status_code == 401

    await login(client)
    me = await client.get('/api/auth/me')
    assert me.status_code == 200
    assert me.json()['username'] == 'admin'

    connectors = await client.get('/api/connectors')
    assert connectors.status_code == 200, connectors.text

    logout = await client.post('/api/auth/logout')
    assert logout.status_code == 204
    logged_out = await client.get('/api/auth/me')
    assert logged_out.status_code == 401


async def test_auth_user_creation_recovery_key_and_disabled_login(client):
    await install_auth(client)
    await bootstrap_admin(client)
    await login(client)

    created = await client.post('/api/auth/users', json={'username': 'operator', 'display_name': 'Operator', 'password': 'old'})
    assert created.status_code == 200, created.text
    user = created.json()
    assert len(user['recovery_keys']) == 5

    recover = await client.post('/api/auth/recover-password', json={'username': 'operator', 'recovery_key': user['recovery_keys'][0], 'new_password': 'new'})
    assert recover.status_code == 204, recover.text
    reused = await client.post('/api/auth/recover-password', json={'username': 'operator', 'recovery_key': user['recovery_keys'][0], 'new_password': 'another'})
    assert reused.status_code == 400

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as operator_client:
        await login(operator_client, 'operator', 'new')
        operator_me = await operator_client.get('/api/auth/me')
        assert operator_me.status_code == 200

    disabled = await client.post(f"/api/auth/users/{user['id']}/disable")
    assert disabled.status_code == 200
    assert disabled.json()['enabled'] is False

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as disabled_client:
        denied = await disabled_client.post('/api/auth/login', json={'username': 'operator', 'password': 'new'})
        assert denied.status_code == 400


async def test_auth_change_password_revokes_sessions(client):
    await install_auth(client)
    await bootstrap_admin(client, password='old')
    await login(client, password='old')

    changed = await client.post('/api/auth/change-password', json={'current_password': 'old', 'new_password': 'new'})
    assert changed.status_code == 204, changed.text
    old_session = await client.get('/api/auth/me')
    assert old_session.status_code == 401

    await login(client, password='new')
    me = await client.get('/api/auth/me')
    assert me.status_code == 200


async def test_auth_does_not_wrap_integration_bus_inbound(client):
    workflow = await client.post(
        '/api/workflows',
        json={
            'name': 'Auth Public Bus Workflow',
            'event_type': 'AuthBusEvent',
            'steps_json': [{'name': 'receive'}],
            'validation_json': {'required_fields': []},
        },
    )
    assert workflow.status_code == 200, workflow.text
    endpoint = await client.post(
        '/api/integration-bus/endpoints',
        json={
            'name': 'Auth public inbound',
            'slug': 'auth-public-inbound',
            'input_mode': 'json',
            'response_mode': 'accepted_event',
            'default_event_type': 'AuthBusEvent',
            'workflow_id': workflow.json()['id'],
            'auth_mode': 'none',
        },
    )
    assert endpoint.status_code == 200, endpoint.text

    await install_auth(client)
    await bootstrap_admin(client)

    protected = await client.get('/api/connectors')
    assert protected.status_code == 401

    inbound = await client.post('/api/bus/in/auth-public-inbound', json={'id': '1'})
    assert inbound.status_code == 200, inbound.text
    assert inbound.json()['event_id']
