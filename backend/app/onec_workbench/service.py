from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.odata import read_odata
from app.core.enums import IntegrationMessageDirection, IntegrationMessageStatus, RunMode
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import IntegrationEvent
from app.execution.engine import ExecutionEngine
from app.onec_workbench.lookup import extract_fields, render_filter_template
from app.onec_workbench import repository
from app.onec_workbench.models import IntegrationMessage
from app.onec_workbench.schemas import ODataLookupTestRequest, XmlInboundJsonRequest
from app.operation_templates.service import install_presets as install_operation_template_presets
from app.workflows.models import Workflow


def xml_metadata_from_headers(headers) -> dict[str, str | None]:
    return {
        "source_system": headers.get("x-omh-source-system") or "1C XML",
        "target_system": headers.get("x-omh-target-system"),
        "message_type": headers.get("x-omh-message-type") or "XML_FILE",
        "correlation_id": headers.get("x-omh-correlation-id"),
        "external_id": headers.get("x-omh-external-id"),
        "document_type": headers.get("x-omh-document-type"),
        "document_number": headers.get("x-omh-document-number"),
    }


async def receive_xml(session: AsyncSession, request: XmlInboundJsonRequest) -> tuple[IntegrationMessage, IntegrationEvent]:
    message = IntegrationMessage(
        direction=IntegrationMessageDirection.INBOUND,
        source_system=request.source_system,
        target_system=request.target_system,
        message_type=request.message_type,
        document_type=request.document_type or request.message_type,
        document_number=request.document_number,
        correlation_id=request.correlation_id,
        external_id=request.external_id,
        status=IntegrationMessageStatus.RECEIVED,
        route_key=f"{request.source_system}:{request.message_type}",
        content_type="application/xml",
        payload_text=request.xml,
        payload_json=None,
        payload_sha256=_sha256_text(request.xml),
        payload_size_bytes=len(request.xml.encode("utf-8")),
    )
    session.add(message)
    await session.flush()

    event = IntegrationEvent(
        correlation_id=request.correlation_id,
        source_system=request.source_system,
        target_system=request.target_system,
        event_type="OneCXmlReceived",
        entity_type=request.message_type,
        entity_id=str(message.id),
    )
    session.add(event)
    await session.flush()
    message.event_id = event.id

    workflow = await ensure_xml_bridge_workflow(session)
    payload = {
        "message_id": str(message.id),
        "source_system": request.source_system,
        "target_system": request.target_system,
        "message_type": request.message_type,
        "correlation_id": request.correlation_id,
        "xml": request.xml,
        "payload_sha256": message.payload_sha256,
        "payload_size_bytes": message.payload_size_bytes,
    }
    await ExecutionEngine(session).execute_event(event.id, mode=RunMode.NORMAL, initial_payload=payload, workflow_id=workflow.id)
    await session.refresh(event)
    await session.refresh(message)
    return message, event


async def get_message_or_404(session: AsyncSession, message_id: UUID) -> IntegrationMessage:
    message = await repository.get_message(session, message_id)
    if message is None:
        raise NotFoundError("Integration message not found")
    return message


async def replay_message(session: AsyncSession, message_id: UUID):
    message = await get_message_or_404(session, message_id)
    if message.event_id is None:
        raise BadRequestError("Integration message is not linked to an event")
    return await ExecutionEngine(session).execute_event(message.event_id, mode=RunMode.REPLAY)


async def test_odata_lookup(session: AsyncSession, request: ODataLookupTestRequest) -> dict[str, Any]:
    connector = await connector_repository.get_by_name(session, request.connector_name)
    if connector is None:
        raise NotFoundError("Connector not found")
    if connector.connector_type != "onec":
        raise BadRequestError("Connector must be connector_type=onec")
    query = dict(request.params)
    query["$filter"] = render_filter_template(request.filter_template, request.input)
    result = await read_odata(connector.config_json, request.resource, query)
    if not result.success:
        raise BadRequestError(result.error_message or result.error_code or "OData lookup failed")
    item = result.items[0] if result.items else None
    if item is None and request.required:
        raise BadRequestError("ODATA_LOOKUP_NOT_FOUND")
    extracted = extract_fields(item or {}, request.extract)
    return {"request": result.request_payload or {}, "response": result.response_payload or {}, "extracted": extracted}


