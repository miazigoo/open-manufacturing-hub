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
