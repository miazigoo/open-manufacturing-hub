import pytest

pytestmark = pytest.mark.anyio


async def _setup_environment(client, variables: list[dict]):
    env = await client.post(
        "/api/environments",
        json={"name": "Fed Env", "code": "fed-env", "environment_type": "development", "is_current": True, "variables": []},
    )
    assert env.status_code == 200, env.text
    env_id = env.json()["id"]
    for variable in variables:
        response = await client.post(f"/api/environments/{env_id}/variables", json=variable)
        assert response.status_code == 200, response.text


async def test_federation_bundle_requires_token(client):
    forbidden = await client.get("/api/federation/config-bundle")
    assert forbidden.status_code == 403
    assert "FEDERATION_TOKEN" in forbidden.text

    await _setup_environment(client, [{"key": "FEDERATION_TOKEN", "value_json": "fed-secret"}])
    wrong = await client.get("/api/federation/config-bundle", headers={"X-OMH-Token": "wrong"})
    assert wrong.status_code == 403

    bundle = await client.get("/api/federation/config-bundle", headers={"X-OMH-Token": "fed-secret"})
    assert bundle.status_code == 200, bundle.text
    body = bundle.json()
    assert body["omh_export_version"] == 1
    assert body["version"]
    assert "objects" in body


async def test_federation_sync_applies_bundle_from_center(client, monkeypatch):
    from app.federation import service as federation_service

    await _setup_environment(client, [
        {"key": "FEDERATION_CENTER_URL", "value_json": "http://center.local"},
        {"key": "FEDERATION_TOKEN", "value_json": "fed-secret"},
        {"key": "FEDERATION_ENABLED", "value_json": "true"},
    ])

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "omh_export_version": 1,
                "version": "2026-08-06T10:00:00",
                "objects": {
                    "connectors": [
                        {"name": "Fed Connector", "connector_type": "rest", "direction": "target", "enabled": True, "status": "enabled", "config_json": {"url": "http://fed.local/api", "method": "POST"}},
                    ]
                },
            }

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, *, headers):
            assert url == "http://center.local/api/federation/config-bundle"
            assert headers["X-OMH-Token"] == "fed-secret"
            return FakeResponse()

    monkeypatch.setattr(federation_service.httpx, "AsyncClient", FakeAsyncClient)

    result = await client.post("/api/federation/sync-now")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "success"
    assert "Применена версия" in body["message"]

    connectors = await client.get("/api/connectors")
    assert any(item["name"] == "Fed Connector" for item in connectors.json())

    again = await client.post("/api/federation/sync-now")
    assert again.json()["status"] == "skipped"

    status = await client.get("/api/federation/status")
    assert status.json()["enabled"] is True
    assert status.json()["last_applied_version"] == "2026-08-06T10:00:00"

    runs = await client.get("/api/federation/runs")
    assert len(runs.json()) == 2
    assert runs.json()[0]["status"] == "skipped"


async def test_federation_sync_fails_clearly_without_center_url(client):
    result = await client.post("/api/federation/sync-now")
    assert result.status_code == 400
    assert "FEDERATION_CENTER_URL" in result.text


async def test_federation_sync_records_center_http_error(client, monkeypatch):
    from app.federation import service as federation_service

    await _setup_environment(client, [
        {"key": "FEDERATION_CENTER_URL", "value_json": "http://center.local"},
        {"key": "FEDERATION_TOKEN", "value_json": "fed-secret"},
    ])

    class FakeResponse:
        status_code = 403
        text = "forbidden"

        @staticmethod
        def json():
            return {}

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, *, headers):
            return FakeResponse()

    monkeypatch.setattr(federation_service.httpx, "AsyncClient", FakeAsyncClient)

    result = await client.post("/api/federation/sync-now")
    body = result.json()
    assert body["status"] == "failed"
    assert "токен" in body["message"]

    runs = await client.get("/api/federation/runs")
    assert runs.json()[0]["status"] == "failed"
