from app.external_errors.normalizers import external_error_artifact, external_error_payload_from_result
from app.sdk.types import ConnectorSendResult


def test_external_error_normalizer_extracts_json_business_error():
    result = ConnectorSendResult(
        success=False,
        status_code=200,
        error_code="ORDER_NOT_FOUND",
        error_message="Заказ 404 не найден в 1С",
        request_payload={"method": "POST", "url": "https://onec/hs/omh/shipment-facts", "operation": "update_shipment_status"},
        response_payload={
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "content_type": "application/json",
            "body": {"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Заказ 404 не найден в 1С"},
        },
        raw_response_json={"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Заказ 404 не найден в 1С"},
        response_content_type="application/json",
    )

    payload = external_error_payload_from_result(result, source_system="WMS", target_system="1C ERP", connector_type="onec", connector_name="1C ERP")

    assert payload["normalized_code"] == "ORDER_NOT_FOUND"
    assert payload["external_error_code"] == "ORDER_NOT_FOUND"
    assert payload["external_error_message"] == "Заказ 404 не найден в 1С"
    assert payload["response_body_json"]["success"] is False
    assert payload["response_body_sha256"]
    artifact = external_error_artifact(payload)
    assert artifact["external"]["body"]["error_message"] == "Заказ 404 не найден в 1С"


def test_external_error_normalizer_preserves_xml_and_html():
    xml_result = ConnectorSendResult(
        success=False,
        status_code=500,
        error_code="ONEC_HTTP_SERVICE_ERROR",
        error_message="1C HTTP service returned 500",
        raw_response_xml="<Fault><faultstring>Внутренняя ошибка 1С</faultstring></Fault>",
        response_content_type="application/xml",
    )
    xml_payload = external_error_payload_from_result(xml_result, connector_type="onec", connector_name="1C ERP")
    assert xml_payload["external_error_message"] == "Внутренняя ошибка 1С"
    assert xml_payload["response_body_xml"].startswith("<Fault>")

    html_result = ConnectorSendResult(
        success=False,
        status_code=500,
        error_code="WMS_HTTP_500",
        error_message="WMS internal error",
        raw_response_text="<html><body><h1>WMS down</h1><p>Picking service unavailable</p></body></html>",
        response_content_type="text/html",
    )
    html_payload = external_error_payload_from_result(html_result, connector_type="mock_wms", connector_name="Mock WMS")
    assert "Picking service unavailable" in html_payload["response_body_preview"]
    assert "<html>" not in html_payload["response_body_preview"]
    assert html_payload["response_body_text"].startswith("<html>")


async def test_failed_connector_creates_external_error_timeline_journal_and_incident(client, failed_payload):
    created = await client.post("/api/events", json=failed_payload)
    assert created.status_code == 200
    event = created.json()
    assert event["status"] == "failed"

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    failed_step = next(step for step in timeline["runs"][0]["steps"] if step["step_name"] == "call_connector")
    assert failed_step["external_error"] is not None
    assert failed_step["external_error"]["external_error_message"] == "Warehouse 005 not found"
    assert failed_step["human_title"] == "WMS rejected shipment"
    assert any(artifact["artifact_type"] == "external_error" for artifact in failed_step["artifacts"])

    journal = (await client.get("/api/events/journal")).json()
    row = next(item for item in journal if item["id"] == event["id"])
    assert row["human_title"] == "WMS rejected shipment"
    assert row["last_external_error_message"] == "Warehouse 005 not found"
    assert row["requires_attention"] is True

    incidents = (await client.get("/api/incidents")).json()
    assert incidents
    assert incidents[0]["sample_external_errors"]
    assert incidents[0]["sample_external_errors"][0]["external_error_message"] == "Warehouse 005 not found"


async def test_mock_wms_text_and_html_errors_are_preserved(client, failed_payload):
    for warehouse_id, expected_type in [("TEXT", "text/plain"), ("HTML", "text/html")]:
        payload = dict(failed_payload)
        payload["payload"] = dict(failed_payload["payload"], warehouse_id=warehouse_id)
        created = (await client.post("/api/events", json=payload)).json()
        timeline = (await client.get(f"/api/events/{created['id']}/timeline")).json()
        failed_step = next(step for step in timeline["runs"][0]["steps"] if step["step_name"] == "call_connector")
        external = failed_step["external_error"]
        assert external["response_content_type"] == expected_type
        assert external["response_body_preview"]
        if warehouse_id == "HTML":
            assert "<html>" not in external["response_body_preview"]
