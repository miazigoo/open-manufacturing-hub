import pytest

pytestmark = pytest.mark.anyio

TEMPLATE = {
    "slug": "tsd-priemka",
    "name": "Приемка с ТСД",
    "input_mode": "json",
    "schema_json": {
        "fields": [
            {"path": "order_number", "type": "string", "required": True},
            {"path": "warehouse", "type": "string", "required": True, "default": "MAIN"},
            {"path": "qty", "type": "number", "required": True, "default": 0},
            {"path": "items", "type": "array", "required": False},
            {"path": "scan_guid", "type": "guid", "required": False},
        ]
    },
}


async def _create_template(client, **overrides):
    response = await client.post("/api/inbox-templates", json={**TEMPLATE, **overrides})
    assert response.status_code == 200, response.text
    return response.json()


async def test_inbox_template_crud(client):
    template = await _create_template(client)
    assert template["slug"] == "tsd-priemka"
    assert template["auth_token_set"] is False

    duplicate = await client.post("/api/inbox-templates", json=TEMPLATE)
    assert duplicate.status_code == 400
    assert "уже существует" in duplicate.text

    patched = await client.patch(f"/api/inbox-templates/{template['id']}", json={"description": "Прием коробок", "enabled": False})
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is False

    disabled = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1})
    assert disabled.status_code == 403
    assert "выключен" in disabled.text

    await client.patch(f"/api/inbox-templates/{template['id']}", json={"enabled": True})
    deleted = await client.delete(f"/api/inbox-templates/{template['id']}")
    assert deleted.status_code == 204
    missing = await client.post("/api/inbox/tsd-priemka", json={})
    assert missing.status_code == 404


async def test_inbox_receive_valid_payload_stores_record(client):
    await _create_template(client)
    response = await client.post(
        "/api/inbox/tsd-priemka",
        json={"order_number": "260530/6543", "warehouse": "MAIN", "qty": "12", "items": [{"code": "c1"}], "scan_guid": "4b66e3ba-76cd-11f1-80d6-000c29b755c7"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["status"] in {"stored", "accepted_with_warnings"}

    records = (await client.get("/api/inbox-records")).json()
    assert records["total"] == 1
    item = records["items"][0]
    assert item["fields_json"]["order_number"] == "260530/6543"
    assert item["fields_json"]["qty"] == 12.0
    assert any("строкой" in warning["message"] for warning in item["warnings_json"])

    detail = await client.get(f"/api/inbox-records/{item['id']}")
    assert detail.status_code == 200


async def test_inbox_reject_policy_returns_clear_error(client):
    await _create_template(client)
    response = await client.post("/api/inbox/tsd-priemka", json={"warehouse": "MAIN"})
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["ok"] is False
    assert "order_number" in body["missing_required"]
    assert "qty" in body["missing_required"]
    assert "обязательных полей" in body["message"]

    records = (await client.get("/api/inbox-records?status=rejected")).json()
    assert records["total"] == 1
    assert records["items"][0]["status"] == "rejected"


async def test_inbox_accept_warning_policy(client):
    await _create_template(client, missing_policy="accept_warning")
    response = await client.post("/api/inbox/tsd-priemka", json={"warehouse": "MAIN", "qty": 3})
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    records = (await client.get("/api/inbox-records")).json()
    assert records["items"][0]["status"] == "accepted_with_warnings"
    assert any("order_number" in warning["path"] for warning in records["items"][0]["warnings_json"])


async def test_inbox_fill_defaults_policy(client):
    await _create_template(client, missing_policy="fill_defaults")
    response = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1"})
    assert response.status_code == 200, response.text
    records = (await client.get("/api/inbox-records")).json()
    fields = records["items"][0]["fields_json"]
    assert fields["warehouse"] == "MAIN"
    assert fields["qty"] == 0
    assert any("подставлено" in warning["message"] for warning in records["items"][0]["warnings_json"])


async def test_inbox_storage_none_keeps_no_record(client):
    await _create_template(client, storage_mode="none")
    response = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1})
    assert response.status_code == 200, response.text
    assert (await client.get("/api/inbox-records")).json()["total"] == 0


async def test_inbox_auth_token(client):
    await _create_template(client, auth_token="secret-token")
    no_token = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1})
    assert no_token.status_code == 401
    bad_token = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1}, headers={"X-OMH-Token": "wrong"})
    assert bad_token.status_code == 401
    good = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1}, headers={"X-OMH-Token": "secret-token"})
    assert good.status_code == 200


