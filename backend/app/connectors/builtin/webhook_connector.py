from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class WebhookConnector:
    connector_type = "webhook"
    display_name = "Webhook Receiver"
    direction = ConnectorDirection.SOURCE

    async def validate_config(self, config: dict) -> ConnectorConfigValidationResult:
        return ConnectorConfigValidationResult(valid=True)

    async def healthcheck(self, config: dict) -> ConnectorHealthResult:
        return ConnectorHealthResult(status=HealthStatus.OK, message="Webhook receiver is active", details={"mode": "http"})

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        body = context.metadata.get("body", {})
        payload = body.get("payload", body)
        return [
            ConnectorReceivedEvent(
                source_system=config.get("default_source_system", "External Webhook"),
                target_system=body.get("target_system") or config.get("default_target_system"),
                event_type=body.get(config.get("event_type_field", "event_type"), "WebhookEvent"),
                entity_type=body.get(config.get("entity_type_field", "entity_type")),
                entity_id=body.get(config.get("entity_id_field", "entity_id")),
                payload=payload,
                correlation_id=body.get("correlation_id"),
                metadata={"connector": "webhook"},
            )
        ]

    async def send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        return ConnectorSendResult(success=False, error_code="UNSUPPORTED_OPERATION", error_message="Webhook is a source connector")

    async def dry_run_send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        return await self.send(config, payload, context)
