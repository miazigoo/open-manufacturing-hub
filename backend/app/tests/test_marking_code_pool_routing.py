import base64

import pytest

from app.marking_code_pools.gs1 import GS, parse_code

CODE_A = f"010464615169781021ABC123{GS}93TAIL"
CODE_B = f"010999999999991021XYZ789{GS}93TAIL"


def _b64(code: str) -> str:
    return base64.b64encode(code.encode("ascii")).decode("ascii")


def test_gs1_parse_full_code():
    parsed = parse_code(CODE_A)
    assert parsed["gtin"] == "04646151697810"
    assert parsed["serial"] == "ABC123"
    assert parsed["ai93"] == "TAIL"


def test_gs1_parse_tolerates_broken_code():
    assert parse_code("garbage")["gtin"] == ""
    assert parse_code("0104646151697810")["serial"] == ""
    assert parse_code("")["code"] == ""


@pytest.mark.anyio
async def test_routing_rules_crud(client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    created = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={
            "name": "GTIN 04646 -> laser + service",
            "priority": 10,
            "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04646"}]},
            "targets_json": [
                {"type": "laser_file"},
                {"type": "http_forward", "name": "Other service", "url": "http://example.local/codes", "header_name": "X-Token", "token": "t"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    rule = created.json()
    assert rule["enabled"] is True
    assert rule["targets_json"][1]["url"] == "http://example.local/codes"

    rules = await client.get("/api/marking-code-pools/routing-rules")
    assert rules.status_code == 200
    assert len(rules.json()) == 1

    patched = await client.patch(f"/api/marking-code-pools/routing-rules/{rule['id']}", json={"enabled": False, "priority": 5})
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is False
    assert patched.json()["priority"] == 5

    deleted = await client.delete(f"/api/marking-code-pools/routing-rules/{rule['id']}")
    assert deleted.status_code == 204
    rules = await client.get("/api/marking-code-pools/routing-rules")
    assert rules.json() == []


@pytest.mark.anyio
async def test_routing_rule_rejects_invalid_matcher_and_target(client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    bad_matcher = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={"name": "bad", "match_json": {"mode": "all", "rules": [{"type": "no_such_type"}]}, "targets_json": []},
    )
    assert bad_matcher.status_code == 400

    bad_target = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={"name": "bad", "match_json": {}, "targets_json": [{"type": "http_forward"}]},
    )
    assert bad_target.status_code == 422


@pytest.mark.anyio
async def test_routing_rules_test_endpoint_splits_codes(client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    created = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={
            "name": "laser codes",
            "priority": 10,
            "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04646"}]},
            "targets_json": [{"type": "laser_file"}],
        },
    )
    assert created.status_code == 200, created.text

    response = await client.post(
        "/api/marking-code-pools/routing-rules/test",
        json={"full_codes_base64": [_b64(CODE_A), _b64(CODE_B)], "order_number": "260530/6543"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_codes"] == 2
    assert body["matched_codes"] == 1
    assert body["default_codes"] == 1
    first, second = body["results"]
    assert first["gtin"] == "04646151697810"
    assert first["rule_name"] == "laser codes"
    assert first["segment"] == "rule:laser codes"
    assert first["targets"] == [{"type": "laser_file", "file_name_template": None, "name": None, "url": None, "method": "POST", "header_name": None, "token": None, "timeout_seconds": None}]
    assert second["segment"] == "default"
    assert second["rule_id"] is None
    assert "<GS>" in first["code_preview"]


@pytest.mark.anyio
async def test_routing_rules_respect_priority_first_match(client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    for name, priority in [("broad", 50), ("specific", 10)]:
        created = await client.post(
            "/api/marking-code-pools/routing-rules",
            json={
                "name": name,
                "priority": priority,
                "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04" if name == "broad" else "04646"}]},
                "targets_json": [],
            },
        )
        assert created.status_code == 200, created.text

    response = await client.post(
        "/api/marking-code-pools/routing-rules/test",
        json={"full_codes_base64": [_b64(CODE_A)]},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["rule_name"] == "specific"


@pytest.mark.anyio
async def test_export_splits_pool_by_routing_rule(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("OMH_CHZ_LASER_FILE_ENABLED", "false")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"ok": True}

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    rule = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={
            "name": "Laser line 1",
            "priority": 10,
            "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04646"}]},
            "targets_json": [{"type": "http_forward", "name": "Line1Service", "url": "http://line1.local/codes"}],
        },
    )
    assert rule.status_code == 200, rule.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260530/6543",
            "full_codes_base64": [_b64(CODE_A), _b64(CODE_B), _b64(CODE_A.replace("ABC123", "DEF456"))],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert len(body["segments"]) == 2
    by_segment = {item["segment"]: item for item in body["segments"]}
    assert by_segment["rule:Laser line 1"]["total_codes"] == 2
    assert by_segment["default"]["total_codes"] == 1

    assert len(calls) == 1
    assert calls[0]["url"] == "http://line1.local/codes"
    forwarded = calls[0]["json"]["payload"]
    assert forwarded["total_codes"] == 2
    assert len(forwarded["full_codes_base64"]) == 2
    decoded = {base64.b64decode(item).decode("ascii") for item in forwarded["full_codes_base64"]}
    assert CODE_B not in decoded

    files = sorted(tmp_path.iterdir())
    assert len(files) == 2
    rule_file = next(file for file in files if "Laser_line_1" in file.name)
    assert len(rule_file.read_bytes().splitlines()) == 2

    exports = await client.get("/api/marking-code-pools/exports")
    assert exports.status_code == 200
    rows = exports.json()
    assert len(rows) == 2
    rule_row = next(row for row in rows if row["metadata_json"].get("segment") == "rule:Laser line 1")
    assert rule_row["status"] == "forwarded"
    default_row = next(row for row in rows if row["metadata_json"].get("segment") == "default")
    assert default_row["status"] == "saved"


