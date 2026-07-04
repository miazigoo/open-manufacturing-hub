from datetime import datetime, timedelta, timezone

from app.audit.diff import json_diff, redact_secrets


def test_audit_diff_redacts_secrets_and_tracks_changes():
    before = {"name": "old", "password": "plain", "nested": {"token": "abc", "qty": 1}}
    after = {"name": "new", "api_key": "secret", "nested": {"token": "def", "qty": 2}, "added": True}
    diff = json_diff(before, after)
    assert {item["path"] for item in diff["changed"]} >= {"name", "nested.qty"}
    assert any(item["path"] == "added" for item in diff["added"])
    assert redact_secrets(after)["api_key"] == "***REDACTED***"
    assert "plain" not in str(diff)
    assert "secret" not in str(diff)


async def test_connector_audit_change_filter_and_object_history(client):
    created = await client.post(
        "/api/connectors",
        headers={"X-Request-ID": "audit-connector-create"},
        json={"name": "Audit REST", "connector_type": "rest", "direction": "target", "config_json": {"url": "https://example.com", "token": "secret-token"}},
    )
    assert created.status_code == 200
    connector = created.json()

    patched = await client.patch(
        f"/api/connectors/{connector['id']}",
        headers={"X-Request-ID": "audit-connector-patch"},
        json={"enabled": False, "config_json": {"url": "https://example.org", "token": "changed-token"}},
    )
    assert patched.status_code == 200

    response = await client.get("/api/audit", params={"category": "connectors", "action": "connector.updated", "object_type": "connector"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    event = body["items"][0]
    assert event["request_id"] == "audit-connector-patch"
    assert event["object_id"] == connector["id"]
    assert event["diff_json"]["changed"]
    assert "changed-token" not in str(event)
    assert "***REDACTED***" in str(event)

    history = await client.get(f"/api/audit/object/connector/{connector['id']}")
    assert history.status_code == 200
    actions = {item["action"] for item in history.json()["items"]}
    assert {"connector.created", "connector.updated"}.issubset(actions)


async def test_auth_audit_login_user_and_password_actions(client):
    installed = await client.post("/api/packages/omh-package-auth/install", json={})
    assert installed.status_code == 200

    bootstrap = await client.post("/api/auth/bootstrap", json={"username": "admin", "display_name": "Admin", "password": "admin"})
    assert bootstrap.status_code == 200
    keys = bootstrap.json()["recovery_keys"]
    assert len(keys) == 5

    login = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert login.status_code == 200
    user_id = login.json()["id"]

    changed = await client.post("/api/auth/change-password", json={"current_password": "admin", "new_password": "new"})
    assert changed.status_code == 204
    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204
    recovered = await client.post("/api/auth/recover-password", json={"username": "admin", "recovery_key": keys[0], "new_password": "again"})
    assert recovered.status_code == 204
    relogin = await client.post("/api/auth/login", json={"username": "admin", "password": "again"})
    assert relogin.status_code == 200

    audit = await client.get("/api/audit", params={"category": "auth", "limit": 20})
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"auth.login", "auth.logout", "auth.password_changed", "auth.recovery_key_used"}.issubset(actions)

    user_history = await client.get(f"/api/audit/user/{user_id}")
    assert user_history.status_code == 200
    assert user_history.json()["total"] >= 1


async def test_queue_dlq_and_production_audit_actions(client):
    queue = await client.post("/api/queue", json={"business_object": "Order", "business_key": "O-1", "operation": "sync", "payload_json": {"order": "O-1"}})
    assert queue.status_code == 200
    queue_id = queue.json()["id"]

    retry = await client.post(f"/api/queue/{queue_id}/retry-now")
    assert retry.status_code == 200
    dlq = await client.post(f"/api/queue/{queue_id}/move-to-dlq", params={"reason": "manual test"})
    assert dlq.status_code == 200
    dlq_id = dlq.json()["id"]
    restored = await client.post(f"/api/dlq/{dlq_id}/retry")
    assert restored.status_code == 200

    pre = await client.post("/api/production/pre-update-check")
    assert pre.status_code == 200
    enabled = await client.post("/api/production/update-mode/enable", json={"message": "test", "enabled_by": "pytest"})
    assert enabled.status_code == 200
    disabled = await client.post("/api/production/update-mode/disable")
    assert disabled.status_code == 200

    queue_audit = await client.get("/api/audit", params={"category": "queue", "object_id": queue_id})
    assert queue_audit.status_code == 200
    queue_actions = {item["action"] for item in queue_audit.json()["items"]}
    assert {"queue.retry_now", "queue.moved_to_dlq"}.issubset(queue_actions)

    dlq_audit = await client.get("/api/audit", params={"category": "dlq", "object_id": dlq_id})
    assert dlq_audit.status_code == 200
    assert any(item["action"] == "dlq.restored" for item in dlq_audit.json()["items"])

    production_audit = await client.get("/api/audit", params={"category": "production", "limit": 20})
    assert production_audit.status_code == 200
    production_actions = {item["action"] for item in production_audit.json()["items"]}
    assert {"production.pre_update_check", "production.update_mode_enabled", "production.update_mode_disabled"}.issubset(production_actions)


async def test_audit_stats_cleanup_and_date_filters(client):
    created = await client.post(
        "/api/connectors",
        json={"name": "Audit Date REST", "connector_type": "rest", "direction": "target", "config_json": {"url": "https://example.com"}},
    )
    assert created.status_code == 200

    now = datetime.now(timezone.utc)
    response = await client.get("/api/audit", params={"date_from": (now - timedelta(minutes=5)).isoformat(), "date_to": (now + timedelta(minutes=5)).isoformat(), "search": "Audit Date"})
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    stats = await client.get("/api/audit/stats")
    assert stats.status_code == 200
    assert stats.json()["total"] >= 1
    assert "connectors" in stats.json()["by_category"]

    cleanup = await client.post("/api/audit/cleanup", json={"retention_days": 1, "dry_run": True})
    assert cleanup.status_code == 200
    assert cleanup.json()["dry_run"] is True
