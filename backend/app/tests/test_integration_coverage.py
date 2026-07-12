from __future__ import annotations

import subprocess
import sys
from pathlib import Path


async def test_integration_coverage_list_summary_and_package_statuses(client):
    response = await client.get("/api/integration-coverage")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["summary"]["total"] >= 11
    assert body["summary"]["ready"] >= 2
    assert body["summary"]["partial"] >= 1
    assert body["summary"]["average_readiness"] > 50
    assert body["summary"]["by_status"]["ready"] == body["summary"]["ready"]

    ids = {item["requirement_id"] for item in body["items"]}
    assert "external_api_asks_1c_by_inn" in ids
    assert "dnp_chz_code_pool_sync" in ids
    assert "poll_odata_send_target" in ids

    dnp = next(item for item in body["items"] if item["requirement_id"] == "dnp_chz_code_pool_sync")
    assert dnp["recommended_pattern"] == "request_odata_object_foreach_send_endpoint"
    assert dnp["wizard_route"] == "/master?pattern=request_odata_object_foreach_send_endpoint"
    assert dnp["package_statuses"]
    assert dnp["package_statuses"][0]["installed"] is False


async def test_integration_coverage_ready_detail_has_full_score(client):
    response = await client.get("/api/integration-coverage/external_api_asks_1c_by_inn")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["status"] == "ready"
    assert body["readiness_score"] == 100
    assert body["statuses"] == {"wizard": "ready", "docs": "ready", "training": "ready", "troubleshooting": "ready", "e2e": "ready"}
    assert body["docs_links"] == ["/docs/onec/recipes/external-service-lookup-contractor"]
    assert body["training_example_ids"] == ["training.onec.find_contractor_by_inn"]


async def test_integration_coverage_order_xml_response_is_ready_and_polling_is_partial(client):
    order_xml = await client.get("/api/integration-coverage/external_api_asks_1c_order_xml_response")
    assert order_xml.status_code == 200, order_xml.text
    order_body = order_xml.json()
    assert order_body["status"] == "ready"
    assert order_body["readiness_score"] == 100
    assert order_body["docs_links"] == ["/docs/onec/recipes/request-odata-xml-response"]
    assert order_body["training_example_ids"] == ["training.onec.lookup_order_products_xml"]
    assert order_body["e2e_tests"] == ["test_request_multiple_odata_response_preview_xml_order_products", "test_request_multiple_odata_response_create_creates_disabled_flow_test_case_and_run_test"]
    assert order_body["gaps"] == []

    polling = await client.get("/api/integration-coverage/poll_odata_send_target")
    assert polling.status_code == 200, polling.text
    polling_body = polling.json()
    assert polling_body["status"] == "partial"
    assert polling_body["wizard_route"] == "/master?pattern=poll_odata_send_target"
    assert polling_body["recipe_link"] == "/docs/onec/recipes/poll-odata-send-target"
    assert polling_body["training_example_ids"] == ["training.polling.odata_orders_to_wms"]
    assert polling_body["statuses"]["wizard"] == "ready"
    assert polling_body["statuses"]["docs"] == "ready"
    assert polling_body["statuses"]["e2e"] == "ready"
    assert any("Manual run" in gap or "scheduler" in gap for gap in polling_body["gaps"])


async def test_integration_coverage_wms_shipment_fact_is_ready(client):
    response = await client.get("/api/integration-coverage/wms_shipment_fact_to_onec")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["readiness_score"] == 100
    assert body["recommended_pattern"] == "wms_fact_to_onec"
    assert body["wizard_route"] == "/master?pattern=wms_fact_to_onec"
    assert body["docs_links"] == ["/docs/onec/scenarios/wms-api-to-1c", "/docs/onec/recipes/wms-shipment-fact-to-onec"]
    assert body["training_example_ids"] == ["training.wms.shipment_fact_to_onec"]
    assert body["e2e_tests"] == ["test_wms_fact_to_onec_preview_shipment_pattern", "test_wms_fact_to_onec_create_creates_disabled_flow_and_run_test"]
    assert body["gaps"] == []


async def test_integration_coverage_summary_and_report_endpoints(client):
    summary = await client.get("/api/integration-coverage/summary")
    assert summary.status_code == 200, summary.text
    assert summary.json()["total"] >= 11

    report = await client.get("/api/integration-coverage/report")
    assert report.status_code == 200, report.text
    markdown = report.json()["markdown"]
    assert "Integration Requirements Coverage Report" in markdown
    assert "external_api_asks_1c_by_inn" in markdown
    assert "Внешний API спрашивает контрагента" in markdown


async def test_integration_coverage_not_found(client):
    response = await client.get("/api/integration-coverage/nope")
    assert response.status_code == 404


def test_integration_coverage_checker_passes():
    backend_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/check_integration_coverage.py"],
        cwd=backend_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert "Integration coverage check" in result.stdout
