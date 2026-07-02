from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.core.database import async_session
from app.core.enums import ArtifactType, ConnectorDirection, ConnectorInstanceStatus, HealthComponentType, HealthStatus, NotificationDeliveryStatus, NotificationTriggerType, RunMode
from app.connectors.models import ConnectorInstance
from app.events.models import EventRun, IntegrationEvent
from app.events.schemas import EventCreate
from app.events.service import create_event, edit_replay_artifact
from app.health.models import HealthCheck
from app.health.service import get_or_create_site
from app.maintenance.models import MaintenanceWindow
from app.mappings.models import MappingDefinition, MappingVersion
from app.notifications.models import NotificationDelivery, NotificationRule
from app.onec_scenarios.service import install_bidirectional_demo, install_sales_order_demo
from app.workflows.models import Workflow


async def ensure_connector(
    session: AsyncSession,
    *,
    name: str,
    connector_type: str,
    direction: ConnectorDirection,
    config_json: dict[str, Any],
) -> ConnectorInstance:
    existing = (await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == name))).scalar_one_or_none()
    if existing is not None:
        existing.connector_type = connector_type
        existing.direction = direction
        existing.enabled = True
        existing.status = ConnectorInstanceStatus.ENABLED
        existing.config_json = config_json
        await session.flush()
        return existing
    instance = ConnectorInstance(
        name=name,
        connector_type=connector_type,
        direction=direction,
        enabled=True,
        status=ConnectorInstanceStatus.ENABLED,
        config_json=config_json,
    )
    session.add(instance)
    await session.flush()
    return instance


