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
        warehouse_id = str(payload.get("warehouse_id") or payload.get("body", {}).get("warehouse_id") or "")
        fail_ids = {str(value) for value in config.get("fail_warehouse_ids", ["005"])}
        if warehouse_id in fail_ids:
            return ConnectorSendResult(
                success=False,
                error_code="WAREHOUSE_NOT_FOUND",
                error_message=f"Warehouse {warehouse_id} not found",
                request_payload={"connector": "mock_wms", "payload": payload},
                response_payload={"message": f"Warehouse {warehouse_id} not found"},
            )
        order_id = payload.get("target_order_id") or payload.get("order_id") or "unknown"
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
