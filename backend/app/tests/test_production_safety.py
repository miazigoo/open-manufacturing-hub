import json

from app.core.config import get_settings


async def test_production_snapshot_status_and_config_export_masks_secrets(client):
    connector = await client.post(
        "/api/connectors",
        json={"name": "Secret REST", "connector_type": "rest", "direction": "target", "config_json": {"url": "https://api.example.com", "token": "real-token", "nested": {"password": "secret"}}},
    )
    assert connector.status_code == 200, connector.text
    workflow = await client.post("/api/workflows", json={"name": "Production Export Workflow", "event_type": "ProductionExport", "steps_json": [{"name": "receive"}], "validation_json": {}})
    assert workflow.status_code == 200, workflow.text

    status = await client.get("/api/production/status")
    assert status.status_code == 200, status.text
    assert status.json()["version"] == "0.1.0"

    snapshot = await client.get("/api/production/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert body["counts"]["connectors"] >= 2
    assert body["counts"]["workflows"] >= 1

    exported = await client.post("/api/production/export-config", json={"secrets_policy": "masked"})
    assert exported.status_code == 200, exported.text
    export_body = exported.json()
    assert export_body["download_url"]

    download = await client.get(export_body["download_url"])
    assert download.status_code == 200, download.text
    payload = download.json()
    assert payload["omh_export_version"] == 1
    assert "integration_events" not in payload["objects"]
    rest = next(item for item in payload["objects"]["connectors"] if item["name"] == "Secret REST")
    assert rest["config_json"]["token"] == "***MASKED***"
    assert rest["config_json"]["nested"]["password"] == "***MASKED***"

    exports = await client.get("/api/production/exports")
    assert exports.status_code == 200
    assert any(item["id"] == export_body["export_id"] for item in exports.json())


async def test_config_import_preview_create_only_and_upsert(client):
    payload = {
        "omh_export_version": 1,
        "created_at": "2026-07-04T00:00:00+00:00",
        "app_version": "0.1.0",
        "environment": "test",
        "packages": [],
        "secrets_policy": "masked",
        "warnings": [],
        "objects": {
            "connectors": [
                {"name": "Imported REST", "connector_type": "rest", "direction": "target", "enabled": True, "config_json": {"base_url": "https://example.test", "token": "***MASKED***"}, "status": "enabled"}
            ],
            "workflows": [
                {"name": "Imported Workflow", "event_type": "ImportedEvent", "enabled": True, "version": 1, "steps_json": [{"name": "receive"}], "validation_json": {}}
            ],
        },
    }
    preview = await client.post("/api/production/import-config/preview", json={"export": payload, "mode": "create_only"})
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] is True
    assert preview.json()["will_create"]["connectors"] == 1
    assert preview.json()["warnings"]

    applied = await client.post("/api/production/import-config/apply", json={"export": payload, "mode": "create_only"})
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied"] is True

    conflict = await client.post("/api/production/import-config/preview", json={"export": payload, "mode": "create_only"})
    assert conflict.status_code == 200
    assert conflict.json()["conflicts"]

    upsert_preview = await client.post("/api/production/import-config/preview", json={"export": payload, "mode": "upsert"})
    assert upsert_preview.status_code == 200
    assert upsert_preview.json()["will_update"]["connectors"] == 1


async def test_pre_update_check_and_update_mode_pause_queue_worker(client):
    workflow = await client.post("/api/workflows", json={"name": "Pause Worker Workflow", "event_type": "PauseWorker", "steps_json": [{"name": "receive"}], "validation_json": {}})
    assert workflow.status_code == 200, workflow.text
    endpoint = await client.post("/api/integration-bus/endpoints", json={"name": "Pause Worker Endpoint", "slug": "pause-worker", "input_mode": "json", "response_mode": "accepted_event", "default_event_type": "PauseWorker", "workflow_id": workflow.json()["id"]})
    assert endpoint.status_code == 200, endpoint.text
    accepted = await client.post("/api/bus/in/pause-worker", json={"id": "1"})
    assert accepted.status_code == 200, accepted.text

    check = await client.post("/api/production/pre-update-check")
    assert check.status_code == 200, check.text
    assert check.json()["safe_to_update"] is False
    assert "Create backup" in check.json()["required_actions"]

    enabled = await client.post("/api/production/update-mode/enable", json={"message": "maintenance", "enabled_by": "test"})
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    processed = await client.post("/api/queue/process-once?worker=test-worker")
    assert processed.status_code == 200
    assert processed.json()["processed"] == 0

    disabled = await client.post("/api/production/update-mode/disable")
    assert disabled.status_code == 200
    processed = await client.post("/api/queue/process-once?worker=test-worker")
    assert processed.status_code == 200
    assert processed.json()["processed"] == 1


async def test_demo_seed_blocked_in_production(monkeypatch, client):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ALLOW_DEMO_SEED_IN_PRODUCTION", raising=False)
    get_settings.cache_clear()
    try:
        response = await client.post("/api/demo/seed")
        assert response.status_code == 400
        assert response.json()["detail"] == "DEMO_SEED_DISABLED_IN_PRODUCTION"
    finally:
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()
