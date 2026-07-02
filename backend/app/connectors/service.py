from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.connectors.repository import get_instance
from app.connectors.registry import registry
from app.sdk.exceptions import ConnectorNotFoundError
from app.connectors.schemas import ConnectorInstanceCreate, ConnectorInstancePatch
from app.core.enums import ConnectorInstanceStatus, HealthComponentType
from app.core.errors import BadRequestError, NotFoundError
from app.health.models import HealthCheck
from app.sdk.types import ConnectorHealthResult


async def create_instance(session: AsyncSession, request: ConnectorInstanceCreate) -> ConnectorInstance:
    try:
        connector = registry.get(request.connector_type)
    except ConnectorNotFoundError as exc:
        raise BadRequestError(str(exc)) from exc
    validation = await connector.validate_config(request.config_json)
    if not validation.valid:
        raise BadRequestError("; ".join(validation.errors))
    instance = ConnectorInstance(
        name=request.name,
        connector_type=request.connector_type,
        direction=request.direction,
        enabled=request.enabled,
        config_json=request.config_json,
        status=ConnectorInstanceStatus.ENABLED if request.enabled else ConnectorInstanceStatus.DISABLED,
    )
    session.add(instance)
    await session.flush()
    return instance


async def patch_instance(session: AsyncSession, connector_id: UUID, request: ConnectorInstancePatch) -> ConnectorInstance:
    instance = await get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    data = request.model_dump(exclude_unset=True)
    if "config_json" in data:
        try:
            connector = registry.get(instance.connector_type)
        except ConnectorNotFoundError as exc:
            raise BadRequestError(str(exc)) from exc
        validation = await connector.validate_config(data["config_json"])
        if not validation.valid:
            raise BadRequestError("; ".join(validation.errors))
    for key, value in data.items():
        setattr(instance, key, value)
    if "enabled" in data:
        instance.status = ConnectorInstanceStatus.ENABLED if instance.enabled else ConnectorInstanceStatus.DISABLED
    await session.flush()
    return instance


async def test_config(connector_type: str, config: dict) -> dict:
    try:
        connector = registry.get(connector_type)
    except ConnectorNotFoundError as exc:
        raise BadRequestError(str(exc)) from exc
    result = await connector.validate_config(config)
    return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings}


async def healthcheck_instance(session: AsyncSession, connector_id: UUID) -> ConnectorHealthResult:
    instance = await get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    connector = registry.get(instance.connector_type)
    result = await connector.healthcheck(instance.config_json)
    instance.last_health_status = result.status
    instance.last_health_message = result.message
    instance.last_health_at = result.checked_at
    if instance.enabled:
        instance.status = ConnectorInstanceStatus.ENABLED
    session.add(
        HealthCheck(
            component_type=HealthComponentType.CONNECTOR,
            component_name=instance.name,
            status=result.status,
            details_json=result.details,
            checked_at=result.checked_at,
        )
    )
    await session.flush()
    return result


async def set_enabled(session: AsyncSession, connector_id: UUID, enabled: bool) -> ConnectorInstance:
    instance = await get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    instance.enabled = enabled
    instance.status = ConnectorInstanceStatus.ENABLED if enabled else ConnectorInstanceStatus.DISABLED
    await session.flush()
    return instance
