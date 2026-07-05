from __future__ import annotations

from app.audit.diff import SECRET_MARKER


async def _create_rule(client):
    response = await client.post(
        "/api/business-rules",
        json={
            "name": "Versioned Router",
            "description": "initial",
            "enabled": True,
            "scope": "global",
            "rules_json": {"mode": "first_match", "rules": []},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_config_version_draft_publish_rollback_and_audit(client):
    rule = await _create_rule(client)
    versions = await client.get(f"/api/config/business_rule/{rule['id']}/versions")
    assert versions.status_code == 200, versions.text
    body = versions.json()
    assert body["active_version"]["version_number"] == 1
    assert body["draft_version"] is None

    draft_config = dict(body["active_version"]["config_json"])
    draft_config["description"] = "draft change"
    draft_config["rules_json"] = {
        "mode": "first_match",
        "rules": [
            {"name": "DNP", "if": {"operator": "eq", "path": "payload.pool_type", "value": "DNP"}, "then": [{"action": "set_route", "value": "dnp"}]}
        ],
    }
    draft = await client.post(f"/api/config/business_rule/{rule['id']}/draft", json={"config_json": draft_config, "comment": "prepare route"})
    assert draft.status_code == 200, draft.text
    draft_body = draft.json()
    assert draft_body["status"] == "draft"
    assert draft_body["version_number"] == 2

    live = await client.get(f"/api/business-rules/{rule['id']}")
    assert live.json()["description"] == "initial"

    diff = await client.get(f"/api/config/business_rule/{rule['id']}/diff?from_version={body['active_version']['id']}&to_version={draft_body['id']}")
    assert diff.status_code == 200, diff.text
    assert any(item["path"] == "description" for item in diff.json()["changed"])

    tested = await client.post(f"/api/config/business_rule/{rule['id']}/versions/{draft_body['id']}/test", json={"payload": {"pool_type": "DNP"}})
    assert tested.status_code == 200, tested.text
    assert tested.json()["test_status"] == "passed"
    assert tested.json()["timeline_url"].startswith("/events/")

    published = await client.post(f"/api/config/business_rule/{rule['id']}/publish", json={"version_id": draft_body["id"], "comment": "publish tested rule"})
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "active"

    live = await client.get(f"/api/business-rules/{rule['id']}")
    assert live.json()["description"] == "draft change"
    assert live.json()["rules_json"]["rules"][0]["name"] == "DNP"

    rollback = await client.post(f"/api/config/business_rule/{rule['id']}/rollback", json={"target_version_id": body["active_version"]["id"], "comment": "restore previous"})
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["status"] == "rollback"

    live = await client.get(f"/api/business-rules/{rule['id']}")
    assert live.json()["description"] == "initial"

    audit = await client.get("/api/audit?category=config_versions")
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"config.draft_created", "config.version_tested", "config.published", "config.rollback"}.issubset(actions)


async def test_config_diff_redacts_secret_values(client):
    rule = await _create_rule(client)
    versions = (await client.get(f"/api/config/business_rule/{rule['id']}/versions")).json()
    draft_config = dict(versions["active_version"]["config_json"])
    draft_config["rules_json"] = {"mode": "first_match", "rules": [], "api_token": "super-secret-token"}
    draft = (await client.post(f"/api/config/business_rule/{rule['id']}/draft", json={"config_json": draft_config})).json()
    diff = await client.get(f"/api/config/business_rule/{rule['id']}/diff?from_version={versions['active_version']['id']}&to_version={draft['id']}")
    assert diff.status_code == 200
    assert SECRET_MARKER in str(diff.json())
    assert "super-secret-token" not in str(diff.json())


async def test_mapping_draft_test_publish_creates_runtime_mapping_version(client):
    mapping = await client.post(
        "/api/mappings",
        json={
            "name": "Versioned Mapping",
            "source_entity": "Order",
            "target_entity": "Order",
            "initial_version": {"rules_json": [{"source": "order_id", "target": "id", "transform": "str"}], "source_schema_json": {}, "target_schema_json": {}},
        },
    )
    assert mapping.status_code == 200, mapping.text
    mapping_body = mapping.json()
    versions = (await client.get(f"/api/config/mapping/{mapping_body['id']}/versions")).json()
    draft_config = dict(versions["active_version"]["config_json"])
    draft_config["version_payload"] = {"rules_json": [{"source": "order_id", "target": "id", "transform": "str"}, {"constant": "SalesOrder", "target": "entity"}], "source_schema_json": {}, "target_schema_json": {}, "notes": "draft"}
    draft = (await client.post(f"/api/config/mapping/{mapping_body['id']}/draft", json={"config_json": draft_config})).json()
    tested = await client.post(f"/api/config/mapping/{mapping_body['id']}/versions/{draft['id']}/test", json={"payload": {"order_id": 1532}})
    assert tested.status_code == 200, tested.text
    assert tested.json()["result"]["preview"]["entity"] == "SalesOrder"
    published = await client.post(f"/api/config/mapping/{mapping_body['id']}/publish", json={"version_id": draft["id"], "comment": "publish mapping"})
    assert published.status_code == 200, published.text
    live = (await client.get(f"/api/mappings/{mapping_body['id']}")).json()
    assert len(live["versions"]) == 2
    assert live["versions"][-1]["rules_json"][-1]["target"] == "entity"
