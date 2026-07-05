from __future__ import annotations

from app.core.database import async_session
from app.core.enums import IntegrationPackageStatus, SecretType
from app.packages.models import InstalledPackage
from app.secrets.models import Secret


async def _create_current_environment(client, *, code: str = "dev") -> dict:
    response = await client.post(
        "/api/environments",
        json={
            "name": f"{code.upper()} Environment",
            "code": code,
            "environment_type": "development" if code == "dev" else "production",
            "is_current": True,
            "base_url": f"https://{code}.example.test",
            "variables": [{"key": "RULE_SCOPE", "value_json": "global", "description": "Rule scope"}],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _create_rule_with_draft(client) -> tuple[dict, dict]:
    rule = await client.post(
        "/api/business-rules",
        json={"name": "Promoted Rule", "description": "initial", "enabled": True, "scope": "global", "rules_json": {"mode": "first_match", "rules": []}},
    )
    assert rule.status_code == 200, rule.text
    rule_body = rule.json()
    versions = (await client.get(f"/api/config/business_rule/{rule_body['id']}/versions")).json()
    draft_config = dict(versions["active_version"]["config_json"])
    draft_config["description"] = "uses env and secret references"
    draft_config["scope"] = {"$env": "RULE_SCOPE"}
    draft_config["rules_json"] = {"mode": "first_match", "rules": [], "audit_token": {"$secret": "promotion-token"}}
    draft = await client.post(f"/api/config/business_rule/{rule_body['id']}/draft", json={"config_json": draft_config, "comment": "prepare promotion"})
    assert draft.status_code == 200, draft.text
    return rule_body, draft.json()


async def test_environment_profiles_variables_and_current_switch(client):
    dev = await _create_current_environment(client, code="dev")
    prod = await client.post("/api/environments", json={"name": "Production", "code": "prod", "environment_type": "production", "is_current": False})
    assert prod.status_code == 200, prod.text

    patched = await client.patch(f"/api/environments/{prod.json()['id']}", json={"description": "Live factory profile"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["description"] == "Live factory profile"

    variable = await client.post(f"/api/environments/{prod.json()['id']}/variables", json={"key": "API_BASE_URL", "value_json": "https://api.example.test"})
    assert variable.status_code == 200, variable.text
    assert variable.json()["key"] == "API_BASE_URL"

    current = await client.post(f"/api/environments/{prod.json()['id']}/set-current")
    assert current.status_code == 200, current.text
    assert current.json()["is_current"] is True
    current_lookup = await client.get("/api/environments/current")
    assert current_lookup.json()["code"] == "prod"

    delete_current = await client.delete(f"/api/environments/{prod.json()['id']}")
    assert delete_current.status_code == 400
    delete_old = await client.delete(f"/api/environments/{dev['id']}")
    assert delete_old.status_code == 204


async def test_change_set_export_preview_apply_with_environment_resolution(client):
    await _create_current_environment(client, code="dev")
    rule, draft = await _create_rule_with_draft(client)
    created = await client.post(
        "/api/change-sets/from-drafts",
        json={"name": "Promote business rule", "description": "draft to production", "object_refs": [{"object_type": "business_rule", "object_id": rule["id"]}]},
    )
    assert created.status_code == 200, created.text
    assert created.json()["items"][0]["version_id"] == draft["id"]

    exported = await client.get(f"/api/change-sets/{created.json()['id']}/export")
    assert exported.status_code == 200, exported.text
    payload = exported.json()
    assert payload["omh_change_set_version"] == 1
    assert "real-token" not in str(payload)

    preview_missing = await client.post("/api/change-sets/import/preview", json={"change_set": payload})
    assert preview_missing.status_code == 200, preview_missing.text
    body = preview_missing.json()
    assert body["valid"] is False
    assert body["missing_secrets"]
    blocked = await client.post("/api/change-sets/import/apply", json={"change_set": payload, "mapping": {"allow_conflicts": True}})
    assert blocked.status_code == 400

    async with async_session() as session:
        session.add(Secret(name="promotion-token", secret_type=SecretType.API_TOKEN, encrypted_value="encrypted", value_preview="***", enabled=True))
        await session.commit()

    apply_response = await client.post("/api/change-sets/import/apply", json={"change_set": payload, "mapping": {"run_smoke_tests": True}})
    assert apply_response.status_code == 200, apply_response.text
    applied = apply_response.json()
    assert applied["applied"] is True
    assert applied["smoke"]["failed"] == 0

    live = await client.get(f"/api/business-rules/{rule['id']}")
    assert live.status_code == 200
    assert live.json()["scope"] == "global"
    assert live.json()["description"] == "uses env and secret references"
    assert live.json()["rules_json"]["audit_token"] == {"$secret": "promotion-token"}


async def test_change_set_preview_reports_missing_package_secret_and_env_var(client):
    await _create_current_environment(client, code="dev")
    payload = {
        "omh_change_set_version": 1,
        "name": "Missing dependencies",
        "description": None,
        "created_at": "2026-07-05T00:00:00+00:00",
        "source_environment": "dev",
        "secrets_policy": "references_only",
        "required_packages": [{"package_id": "omh-package-onec", "version": ">=0.1.0"}],
        "items": [
            {
                "object_type": "business_rule",
                "object_id": None,
                "object_name": "Package-bound rule",
                "operation": "create",
                "config_json": {"name": "Package-bound rule", "enabled": True, "scope": {"$env": "MISSING_SCOPE"}, "rules_json": {"mode": "first_match", "rules": [], "token": {"$secret": "missing-token"}}},
                "dependencies_json": {"required_packages": [{"package_id": "omh-package-onec", "version": ">=0.1.0"}], "secret_refs": [{"name": "missing-token", "path": "rules_json.token"}], "environment_refs": [{"key": "MISSING_SCOPE", "path": "scope"}]},
            }
        ],
        "warnings": [],
    }
    preview = await client.post("/api/change-sets/import/preview", json={"change_set": payload})
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["valid"] is False
    assert body["missing_packages"][0]["package_id"] == "omh-package-onec"
    assert body["missing_secrets"][0]["name"] == "missing-token"
    assert body["missing_environment_variables"][0]["key"] == "MISSING_SCOPE"

    async with async_session() as session:
        session.add(InstalledPackage(package_id="omh-package-onec", name="1C Package", version="0.1.0", status=IntegrationPackageStatus.ENABLED, enabled=True, manifest_json={}))
        session.add(Secret(name="missing-token", secret_type=SecretType.API_TOKEN, encrypted_value="encrypted", value_preview="***", enabled=True))
        await session.commit()

    fixed = await client.post("/api/change-sets/import/preview", json={"change_set": payload, "mapping": {"environment_variables": {"MISSING_SCOPE": "global"}}})
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["valid"] is True
