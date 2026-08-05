import base64

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