async def ensure_demo_connectors(session: AsyncSession) -> None:
    await ensure_connector(
        session,
        name="Mock WMS",
        connector_type="mock_wms",
        direction=ConnectorDirection.TARGET,
        config_json={"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
    )
    await ensure_connector(
        session,
        name="Mock WMS Replay Lab",
        connector_type="mock_wms",
        direction=ConnectorDirection.TARGET,
        config_json={"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
    )
    await ensure_connector(
        session,
        name="Mock WMS Archive",
        connector_type="mock_wms",
        direction=ConnectorDirection.TARGET,
        config_json={"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
    )
    await ensure_connector(
        session,
        name="Mock ERP",
        connector_type="mock_erp",
        direction=ConnectorDirection.SOURCE,
        config_json={"source_system": "Mock ERP", "target_system": "Mock WMS"},
    )
    await ensure_connector(
        session,
        name="REST Demo Target",
        connector_type="rest",
        direction=ConnectorDirection.TARGET,
        config_json={"method": "POST", "url": "https://example.com/api/orders", "headers": {}, "timeout_seconds": 10},
    )
    await ensure_connector(
        session,
        name="Webhook Demo Source",
        connector_type="webhook",
        direction=ConnectorDirection.SOURCE,
        config_json={"default_source_system": "External Webhook", "default_target_system": "Mock WMS"},
    )


async def ensure_mapping(
    session: AsyncSession,
    *,
    name: str,
    source_entity: str,
    target_entity: str,
    rules_json: list[dict[str, Any]],
    source_schema_json: dict[str, Any],
    target_schema_json: dict[str, Any],
) -> MappingVersion:
    existing = (await session.execute(select(MappingDefinition).where(MappingDefinition.name == name))).scalar_one_or_none()
    if existing is None:
        existing = MappingDefinition(name=name, source_entity=source_entity, target_entity=target_entity)
        session.add(existing)
        await session.flush()
    version = (
        await session.execute(
            select(MappingVersion).where(MappingVersion.mapping_id == existing.id, MappingVersion.version == 1)
        )
    ).scalar_one_or_none()
    if version is not None:
        return version
    version = MappingVersion(
        mapping_id=existing.id,
        version=1,
        rules_json=rules_json,
        source_schema_json=source_schema_json,
        target_schema_json=target_schema_json,
        notes="Demo baseline",
    )
    session.add(version)
    await session.flush()
    return version


async def ensure_workflow(
    session: AsyncSession,
    *,
    name: str,
    event_type: str,
    source_system: str | None,
    target_system: str | None,
    source_mapping_version_id,
    target_mapping_version_id,
) -> Workflow:
    existing = (await session.execute(select(Workflow).where(Workflow.name == name))).scalar_one_or_none()
    payload = {
        "event_type": event_type,
        "source_system": source_system,
        "target_system": target_system,
        "entity_type": "SalesOrder",
        "version": 1,
        "enabled": True,
        "steps_json": [
            {"name": "receive"},
            {"name": "maintenance_guard"},
            {"name": "normalize"},
            {"name": "validate"},
            {"name": "map_payload"},
            {"name": "call_connector"},
            {"name": "handle_response"},
            {"name": "create_incident", "on": "failure"},
            {"name": "send_notifications", "on": "failure"},
        ],
        "validation_json": {"required_fields": ["id", "warehouse.id", "lines"]},
        "source_mapping_version_id": source_mapping_version_id,
        "target_mapping_version_id": target_mapping_version_id,
    }
    if existing is not None:
        for key, value in payload.items():
            setattr(existing, key, value)
        await session.flush()
        return existing
    workflow = Workflow(name=name, **payload)
    session.add(workflow)
    await session.flush()
    return workflow


async def ensure_demo_workflows(session: AsyncSession) -> None:
    source_version = await ensure_mapping(
        session,
        name="Demo ERP SalesOrder to Canonical",
        source_entity="SalesOrder",
        target_entity="SalesOrder",
        rules_json=[
            {"source": "order_id", "target": "id", "transform": "str"},
            {"source": "warehouse_id", "target": "warehouse.id", "transform": "str"},
            {
                "source": "items",
                "target": "lines",
                "type": "array",
                "items": [
                    {"source": "sku", "target": "sku"},
                    {"source": "qty", "target": "quantity"},
                ],
            },
            {"constant": "SalesOrder", "target": "entity"},
        ],
        source_schema_json={"order_id": "string", "warehouse_id": "string", "items": [{"sku": "string", "qty": "number"}]},
        target_schema_json={"id": "string", "warehouse": {"id": "string"}, "lines": [{"sku": "string", "quantity": "number"}]},
    )
    target_version = await ensure_mapping(
        session,
        name="Demo Canonical SalesOrder to WMS",
        source_entity="SalesOrder",
        target_entity="Shipment",
        rules_json=[
            {"source": "id", "target": "target_order_id"},
            {"source": "warehouse.id", "target": "warehouse_id"},
            {
                "source": "lines",
                "target": "lines",
                "type": "array",
                "items": [
                    {"source": "sku", "target": "sku"},
                    {"source": "quantity", "target": "qty"},
                ],
            },
            {"expression": "concat('SO-', $.id)", "target": "external_ref"},
        ],
        source_schema_json={"id": "string", "warehouse": {"id": "string"}, "lines": [{"sku": "string", "quantity": "number"}]},
        target_schema_json={"target_order_id": "string", "warehouse_id": "string", "lines": [{"sku": "string", "qty": "number"}]},
    )
    await ensure_workflow(
        session,
        name="Demo 1C sales orders to WMS",
        event_type="SalesOrderCreated",
        source_system="1C ERP",
        target_system=None,
        source_mapping_version_id=source_version.id,
        target_mapping_version_id=target_version.id,
    )
    await ensure_workflow(
        session,
        name="Demo Mock ERP sales orders to WMS",
        event_type="SalesOrderCreated",
        source_system="Mock ERP",
        target_system=None,
        source_mapping_version_id=source_version.id,
        target_mapping_version_id=target_version.id,
    )


def sales_order_payload(order_id: str, warehouse_id: str) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "warehouse_id": warehouse_id,
        "items": [
            {"sku": "ABC123", "qty": 5},
            {"sku": "MNT-42", "qty": 2},
        ],
    }


async def get_event_by_correlation(session: AsyncSession, correlation_id: str) -> IntegrationEvent | None:
    result = await session.execute(select(IntegrationEvent).where(IntegrationEvent.correlation_id == correlation_id))
    return result.scalar_one_or_none()


async def ensure_event(
    session: AsyncSession,
    *,
    correlation_id: str,
    entity_id: str,
    warehouse_id: str,
    target_system: str = "Mock WMS",
    source_system: str = "1C ERP",
) -> IntegrationEvent:
    existing = await get_event_by_correlation(session, correlation_id)
    if existing is not None:
        return existing
    return await create_event(
        session,
        EventCreate(
            correlation_id=correlation_id,
            source_system=source_system,
            target_system=target_system,
            event_type="SalesOrderCreated",
            entity_type="SalesOrder",
            entity_id=entity_id,
            payload=sales_order_payload(entity_id, warehouse_id),
        ),
    )


async def ensure_edit_replay_example(session: AsyncSession) -> None:
    event = await ensure_event(
        session,
        correlation_id="demo_edit_replay_1701",
        entity_id="1701",
        warehouse_id="005",
        target_system="Mock WMS Replay Lab",
    )
    result = await session.execute(
        select(EventRun).where(EventRun.event_id == event.id, EventRun.mode == RunMode.EDIT_REPLAY).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return
    artifact = (
        await session.execute(
            select(Artifact)
            .where(Artifact.event_id == event.id, Artifact.artifact_type == ArtifactType.RAW_PAYLOAD.value)
            .order_by(Artifact.created_at.asc())
            .limit(1)
        )
    ).scalar_one()
    edited = dict(artifact.content_json)
    edited["warehouse_id"] = "MAIN"
    await edit_replay_artifact(session, artifact.id, edited, "normalize")


async def ensure_health(session: AsyncSession) -> None:
    site = await get_or_create_site(session, "Main Warehouse", "main-warehouse", "Primary demo warehouse site")
    now = datetime.now(timezone.utc)
    checks = [
        (HealthComponentType.SITE, "internet", HealthStatus.DOWN, {"label": "Internet down"}, site.id),
        (HealthComponentType.SITE, "wms", HealthStatus.WARNING, {"label": "WMS unreachable"}, site.id),
        (HealthComponentType.SITE, "erp", HealthStatus.OK, {"label": "ERP reachable"}, site.id),
        (HealthComponentType.QUEUE, "queue", HealthStatus.WARNING, {"queue_size": 342, "label": "342 waiting"}, site.id),
        (HealthComponentType.CONNECTOR, "1C ERP", HealthStatus.OK, {}, None),
        (HealthComponentType.CONNECTOR, "Mock WMS", HealthStatus.WARNING, {}, None),
        (HealthComponentType.NOTIFICATION_CHANNEL, "SMTP", HealthStatus.DOWN, {}, None),
        (HealthComponentType.NOTIFICATION_CHANNEL, "Webhook", HealthStatus.OK, {}, None),
        (HealthComponentType.QUEUE, "RabbitMQ", HealthStatus.WARNING, {"label": "overloaded"}, None),
    ]
    for component_type, component_name, status, details, site_id in checks:
        session.add(
            HealthCheck(
                component_type=component_type,
                component_name=component_name,
                site_id=site_id,
                status=status,
                details_json=details,
                checked_at=now,
            )
        )
    await session.flush()


async def ensure_notification_rule(session: AsyncSession) -> None:
    existing = (
        await session.execute(select(NotificationRule).where(NotificationRule.name == "Critical WMS errors"))
    ).scalar_one_or_none()
    if existing is None:
        existing = NotificationRule(
            name="Critical WMS errors",
            enabled=True,
            trigger_type=NotificationTriggerType.INCIDENT_CREATED,
            filters_json={"target_system": "Mock WMS", "severity": "error"},
            channels_json=[
                {"type": "email_stub", "to": "dev@example.com"},
                {"type": "webhook", "url": "https://example.com/integration-alert"},
            ],
            cooldown_seconds=600,
        )
        session.add(existing)
        await session.flush()
    delivery_exists = (
        await session.execute(select(NotificationDelivery).where(NotificationDelivery.rule_id == existing.id).limit(1))
    ).scalar_one_or_none()
    if delivery_exists is None:
        session.add(
            NotificationDelivery(
                rule_id=existing.id,
                trigger_type=existing.trigger_type.value,
                target_channel="email_stub",
                target_address="dev@example.com",
                status=NotificationDeliveryStatus.SENT,
                request_payload={"demo": True, "target_system": "Mock WMS", "severity": "error"},
                response_payload={"stub": True},
                sent_at=datetime.now(timezone.utc),
            )
        )
        await session.flush()


async def ensure_maintenance(session: AsyncSession) -> None:
    existing = (
        await session.execute(
            select(MaintenanceWindow).where(
                MaintenanceWindow.component_type == "connector",
                MaintenanceWindow.component_name == "Mock WMS",
                MaintenanceWindow.reason == "WMS update",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    now = datetime.now(timezone.utc)
    session.add(
        MaintenanceWindow(
            component_type="connector",
            component_name="Mock WMS",
            reason="WMS update",
            starts_at=now + timedelta(hours=4),
            ends_at=now + timedelta(hours=6),
            enabled=True,
        )
    )
    await session.flush()


async def ensure_retention_examples(session: AsyncSession) -> None:
    past = datetime.now(timezone.utc) - timedelta(days=1)
    expired = await ensure_event(
        session,
        correlation_id="demo_expired_success_9001",
        entity_id="9001",
        warehouse_id="MAIN",
        target_system="Mock WMS Archive",
    )
    expired.expires_at = past
    expired.pinned = False
    pinned = await ensure_event(
        session,
        correlation_id="demo_pinned_expired_9002",
        entity_id="9002",
        warehouse_id="MAIN",
        target_system="Mock WMS Archive",
    )
    pinned.expires_at = past
    pinned.pinned = True
    artifact = (
        await session.execute(select(Artifact).where(Artifact.event_id == expired.id).limit(1))
    ).scalar_one_or_none()
    if artifact is not None:
        artifact.expires_at = past
    await session.flush()


async def normalize_demo_timestamps(session: AsyncSession) -> None:
    demo_time = datetime.now(timezone.utc) - timedelta(minutes=12)
    events = (
        await session.execute(
            select(IntegrationEvent).where(
                IntegrationEvent.correlation_id.is_not(None),
                IntegrationEvent.correlation_id.like("demo_%"),
            )
        )
    ).scalars().all()
    for event in events:
        event.created_at = demo_time
        event.updated_at = demo_time
    await session.flush()


async def seed_demo(session: AsyncSession) -> dict[str, Any]:
    await ensure_demo_connectors(session)
    await ensure_demo_workflows(session)
    onec_scenario = await install_sales_order_demo(session)
    bidirectional_scenario = await install_bidirectional_demo(session)
    await ensure_event(session, correlation_id="demo_success_1001", entity_id="1001", warehouse_id="MAIN")
    await ensure_event(session, correlation_id="demo_failed_1532", entity_id="1532", warehouse_id="005")
    for index in range(1533, 1537):
        await ensure_event(session, correlation_id=f"demo_grouped_failure_{index}", entity_id=str(index), warehouse_id="005")
    await ensure_edit_replay_example(session)
    await ensure_health(session)
    await ensure_notification_rule(session)
    await ensure_maintenance(session)
    await ensure_retention_examples(session)
    await normalize_demo_timestamps(session)
    return {
        "status": "ok",
        "events": ["1001", "1532", "1533", "1534", "1535", "1536", "1701", "9001", "9002"],
        "health_site": "Main Warehouse",
        "notification_rule": "Critical WMS errors",
        "maintenance": "Mock WMS",
        "onec_scenario": onec_scenario["scenario"],
        "onec_bidirectional_scenario": bidirectional_scenario["scenario"],
    }


async def main() -> None:
    async with async_session() as session:
        result = await seed_demo(session)
        await session.commit()
        print("Demo seed complete")
        for key, value in result.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