@pytest.mark.anyio
async def test_export_without_rules_has_no_segments(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={"order_number": "260530/6543", "full_codes_base64": [_b64(CODE_A)]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["segments"] == []
    assert "segments" not in body["export"]["metadata_json"]


@pytest.mark.anyio
async def test_preview_shows_segments(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    rule = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={
            "name": "GTIN 04646",
            "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04646"}]},
            "targets_json": [{"type": "laser_file"}],
        },
    )
    assert rule.status_code == 200, rule.text

    preview = await client.post(
        "/api/marking-code-pools/onec/export-file/preview",
        json={"order_number": "260530/6543", "full_codes_base64": [_b64(CODE_A), _b64(CODE_B)]},
    )
    assert preview.status_code == 200, preview.text
    segments = preview.json()["segments"]
    assert len(segments) == 2
    assert segments[0]["rule_name"] == "GTIN 04646"
    assert segments[0]["total_codes"] == 1
    assert segments[1]["segment"] == "default"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.anyio
async def test_retry_forward_uses_routing_target(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"ok": True}

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls.append({"url": url, "json": json})
            return FakeResponse()

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    rule = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={
            "name": "Target rule",
            "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04646"}]},
            "targets_json": [{"type": "http_forward", "name": "RetryTarget", "url": "http://retry.local/codes"}],
        },
    )
    assert rule.status_code == 200, rule.text

    exported = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={"order_number": "260530/6543", "full_codes_base64": [_b64(CODE_A)]},
    )
    assert exported.status_code == 200, exported.text
    export_id = exported.json()["export"]["id"]
    assert calls and calls[0]["url"] == "http://retry.local/codes"

    retried = await client.post(f"/api/marking-code-pools/exports/{export_id}/retry-forward")
    assert retried.status_code == 200, retried.text
    assert retried.json()["success"] is True
    assert calls[-1]["url"] == "http://retry.local/codes"
    assert len(calls) == 2


@pytest.mark.anyio
async def test_actions_override_blocks_rule_targets(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls.append(url)
            raise AssertionError("no HTTP call expected when external_forward override is false")

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    rule = await client.post(
        "/api/marking-code-pools/routing-rules",
        json={
            "name": "Guarded rule",
            "match_json": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "gtin", "value": "04646"}]},
            "targets_json": [{"type": "http_forward", "name": "GuardedTarget", "url": "http://guarded.local/codes"}],
        },
    )
    assert rule.status_code == 200, rule.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260530/6543",
            "full_codes_base64": [_b64(CODE_A)],
            "actions_override": {"local_outbox": True, "laser_file": False, "external_forward": False},
        },
    )
    assert response.status_code == 200, response.text
    assert calls == []
    rule_action = response.json()["export"]["metadata_json"]["actions"]["http_forward:GuardedTarget"]
    assert rule_action["status"] == "disabled"
    assert rule_action["reason"] == "disabled by request actions_override"
