import json
from uuid import UUID

import pytest

from app.core.config import get_settings
from app.core.database import async_session
from app.secrets import crypto
from app.secrets.models import Secret


@pytest.fixture(autouse=True)
async def install_secrets_package(client):
    response = await client.post('/api/packages/omh-package-secrets/install', json={'install_demo_data': False})
    assert response.status_code == 200, response.text


async def test_secret_crud_encrypts_value_and_audit_redacts_plaintext(client):
    response = await client.post('/api/secrets', json={'name': 'onec.erp.password', 'secret_type': 'password', 'value': 'super-secret-password', 'description': '1C ERP password'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['reference'] == {'$secret': 'onec.erp.password'}
    assert 'super-secret-password' not in json.dumps(body)

    async with async_session() as session:
        secret = await session.get(Secret, UUID(body['id']))
        assert secret is not None
        assert secret.encrypted_value != 'super-secret-password'
        assert crypto.decrypt_value(secret.encrypted_value) == 'super-secret-password'

    rotated = await client.post(f"/api/secrets/{body['id']}/rotate", json={'value': 'rotated-password'})
    assert rotated.status_code == 200, rotated.text
    assert 'rotated-password' not in json.dumps(rotated.json())

    audit = await client.get('/api/audit?category=secrets&limit=20')
    assert audit.status_code == 200, audit.text
    serialized = json.dumps(audit.json())
    assert 'super-secret-password' not in serialized
    assert 'rotated-password' not in serialized


async def test_validate_config_and_connector_secret_reference(client):
    secret = await client.post('/api/secrets', json={'name': 'onec.basic.password', 'secret_type': 'basic_auth_password', 'value': 'p@ssw0rd'})
    assert secret.status_code == 200, secret.text
    config = {'base_url': 'https://onec.example.local/odata/standard.odata', 'auth': {'type': 'basic', 'username': 'usr', 'password': {'$secret': 'onec.basic.password'}}, 'timeout_seconds': 10, 'verify_ssl': True}

    validation = await client.post('/api/secrets/validate-config', json={'config': config})
    assert validation.status_code == 200, validation.text
    assert validation.json()['valid'] is True
    assert validation.json()['references'][0]['status'] == 'ok'
    assert validation.json()['raw_secret_warnings'] == []

    connector = await client.post('/api/connectors', json={'name': '1C Secret ERP', 'connector_type': 'onec', 'direction': 'bidirectional', 'config_json': config})
    assert connector.status_code == 200, connector.text
    connector_body = connector.json()
    assert connector_body['config_json']['auth']['password'] == {'$secret': 'onec.basic.password'}

    raw_warning = await client.post('/api/secrets/validate-config', json={'config': {'token': 'plain-token'}})
    assert raw_warning.status_code == 200
    assert raw_warning.json()['raw_secret_warnings']


async def test_integration_bus_static_token_can_use_secret_reference(client):
    token = await client.post('/api/secrets', json={'name': 'bus.static.token', 'secret_type': 'static_token', 'value': 'bus-secret-token'})
    assert token.status_code == 200, token.text
    workflow = await client.post('/api/workflows', json={'name': 'Secret Bus Workflow', 'event_type': 'SecretBus', 'steps_json': [{'name': 'receive'}], 'validation_json': {'required_fields': []}})
    assert workflow.status_code == 200, workflow.text
    endpoint = await client.post('/api/integration-bus/endpoints', json={'name': 'Secret Bus', 'slug': 'secret-bus', 'input_mode': 'json', 'response_mode': 'accepted_event', 'default_event_type': 'SecretBus', 'workflow_id': workflow.json()['id'], 'auth_mode': 'static_token', 'auth_config_json': {'token': {'$secret': 'bus.static.token'}}})
    assert endpoint.status_code == 200, endpoint.text

    denied = await client.post('/api/bus/in/secret-bus', headers={'X-OMH-Token': 'wrong'}, json={'id': '1'})
    assert denied.status_code == 400
    accepted = await client.post('/api/bus/in/secret-bus', headers={'X-OMH-Token': 'bus-secret-token'}, json={'id': '1'})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['accepted'] is True


async def test_export_preserves_secret_reference_and_masks_raw_values(client):
    await client.post('/api/secrets', json={'name': 'rest.auth.header', 'secret_type': 'bearer_token', 'value': 'Bearer abc123'})
    ref_connector = await client.post('/api/connectors', json={'name': 'REST Secret Ref', 'connector_type': 'rest', 'direction': 'target', 'config_json': {'method': 'POST', 'url': 'https://api.example.com/orders', 'headers': {'Authorization': {'$secret': 'rest.auth.header'}}}})
    assert ref_connector.status_code == 200, ref_connector.text
    raw_connector = await client.post('/api/connectors', json={'name': 'REST Raw Secret', 'connector_type': 'rest', 'direction': 'target', 'config_json': {'method': 'POST', 'url': 'https://api.example.com/orders', 'token': 'raw-token'}})
    assert raw_connector.status_code == 200, raw_connector.text

    exported = await client.post('/api/production/export-config', json={'secrets_policy': 'masked'})
    assert exported.status_code == 200, exported.text
    download = await client.get(exported.json()['download_url'])
    payload = download.json()
    ref = next(item for item in payload['objects']['connectors'] if item['name'] == 'REST Secret Ref')
    raw = next(item for item in payload['objects']['connectors'] if item['name'] == 'REST Raw Secret')
    assert ref['config_json']['headers']['Authorization'] == {'$secret': 'rest.auth.header'}
    assert raw['config_json']['token'] == '***MASKED***'
    assert 'Bearer abc123' not in json.dumps(payload)


async def test_production_secret_checks_report_missing_key_and_broken_references(monkeypatch, client):
    get_settings.cache_clear()
    monkeypatch.setenv('OMH_APP_ENV', 'production')
    monkeypatch.delenv('OMH_SECRET_KEY', raising=False)
    connector = await client.post('/api/connectors', json={'name': 'Broken Secret REST', 'connector_type': 'rest', 'direction': 'target', 'config_json': {'method': 'POST', 'url': 'https://api.example.com/orders', 'headers': {'Authorization': {'$secret': 'missing.secret'}}}})
    assert connector.status_code == 400

    # Insert a broken reference through import-like direct DB state so production checks can detect existing drift.
    async with async_session() as session:
        from app.connectors.models import ConnectorInstance
        session.add(ConnectorInstance(name='Broken Existing REST', connector_type='rest', direction='target', enabled=True, status='enabled', config_json={'method': 'POST', 'url': 'https://api.example.com/orders', 'headers': {'Authorization': {'$secret': 'missing.secret'}}}))
        await session.commit()

    checks = await client.post('/api/production/pre-update-check')
    assert checks.status_code == 200, checks.text
    serialized = json.dumps(checks.json())
    assert 'OMH_SECRET_KEY is required in production' in serialized
    assert 'missing.secret' in serialized
    get_settings.cache_clear()


async def test_create_secret_in_production_requires_secret_key(monkeypatch, client):
    get_settings.cache_clear()
    monkeypatch.setenv('OMH_APP_ENV', 'production')
    monkeypatch.delenv('OMH_SECRET_KEY', raising=False)
    response = await client.post('/api/secrets', json={'name': 'prod.missing.key', 'secret_type': 'generic', 'value': 'value'})
    assert response.status_code == 400
    assert response.json()['detail'] == 'OMH_SECRET_KEY is required in production'
    get_settings.cache_clear()
