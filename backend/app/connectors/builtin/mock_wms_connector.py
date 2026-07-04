from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class MockWMSConnector:
    connector_type = "mock_wms"
    display_name = "Mock WMS"
    direction = ConnectorDirection.TARGET

    async def validate_config(self, config: dict) -> ConnectorConfigValidationResult:
        errors: list[str] = []
        if not isinstance(config.get("fail_warehouse_ids", []), list):
            errors.append("fail_warehouse_ids must be a list")
        if not isinstance(config.get("success_warehouse_ids", []), list):
            errors.append("success_warehouse_ids must be a list")
        return ConnectorConfigValidationResult(valid=not errors, errors=errors)

    async def healthcheck(self, config: dict) -> ConnectorHealthResult:
        if config.get("force_down"):
            return ConnectorHealthResult(status=HealthStatus.DOWN, message="Mock WMS forced down", details=config)
        return ConnectorHealthResult(status=HealthStatus.OK, message="Mock WMS accepts requests", details={"mode": "mock"})

    async def send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        document = payload.get("document") if isinstance(payload.get("document"), dict) else {}
        warehouse_id = str(payload.get("warehouse_id") or document.get("warehouse_id") or payload.get("body", {}).get("warehouse_id") or "")
        fail_ids = {str(value) for value in config.get("fail_warehouse_ids", ["005"])}
        if warehouse_id == "HTML":
            html = "<html><body><h1>WMS internal error</h1><p>Picking service unavailable</p></body></html>"
            return ConnectorSendResult(
                success=False,
                status_code=500,
                error_code="WMS_HTTP_500",
                error_message="WMS internal error",
                request_payload={"connector": "mock_wms", "payload": payload},
                response_payload={"status_code": 500, "headers": {"content-type": "text/html"}, "content_type": "text/html", "body": {"text": html}},
                external_error_message="Picking service unavailable",
                external_error_type="http_server_error",
                human_title="WMS returned HTML error page",
                human_summary="Mock WMS HTTP 500: Picking service unavailable",
                developer_message="Original HTML response is preserved in artifacts.",
                hint="Check WMS service availability, logs and retry after the outage is resolved.",
                raw_response_text=html,
                response_headers={"content-type": "text/html"},
                response_content_type="text/html",
                endpoint_url="mock://wms/shipments",
                operation="accept_shipment",
            )
        if warehouse_id == "TEXT":
            text = "WMS validation failed: product SKU-404 is not known"
            return ConnectorSendResult(
                success=False,
                status_code=400,
                error_code="WMS_VALIDATION_ERROR",
                error_message=text,
                request_payload={"connector": "mock_wms", "payload": payload},
                response_payload={"status_code": 400, "headers": {"content-type": "text/plain"}, "content_type": "text/plain", "body": {"text": text}},
                external_error_message=text,
                external_error_type="validation_error",
                human_title="WMS rejected shipment",
                human_summary=text,
                developer_message="Original text/plain response is preserved in artifacts.",
                hint="Check SKU master data and shipment mapping before replay.",
                raw_response_text=text,
                response_headers={"content-type": "text/plain"},
                response_content_type="text/plain",
                endpoint_url="mock://wms/shipments",
                operation="accept_shipment",
            )
        if warehouse_id in fail_ids:
            body = {"success": False, "error_code": "WAREHOUSE_NOT_FOUND", "error_message": f"Warehouse {warehouse_id} not found"}
            return ConnectorSendResult(
                success=False,
                status_code=200,
                error_code="WAREHOUSE_NOT_FOUND",
                error_message=f"Warehouse {warehouse_id} not found",
                request_payload={"connector": "mock_wms", "payload": payload},
                response_payload={"status_code": 200, "headers": {"content-type": "application/json"}, "content_type": "application/json", "body": body},
                external_error_code="WAREHOUSE_NOT_FOUND",
                external_error_message=f"Warehouse {warehouse_id} not found",
                external_error_type="business_error",
                human_title="WMS rejected shipment",
                human_summary=f"Mock WMS says: Warehouse {warehouse_id} not found",
                developer_message="Original WMS JSON business error is preserved in artifacts.",
                hint="Check warehouse master data or route this order to a valid warehouse.",
                raw_response_json=body,
                response_headers={"content-type": "application/json"},
                response_content_type="application/json",
                endpoint_url="mock://wms/shipments",
                operation="accept_shipment",
            )
        order_id = payload.get("target_order_id") or payload.get("order_id") or document.get("external_id") or "unknown"
        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload={"connector": "mock_wms", "payload": payload},
            response_payload={"external_document_id": f"WMS-SHIP-{order_id}", "status": "accepted"},
        )

    async def dry_run_send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload={"connector": "mock_wms", "payload": payload, "dry_run": True},
            response_payload={"dry_run": True, "would_send_to": "Mock WMS"},
        )

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return []
