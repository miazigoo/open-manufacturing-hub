from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, PollingCursorType
from app.mappings.service import install_all_presets
from app.onec_scenarios.presets import SALES_ORDER_DEMO
from app.polling.models import PollingJob
from app.workflows.models import Workflow

DEMO_ONEC_CONNECTOR_NAME = "Demo 1C ERP"
DEMO_MOCK_WMS_NAME = "Mock WMS"
DEMO_WORKFLOW_NAME = "1C SalesOrder to WMS ShipmentOrder"
DEMO_POLLING_JOB_NAME = "Poll 1C sales orders"

DEMO_ONEC_CONFIG: dict[str, Any] = {
    "base_url": "https://onec.example.local/odata/standard.odata",
    "http_service_base_url": "https://onec.example.local/hs/omh",
    "auth": {"type": "none"},
    "timeout_seconds": 10,
    "verify_ssl": True,
    "odata": {
        "enabled": True,
        "default_page_size": 100,
        "max_pages": 10,
    },
    "http_services": {
        "enabled": True,
        "services": [
            {"name": "health", "method": "GET", "path": "/health"},
            {"name": "echo", "method": "POST", "path": "/echo"},
        ],
    },
}


async def install_sales_order_demo(session: AsyncSession) -> dict[str, Any]:
    source = await _ensure_connector(
        session,
        name=DEMO_ONEC_CONNECTOR_NAME,
        connector_type="onec",
        direction=ConnectorDirection.BIDIRECTIONAL,
        config_json=DEMO_ONEC_CONFIG,
    )
    target = await _ensure_connector(
        session,
        name=DEMO_MOCK_WMS_NAME,
        connector_type="mock_wms",
        direction=ConnectorDirection.TARGET,
        config_json={"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
    )
    mappings = await install_all_presets(session)
    workflow = await _ensure_workflow(session)
    polling_job = await _ensure_polling_job(session, source.id, target.name)
    return {
        "scenario": SALES_ORDER_DEMO["key"],
        "source_connector_id": source.id,
        "target_connector_id": target.id,
        "workflow_id": workflow.id,
        "polling_job_id": polling_job.id,
        "mappings": [mapping.name for mapping in mappings],
        "notes": [
            "Demo 1C connector uses placeholder HTTPS URLs; set real base_url and credentials before live polling.",
            "Polling run-once creates integration events and executes the installed workflow immediately.",
        ],
    }


async def _ensure_connector(
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


async def _ensure_workflow(session: AsyncSession) -> Workflow:
    payload = {
        "description": "Production-grade demo: 1C OData sales order polling to Mock WMS shipment order creation.",
        "event_type": SALES_ORDER_DEMO["event_type"],
        "source_system": DEMO_ONEC_CONNECTOR_NAME,
        "target_system": DEMO_MOCK_WMS_NAME,
        "entity_type": SALES_ORDER_DEMO["entity_type"],
        "version": 1,
        "enabled": True,
        "steps_json": [
            {"name": "receive"},
            {"name": "maintenance_guard"},
            {"name": "map_payload", "config": {"mapping": "onec_sales_order_to_canonical_sales_order"}},
            {"name": "map_payload", "config": {"mapping": "canonical_sales_order_to_mock_wms_shipment_order"}},
            {"name": "call_connector"},
            {"name": "handle_response"},
            {"name": "create_incident", "on": "failure"},
            {"name": "send_notifications", "on": "failure"},
        ],
        "validation_json": {},
        "source_mapping_version_id": None,
        "target_mapping_version_id": None,
    }
    existing = (await session.execute(select(Workflow).where(Workflow.name == DEMO_WORKFLOW_NAME))).scalar_one_or_none()
    if existing is not None:
        for key, value in payload.items():
            setattr(existing, key, value)
        await session.flush()
        return existing
    workflow = Workflow(name=DEMO_WORKFLOW_NAME, **payload)
    session.add(workflow)
    await session.flush()
    return workflow


async def _ensure_polling_job(session: AsyncSession, source_connector_id, target_system: str) -> PollingJob:
    payload = {
        "enabled": True,
        "source_connector_id": source_connector_id,
        "target_system": target_system,
        "resource": SALES_ORDER_DEMO["source_resource"],
        "query_json": {"$select": "Ref_Key,Number,Date,Партнер_Key,Склад_Key,Комментарий,Товары", "$orderby": "Date asc"},
        "event_type": SALES_ORDER_DEMO["event_type"],
        "entity_type": SALES_ORDER_DEMO["entity_type"],
        "entity_id_field": "Ref_Key",
        "correlation_id_field": "Number",
        "updated_at_field": "Date",
        "cursor_type": PollingCursorType.UPDATED_AT,
        "interval_seconds": 300,
    }
    existing = (await session.execute(select(PollingJob).where(PollingJob.name == DEMO_POLLING_JOB_NAME))).scalar_one_or_none()
    if existing is not None:
        for key, value in payload.items():
            setattr(existing, key, value)
        await session.flush()
        return existing
    job = PollingJob(name=DEMO_POLLING_JOB_NAME, **payload)
    session.add(job)
    await session.flush()
    return job
