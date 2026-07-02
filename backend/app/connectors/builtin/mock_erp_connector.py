from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class MockERPConnector:
    connector_type = "mock_erp"
    display_name = "Mock ERP"
    direction = ConnectorDirection.SOURCE

    async def validate_config(self, config: dict) -> ConnectorConfigValidationResult:
        return ConnectorConfigValidationResult(valid=True)

    async def healthcheck(self, config: dict) -> ConnectorHealthResult:
        return ConnectorHealthResult(status=HealthStatus.OK, message="Mock ERP source ready", details={"mode": "mock"})

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return [
            ConnectorReceivedEvent(
                source_system=config.get("source_system", "Mock ERP"),
                target_system=config.get("target_system", "Mock WMS"),
                event_type="SalesOrderCreated",
                entity_type="SalesOrder",
                entity_id="1001",
                correlation_id="mock_erp_1001",
                payload={"order_id": "1001", "warehouse_id": "MAIN", "items": [{"sku": "ABC123", "qty": 5}]},
            ),
            ConnectorReceivedEvent(
                source_system=config.get("source_system", "Mock ERP"),
                target_system=config.get("target_system", "Mock WMS"),
                event_type="SalesOrderCreated",
                entity_type="SalesOrder",
                entity_id="1532",
                correlation_id="mock_erp_1532",
                payload={"order_id": "1532", "warehouse_id": "005", "items": [{"sku": "ABC123", "qty": 5}]},
            ),
        ]

    async def send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        return ConnectorSendResult(success=False, error_code="UNSUPPORTED_OPERATION", error_message="Mock ERP is a source connector")

    async def dry_run_send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        return await self.send(config, payload, context)
