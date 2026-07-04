from app.connectors.builtin.onec.schemas import OneCReadResult
from app.connectors.builtin.onec_connector import OneCConnector


ONEC_ITEMS = [
    {
        "Ref_Key": "ORDER-1",
        "Number": "SO-0001",
        "Date": "2026-07-02T10:00:00",
        "Партнер_Key": "CUST-1",
        "Склад_Key": "MAIN",
        "Комментарий": "demo",
        "Товары": [{"Номенклатура_Key": "SKU-1", "Количество": 2, "Цена": 100}],
    }
]


async def _install_onec_package(client):
    response = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert response.status_code == 200, response.text


async def test_onec_scenario_installer_creates_end_to_end_assets(client):
    await _install_onec_package(client)
    presets = await client.get("/api/onec-scenarios/presets")
    assert presets.status_code == 200
    assert presets.json()[0]["key"] == "onec_sales_order_to_mock_wms"

    installed = await client.post("/api/onec-scenarios/install-sales-order-demo")
    assert installed.status_code == 200
    body = installed.json()
    assert body["source_connector_id"]
    assert body["workflow_id"]
    assert body["polling_job_id"]
    assert "onec_sales_order_to_canonical_sales_order" in body["mappings"]

    jobs = (await client.get("/api/polling/jobs")).json()
    assert any(job["name"] == "Poll 1C sales orders" for job in jobs)


async def test_onec_polling_run_once_is_idempotent_and_executes_workflow(monkeypatch, client):
    await _install_onec_package(client)
    async def fake_read_odata(self, config, resource, query=None, context=None):
        return OneCReadResult(True, items=ONEC_ITEMS, count=len(ONEC_ITEMS), request_payload={"resource": resource, "query": query})

    monkeypatch.setattr(OneCConnector, "read_odata", fake_read_odata)
    installed = (await client.post("/api/onec-scenarios/install-sales-order-demo")).json()
    job_id = installed["polling_job_id"]

    first = await client.post(f"/api/polling/jobs/{job_id}/run-once")
    assert first.status_code == 200
    first_run = first.json()
    assert first_run["status"] == "success"
    assert first_run["events_created"] == 1
    assert first_run["items_skipped"] == 0

    second = (await client.post(f"/api/polling/jobs/{job_id}/run-once")).json()
    assert second["status"] == "success"
    assert second["events_created"] == 0
    assert second["items_skipped"] == 1

    event_id = first_run["details_json"]["created_event_ids"][0]
    timeline = (await client.get(f"/api/events/{event_id}/timeline")).json()
    run = timeline["runs"][0]
    assert run["workflow_name"] == "1C SalesOrder to WMS ShipmentOrder"
    steps = [step["step_name"] for step in run["steps"]]
    assert steps.count("map_payload") == 2
    assert run["status"] == "success"
