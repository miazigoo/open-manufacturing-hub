import base64

import httpx
import pytest


GS = "\x1d"


@pytest.mark.anyio
async def test_chz_aggregation_file_preview_parses_tab_separated_codes(client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    content = (
        f"010464615169781021ABC{GS}93TAIL\t00046306261900008223\n"
        f"010464615169781021DEF{GS}93TAIL\t00046306261900008223\n"
        f"010464615169781021GHI{GS}93TAIL\t00046306261900008224\n"
    ).encode("utf-8")

    response = await client.post(
        "/api/chz-aggregations/register-file/preview",
        files={"file": ("chz-packed-codes-26-0530_6543-2026-05-13.csv", content, "text/csv")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["order_number_1c"] == "260530/6543"
    assert body["order_number_external"] == "26-0530/6543"
    assert body["total_codes"] == 3
    assert body["total_aggregates"] == 2
    assert body["sample"]["first_aggregate_code"] == "00046306261900008223"
    assert "<GS>" in body["sample"]["first_code_preview"]


@pytest.mark.anyio
async def test_chz_aggregation_register_json_forwards_base64_groups(client, monkeypatch):
    from app.chz_aggregations import service

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    calls = []

    async def fake_forward(config, record, normalized):
        calls.append(service._onec_payload(record, normalized))
        return {"status": "success", "url": "http://onec.test/aggregation", "http_status": 200, "response": {"success": True, "status": "accepted"}}

    monkeypatch.setattr(service, "_forward_to_onec", fake_forward)
    encoded = base64.b64encode(f"010464615169781021ABC{GS}93TAIL".encode("ascii")).decode("ascii")

    response = await client.post(
        "/api/chz-aggregations/register",
        json={
            "source_system": "Laser service",
            "order_number": "260530/6543",
            "aggregates": [{"aggregate_code": "00046306261900008223", "full_codes_base64": [encoded]}],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "forwarded"
    assert body["registration"]["total_codes"] == 1
    payload = calls[0]["payload"]
    assert payload["order_number_1c"] == "260530/6543"
    assert payload["order_number_external"] == "26-0530/6543"
    forwarded_code = base64.b64decode(payload["aggregates"][0]["full_codes_base64"][0]).decode("ascii")
    assert forwarded_code == f"010464615169781021ABC{GS}93TAIL"


@pytest.mark.anyio
async def test_pull_from_dnp_proxies_request_and_logs_event(client, monkeypatch):
    from app.chz_aggregations import service

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    calls = []

    async def fake_request(config, payload):
        calls.append((config, payload))
        return {
            "ok": True,
            "order_number_1c": "260530/6543",
            "order_name_dnp": "26-0530/6543",
            "codes_count": 2,
            "boxes_count": 1,
            "tsv_text_base64": base64.b64encode(f"010464615169781021ABC{GS}93TAIL\t00046306261900008223\n".encode("ascii")).decode("ascii"),
            "rows": [{"full_code_base64": base64.b64encode(b"010464615169781021ABC").decode("ascii"), "sscc": "00046306261900008223"}],
        }

    monkeypatch.setattr(service, "_request_dnp_packed_codes", fake_request)
    monkeypatch.setattr(service, "_dnp_pull_runtime_config", _async_dnp_config("http://dnp.test/export-for-1c"))

    response = await client.post(
        "/api/chz-aggregations/pull-from-dnp",
        json={"order_number_1c": "260530/6543", "date_from": "2026-07-13", "date_to": "2026-07-13", "only_new": True},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["order_number_1c"] == "260530/6543"
    assert body["order_name_dnp"] == "26-0530/6543"
    assert body["codes_count"] == 2
    assert body["boxes_count"] == 1
    assert body["rows"][0]["sscc"] == "00046306261900008223"
    assert body["event_id"]
    assert body["timeline_url"] == f"/events/{body['event_id']}"

    config, payload = calls[0]
    assert config.export_url == "http://dnp.test/export-for-1c"
    assert payload == {
        "order_number_1c": "260530/6543",
        "date_from": "2026-07-13",
        "date_to": "2026-07-13",
        "only_new": True,
        "mark_exported": False,
    }

    timeline = await client.get(f"/api/events/{body['event_id']}/timeline")
    assert timeline.status_code == 200, timeline.text
    event = timeline.json()["event"] if "event" in timeline.json() else timeline.json()
    assert event["event_type"] == "chz.dnp_packed_codes_pull"
    assert event["status"] == "success"


@pytest.mark.anyio
async def test_pull_from_dnp_requires_export_url(client, monkeypatch):
    from app.chz_aggregations import service

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    monkeypatch.setattr(service, "_dnp_pull_runtime_config", _async_dnp_config(""))

    response = await client.post("/api/chz-aggregations/pull-from-dnp", json={"order_number_1c": "260530/6543"})

    assert response.status_code == 400, response.text
    assert "CHZ_DNP_PACKED_CODES_EXPORT_URL" in response.text


@pytest.mark.anyio
async def test_pull_from_dnp_dnp_error_is_reported_and_logged(client, monkeypatch):
    from app.chz_aggregations import service

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    async def fake_request(config, payload):
        from app.core.errors import BadRequestError

        raise BadRequestError("DnP rejected packed codes export with HTTP 404: order not found")

    monkeypatch.setattr(service, "_request_dnp_packed_codes", fake_request)
    monkeypatch.setattr(service, "_dnp_pull_runtime_config", _async_dnp_config("http://dnp.test/export-for-1c"))

    response = await client.post("/api/chz-aggregations/pull-from-dnp", json={"order_number_1c": "260530/6543", "only_new": False})

    assert response.status_code == 400, response.text
    assert "order not found" in response.text

    journal = await client.get("/api/events/journal")
    assert journal.status_code == 200, journal.text
    pull_events = [item for item in journal.json() if item.get("event_type") == "chz.dnp_packed_codes_pull"]
    assert pull_events, "failed pull must be recorded as an event"
    assert pull_events[0]["status"] == "failed"


def _async_dnp_config(export_url: str):
    from app.chz_aggregations.service import ChzDnpPullRuntimeConfig

    async def _config(session):
        return ChzDnpPullRuntimeConfig(export_url=export_url, timeout_seconds=5.0)

    return _config



@pytest.mark.anyio
async def test_chz_aggregation_settings_roundtrip_via_environment_variables(client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    patched = await client.patch(
        "/api/chz-aggregations/settings",
        json={"onec_url": "http://onec.test/hs/chz/aggregation", "onec_timeout_seconds": 240},
    )
    assert patched.status_code == 200, patched.text

    settings = await client.get("/api/chz-aggregations/settings")
    assert settings.status_code == 200, settings.text
    assert settings.json()["onec_url"] == "http://onec.test/hs/chz/aggregation"
    assert settings.json()["timeout_seconds"] == 240


@pytest.mark.anyio
async def test_aggregation_settings_can_replace_and_clear_authentication(client, session):
    from sqlalchemy import select
    from app.environments.models import EnvironmentVariable
    from app.secrets.models import Secret

    await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    url = "/api/chz-aggregations/settings"
    original = {"onec_url": "http://erp.test/report", "onec_timeout_seconds": 42,
                "onec_header_name": "Authorization", "onec_token": "Bearer test-token"}
    saved = await client.patch(url, json=original)
    assert saved.status_code == 200
    assert saved.json()["token_set"] is True
    assert saved.json()["header_name"] == "Authorization"
    assert "test-token" not in saved.text
    variable = await session.scalar(select(EnvironmentVariable).where(EnvironmentVariable.key == "CHZ_AGGREGATION_ONEC_TOKEN"))
    assert variable.value_json is None and variable.secret_ref
    secret = await session.scalar(select(Secret).where(Secret.name == variable.secret_ref))
    assert "test-token" not in secret.encrypted_value
    for address in ["https://erp.test/report", "http://erp.test:8080/report", "http://other.test/report", ""]:
        denied = await client.patch(url, json={"onec_url": address})
        assert denied.status_code == 400
    same_host = await client.patch(url, json={"onec_url": "http://erp.test:80/new-path"})
    assert same_host.status_code == 200
    new_address = await client.patch(url, json={"onec_url": "https://erp.test:9443/reports", "onec_token": "new-token"})
    downgrade = await client.patch(url, json={"onec_url": "http://erp.test:9443/reports"})
    assert downgrade.status_code == 400
    assert new_address.json()["timeout_seconds"] == 42
    assert new_address.json()["token_set"] is True
    for invalid in ({"onec_header_name": "Header: Wrong"}, {"onec_url": "ftp://erp.test"}, {"onec_url": "https://user:pass@erp.test/"}):
        assert (await client.patch(url, json=invalid)).status_code == 422
    cleared = await client.patch(url, json={"onec_url": "", "onec_token": ""})
    assert cleared.json()["onec_url"] == ""
    assert cleared.json()["token_set"] is False
    assert (await client.get(url)).json() == cleared.json()


@pytest.mark.anyio
@pytest.mark.parametrize(("erp_response", "expected"), [
    (httpx.Response(200, json={"success": True, "status": "accepted"}), True),
    (httpx.Response(201, json={"ok": True}), True),
    (httpx.Response(302, headers={"Location": "/login"}), False),
    (httpx.Response(200, text="<html>Login</html>"), False),
    (httpx.Response(200, json={"success": False}), False),
    (httpx.Response(200, json={"success": True, "ok": False}), False),
    (httpx.Response(200, json={}), False),
    (httpx.Response(204), False),
    (httpx.Response(202, json={"ok": True}), False),
    (httpx.Response(200, json={"ok": True, "status": "pending"}), False),
    (httpx.Response(200, json={"success": True, "status": "rejected"}), False),
    (httpx.Response(200, json={"success": True, "error": "failed"}), False),
])
async def test_registration_marks_forwarded_only_on_erp_acknowledgement(client, monkeypatch, erp_response, expected):
    from app.chz_aggregations import service

    await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    settings = {"onec_url": "https://erp.test:9443/report", "onec_header_name": "Authorization",
                "onec_token": "Bearer test-token"}
    await client.patch("/api/chz-aggregations/settings", json=settings)

    def receiver(request):
        assert str(request.url) == settings["onec_url"]
        assert request.headers["Authorization"] == settings["onec_token"]
        return erp_response

    async_client = httpx.AsyncClient
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **kwargs: async_client(transport=httpx.MockTransport(receiver), **kwargs))
    result = await client.post(
        "/api/chz-aggregations/register-file",
        data={"order_number": "26-0001/1000"},
        files={"file": ("test.csv", b"010123456789012321ABCD\x1d93TEST\t00046306261900008223\n", "text/csv")},
    )
    assert result.status_code == 200
    assert result.json()["success"] is expected
    assert result.json()["registration"]["status"] == ("forwarded" if expected else "failed")


@pytest.mark.anyio
async def test_disabled_route_records_a_skip_without_contacting_erp(client, monkeypatch):
    from app.chz_aggregations import service

    await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    payload = {"onec_url": "https://erp.test:9443/hs/chz/aggregation", "onec_enabled": False}
    response = await client.patch("/api/chz-aggregations/settings", json=payload)
    assert response.json()["onec_enabled"] is False

    def unexpected_http(**kwargs):
        pytest.fail("Disabled route attempted an HTTP exchange.")

    monkeypatch.setattr(service.httpx, "AsyncClient", unexpected_http)

    result = await client.post(
        "/api/chz-aggregations/register-file",
        data={"order_number": "26-0001/1000", "source_document_id": "test-batch-001"},
        files={"file": ("test.csv", b"010123456789012321ABCD\x1d93TEST\t00046306261900008223\n", "text/csv")},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["success"] is False
    assert body["status"] == "skipped"
    assert body["registration"]["metadata_json"]["onec_forward"] == {
        "status": "skipped", "reason": "onec_forward_disabled", "delivery_attempted": False,
    }
    journal = await client.get("/api/chz-aggregations/registrations", params={"source_document_id": "test-batch-001"})
    assert [item["id"] for item in journal.json()] == [body["registration"]["id"]]
    other_batch = await client.get("/api/chz-aggregations/registrations", params={"source_document_id": "another-batch"})
    assert other_batch.json() == []
