from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository, service
from app.connectors.registry import registry
from app.connectors.schemas import ConnectorConfigValidationRead, ConnectorHealthRead, ConnectorInstanceCreate, ConnectorInstancePatch, ConnectorInstanceRead, ConnectorTypeRead, WebhookEventResponse
from app.core.database import get_session
from app.core.errors import BadRequestError, NotFoundError
from app.events.schemas import EventCreate
from app.events.service import create_event
from app.sdk.types import ConnectorContext

router = APIRouter(tags=["connectors"])


@router.get("/api/connectors/types", response_model=list[ConnectorTypeRead])
async def connector_types():
    return registry.list()


@router.get("/api/connectors", response_model=list[ConnectorInstanceRead])
async def list_connectors(session: AsyncSession = Depends(get_session)):
    return await repository.list_instances(session)


@router.post("/api/connectors", response_model=ConnectorInstanceRead)
async def create_connector(request: ConnectorInstanceCreate, session: AsyncSession = Depends(get_session)):
    instance = await service.create_instance(session, request)
    await session.commit()
    return instance


@router.get("/api/connectors/{connector_id}", response_model=ConnectorInstanceRead)
async def get_connector(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    instance = await repository.get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    return instance


@router.patch("/api/connectors/{connector_id}", response_model=ConnectorInstanceRead)
async def patch_connector(connector_id: UUID, request: ConnectorInstancePatch, session: AsyncSession = Depends(get_session)):
    instance = await service.patch_instance(session, connector_id, request)
    await session.commit()
    return instance


@router.delete("/api/connectors/{connector_id}", status_code=204)
async def delete_connector(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    instance = await repository.get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    await session.delete(instance)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/connectors/{connector_id}/test-config", response_model=ConnectorConfigValidationRead)
async def test_connector_config(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    instance = await repository.get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    return await service.test_config(instance.connector_type, instance.config_json)


@router.post("/api/connectors/{connector_id}/healthcheck", response_model=ConnectorHealthRead)
async def healthcheck_connector(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.healthcheck_instance(session, connector_id)
    await session.commit()
    return result


@router.post("/api/connectors/{connector_id}/enable", response_model=ConnectorInstanceRead)
async def enable_connector(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    instance = await service.set_enabled(session, connector_id, True)
    await session.commit()
    return instance


@router.post("/api/connectors/{connector_id}/disable", response_model=ConnectorInstanceRead)
async def disable_connector(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    instance = await service.set_enabled(session, connector_id, False)
    await session.commit()
    return instance


@router.post("/api/connectors/{connector_id}/mock-erp/generate-events")
async def generate_mock_erp_events(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    instance = await repository.get_instance(session, connector_id)
    if instance is None:
        raise NotFoundError("Connector instance not found")
    if instance.connector_type != "mock_erp":
        raise BadRequestError("Connector is not mock_erp")
    connector = registry.get(instance.connector_type)
    received = await connector.receive(instance.config_json, ConnectorContext(metadata={"source": "manual"}))
    events = []
    for item in received:
        event = await create_event(
            session,
            EventCreate(
                correlation_id=item.correlation_id,
                source_system=item.source_system,
                target_system=item.target_system,
                event_type=item.event_type,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                payload=item.payload,
            ),
        )
        events.append({"event_id": event.id, "status": event.status})
    await session.commit()
    return {"created": events}


@router.post("/api/webhooks/{connector_name}", response_model=WebhookEventResponse)
async def receive_webhook(connector_name: str, body: dict, session: AsyncSession = Depends(get_session)):
    instance = await repository.get_by_name(session, connector_name)
    if instance is None:
        raise NotFoundError("Webhook connector not found")
    if instance.connector_type != "webhook":
        raise BadRequestError("Connector is not webhook")
    connector = registry.get(instance.connector_type)
    received = await connector.receive(instance.config_json, ConnectorContext(metadata={"body": body}))
    if not received:
        raise BadRequestError("Webhook did not produce an event")
    item = received[0]
    event = await create_event(
        session,
        EventCreate(
            correlation_id=item.correlation_id,
            source_system=item.source_system,
            target_system=item.target_system,
            event_type=item.event_type,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            payload=item.payload,
        ),
    )
    await session.commit()
    return {"event_id": event.id, "status": event.status}