async def ensure_xml_bridge_workflow(session: AsyncSession) -> Workflow:
    return await _upsert_workflow(
        session,
        name="1C XML Inbound Workbench",
        description="Default safe XML inbound workflow for 1C Workbench.",
        event_type="OneCXmlReceived",
        source_system=None,
        target_system=None,
        entity_type=None,
        steps_json=[
            {"name": "receive"},
            {"name": "save_integration_message"},
            {"name": "parse_xml"},
            {"name": "route_by_rule", "config": {"default": {}}},
            {"name": "handle_response"},
            {"name": "create_incident", "on": "failure"},
        ],
        validation_json={"required_fields": []},
    )


async def install_inn_lookup_demo(session: AsyncSession) -> Workflow:
    return await _upsert_workflow(
        session,
        name="1C INN to UUID Enrichment Demo",
        description="Resolve contractor UUID through 1C OData and inject it into payload.",
        event_type="OneCInnLookupRequested",
        source_system=None,
        target_system="1C ERP",
        entity_type=None,
        steps_json=[
            {"name": "receive"},
            {"name": "odata_lookup", "config": {"connector": "1C ERP", "resource": "Catalog_Контрагенты", "filter_template": "ИНН eq '{inn}'", "input": {"inn": "payload.inn"}, "params": {"$top": 1}, "extract": {"contractor_uuid": "Ref_Key", "contractor_name": "Description"}, "inject": {"payload.contractor_uuid": "contractor_uuid"}, "required": True}},
            {"name": "map_payload"},
            {"name": "call_connector"},
            {"name": "handle_response"},
            {"name": "create_incident", "on": "failure"},
        ],
        validation_json={"required_fields": []},
    )


async def install_print_pipeline(session: AsyncSession) -> Workflow:
    return await _upsert_workflow(
        session,
        name="1C Print Request Pipeline",
        description="Execute a 1C print request through the printing service as a workflow step.",
        event_type="OneCPrintRequest",
        source_system=None,
        target_system=None,
        entity_type=None,
        steps_json=[
            {"name": "receive"},
            {"name": "route_by_rule", "config": {"rules": [{"when": {"message_type": "PRINT_ZPL"}, "operation": "print_zpl"}], "default": {"operation": "print_zpl"}}},
            {"name": "call_print_operation"},
            {"name": "handle_response"},
            {"name": "create_incident", "on": "failure"},
        ],
        validation_json={"required_fields": []},
    )


async def install_all_presets(session: AsyncSession) -> list[Workflow]:
    await install_operation_template_presets(session)
    return [await ensure_xml_bridge_workflow(session), await install_inn_lookup_demo(session), await install_print_pipeline(session)]


async def _upsert_workflow(session: AsyncSession, *, name: str, description: str, event_type: str, source_system: str | None, target_system: str | None, entity_type: str | None, steps_json: list[dict[str, Any]], validation_json: dict[str, Any]) -> Workflow:
    result = await session.execute(select(Workflow).where(Workflow.name == name))
    workflow = result.scalar_one_or_none()
    if workflow is None:
        workflow = Workflow(name=name, description=description, event_type=event_type, source_system=source_system, target_system=target_system, entity_type=entity_type, version=1, enabled=True, steps_json=steps_json, validation_json=validation_json)
        session.add(workflow)
    else:
        workflow.description = description
        workflow.event_type = event_type
        workflow.source_system = source_system
        workflow.target_system = target_system
        workflow.entity_type = entity_type
        workflow.enabled = True
        workflow.steps_json = steps_json
        workflow.validation_json = validation_json
    await session.flush()
    return workflow


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
