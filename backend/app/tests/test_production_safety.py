import json
import os
from pathlib import Path
import subprocess
import sys

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


async def test_production_doctor_and_first_run_checklist(client):
    await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    await client.post("/api/packages/omh-package-printer/install", json={"install_demo_data": False})

    doctor = await client.get("/api/production/doctor")
    assert doctor.status_code == 200, doctor.text
    body = doctor.json()
    assert body["status"] in {"ok", "warning"}
    assert body["counts"]["connectors"] >= 0
    assert any(item["name"] == "Package compatibility" for item in body["checks"])
    assert any(item["name"] == "1C Package" and item["status"] == "ok" for item in body["checks"])

    checklist = await client.get("/api/production/checklist")
    assert checklist.status_code == 200, checklist.text
    items = {item["code"]: item for item in checklist.json()["items"]}
    assert items["release_check"]["status"] == "manual"
    assert "onec_package" in items
    assert "env_production" in items
    assert "worker_heartbeat" in items
    assert "secrets_store" in items


async def test_route_inventory_gate_api(client):
    inventory = await client.get("/api/packages/route-inventory")
    assert inventory.status_code == 200, inventory.text
    paths = {item["path"]: item for item in inventory.json()}
    assert paths["/api/bus/in/{slug}"]["source"] == "core"
    assert paths["/api/printing/*"]["guarded"] is True


def test_factory_production_profile_files_contract():
    repo = Path(__file__).resolve().parents[3]
    compose = (repo / "docker-compose.production.yml").read_text(encoding="utf-8")
    env = (repo / ".env.production.example").read_text(encoding="utf-8")
    frontend_env = (repo / "frontend/.env.production.example").read_text(encoding="utf-8")
    makefile = (repo / "Makefile").read_text(encoding="utf-8")
    nginx = (repo / "deploy/nginx/omh.conf").read_text(encoding="utf-8")

    for service in ["postgres:", "backend:", "worker:", "frontend:", "nginx:"]:
        assert service in compose
    assert "python -m app.workers.queue_worker" in compose
    assert "/api/health/ready" in compose
    assert "./backups:/app/backups" in compose
    assert "profiles: [\"backup\"]" in compose

    for name in ["APP_ENV=production", "OMH_SECRET_KEY=", "DATABASE_URL=", "POSTGRES_PASSWORD=", "VITE_API_BASE_URL=/api", "OMH_PRODUCTION_PROFILE=true"]:
        assert name in env
    assert "VITE_API_BASE_URL=/api" in frontend_env

    for target in ["prod-up", "prod-down", "prod-logs", "prod-migrate", "prod-backup", "prod-restore", "prod-doctor", "prod-release-check", "prod-update-mode-on", "prod-update-mode-off"]:
        assert f"{target}:" in makefile

    assert "location /api/" in nginx
    assert "proxy_pass http://omh_backend" in nginx
    assert "proxy_pass http://omh_frontend" in nginx


async def test_factory_deployment_checks_exposed_in_doctor(monkeypatch, client):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OMH_PRODUCTION_PROFILE", "true")
    monkeypatch.setenv("POSTGRES_PASSWORD", "change-me-long-random-db-password")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://factory.local")
    monkeypatch.delenv("OMH_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    try:
        doctor = await client.get("/api/production/doctor")
        assert doctor.status_code == 200, doctor.text
        checks = {item["name"]: item for item in doctor.json()["checks"]}
        assert checks[".env.production loaded"]["status"] == "ok"
        assert checks["Postgres password changed"]["status"] == "warning"
        assert checks["Nginx/reverse proxy configured"]["status"] == "warning"
        assert checks["Backup volume exists"]["status"] in {"ok", "error"}
        assert "Worker heartbeat OK" in checks
    finally:
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.delenv("OMH_PRODUCTION_PROFILE", raising=False)
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
        get_settings.cache_clear()


def test_queue_worker_entrypoint_imports_and_help_runs():
    repo = Path(__file__).resolve().parents[3]
    from app.workers import queue_worker

    assert callable(queue_worker.main)
    result = subprocess.run(
        [sys.executable, "-m", "app.workers.queue_worker", "--help"],
        cwd=repo / "backend",
        env={**os.environ, "OMH_DATABASE_URL": "sqlite+aiosqlite:///:memory:"},
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "--healthcheck" in result.stdout
