from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.connectors.repository import get_by_name
from app.connectors.registry import registry
from app.core.enums import ConnectorInstanceStatus
from app.sdk.exceptions import ConnectorNotFoundError
from app.sdk.types import ConnectorContext, ConnectorSendResult


class ConnectorManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_target_instance(self, target_system: str | None) -> ConnectorInstance:
        if not target_system:
            raise ConnectorNotFoundError("Target connector is not set")
        instance = await get_by_name(self.session, target_system)
        if instance is None:
            raise ConnectorNotFoundError(f"Target connector {target_system} not found")
        return instance

    async def send_to_target(self, target_system: str | None, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        instance = await self.get_target_instance(target_system)
        if not instance.enabled or instance.status == ConnectorInstanceStatus.DISABLED:
            return ConnectorSendResult(success=False, error_code="CONNECTOR_DISABLED", error_message=f"Target connector {instance.name} is disabled")
        if instance.status == ConnectorInstanceStatus.MAINTENANCE:
            return ConnectorSendResult(success=False, error_code="CONNECTOR_MAINTENANCE", error_message=f"Target connector {instance.name} is in maintenance")
        connector = registry.get(instance.connector_type)
        if context.dry_run:
            result = await connector.dry_run_send(instance.config_json, payload, context)
        else:
            result = await connector.send(instance.config_json, payload, context)
        result.connector_type = instance.connector_type
        result.connector_name = instance.name
        return result