async def test_inbox_template_test_endpoint(client):
    template = await _create_template(client)
    response = await client.post(f"/api/inbox-templates/{template['id']}/test", json={"payload": {"warehouse": "W"}})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "rejected"
    assert any(warning["path"] == "order_number" for warning in body["warnings"]) is False
    assert (await client.get("/api/inbox-records")).json()["total"] == 0


async def test_inbox_custom_response_template(client):
    await _create_template(client, response_json={"prinjato": True, "zakaz": "{{fields.order_number}}", "zapis": "{{record.id}}"})
    response = await client.post("/api/inbox/tsd-priemka", json={"order_number": "Z-1", "warehouse": "W", "qty": 2})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prinjato"] is True
    assert body["zakaz"] == "Z-1"
    assert body["zapis"]


async def test_inbox_timeline_event_logged(client):
    await _create_template(client)
    response = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1})
    assert response.status_code == 200
    journal = await client.get("/api/events/journal")
    inbox_events = [item for item in journal.json() if item["event_type"] == "inbox.received"]
    assert inbox_events, "inbox event must be logged to timeline"


async def test_inbox_retention_deletes_old_records(client, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from app.core.database import async_session
    from app.data_inbox.models import InboxRecord

    template = await _create_template(client, storage_mode="days", storage_days=7)
    response = await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1})
    assert response.status_code == 200
    async with async_session() as session:
        record = (await session.execute(__import__("sqlalchemy").select(InboxRecord))).scalar_one()
        record.created_at = datetime.now(UTC) - timedelta(days=30)
        await session.commit()

    preview = (await client.get("/api/retention/preview")).json()
    assert preview["aged_inbox_records"] == 1
    await client.post("/api/retention/cleanup")
    assert (await client.get("/api/inbox-records")).json()["total"] == 0


async def test_sql_console_allows_select(client):
    await _create_template(client)
    await client.post("/api/inbox/tsd-priemka", json={"order_number": "A1", "warehouse": "W", "qty": 1})
    response = await client.post("/api/sql-console/query", json={"query": "select status, count(*) as cnt from inbox_records group by status"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["columns"] == ["status", "cnt"]
    assert body["rows"][0]["status"] in {"stored", "accepted_with_warnings"}
    assert body["elapsed_ms"] >= 0


async def test_sql_console_blocks_writes_and_multistatements(client):
    for query in [
        "drop table inbox_records",
        "insert into inbox_records (id) values ('x')",
        "select 1; select 2",
        "update inbox_records set status='x'",
        "delete from inbox_records",
    ]:
        response = await client.post("/api/sql-console/query", json={"query": query})
        assert response.status_code == 400, query
        assert "SELECT" in response.text or "один запрос" in response.text


async def test_sql_console_limit(client):
    response = await client.post("/api/sql-console/query", json={"query": "select 1 as one union all select 2 union all select 3", "limit": 2})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["row_count"] == 2
    assert body["truncated"] is True


async def test_db_backup_to_custom_dir(client, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("OMH_BACKUP_DIR", str(tmp_path))
    get_settings.cache_clear()

    response = await client.post("/api/production/backups/db")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["size_bytes"] > 0
    files = list(tmp_path.glob("omh-db-*.dump"))
    assert len(files) == 1

    download = await client.get(f"/api/production/exports/{body['id']}/download")
    assert download.status_code == 200


async def test_db_backup_dir_override_via_environment_variable(client, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("OMH_BACKUP_DIR", "/nonexistent-readonly-path-xyz")
    get_settings.cache_clear()
    env_response = await client.post("/api/environments", json={"name": "Backup Env", "code": "backup-env", "environment_type": "development", "is_current": True, "variables": []})
    assert env_response.status_code == 200, env_response.text
    env_id = env_response.json()["id"]
    variable = await client.post(f"/api/environments/{env_id}/variables", json={"key": "BACKUP_DIR", "value_json": str(tmp_path)})
    assert variable.status_code == 200, variable.text

    response = await client.post("/api/production/backups/db")
    assert response.status_code == 200, response.text
    assert len(list(tmp_path.glob("omh-db-*.dump"))) == 1
