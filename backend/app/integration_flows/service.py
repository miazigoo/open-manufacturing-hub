from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, IntegrationFlowTargetType
from app.core.errors import BadRequestError, NotFoundError
from app.integration_bus import repository as bus_repository
from app.integration_bus import service as bus_service
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute
from app.integration_flows import repository
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.presets import MARKING_POOL_PRESET
from app.integration_flows.schemas import FlowTestRequest, IntegrationFlowCreate, IntegrationFlowPatch
from app.matchers.engine import evaluate_matcher_group
from app.matchers.validators import validate_matcher_group
from app.operation_templates.models import OperationTemplate
from app.test_console.models import SavedTestCase
from app.workflows.models import Workflow


def endpoint_url(slug: str) -> str:
    return f"/api/bus/in/{slug}"


def curl_example(slug: str, input_mode: str, sample: dict[str, Any] | str | None, token: str | None = None) -> str:
    content_type = "application/xml" if input_mode == "xml" else "text/plain" if input_mode == "raw_text" else "application/json"
    body = sample if isinstance(sample, str) else json.dumps(sample or {"pool_type": "DNP", "codes": ["..."]}, ensure_ascii=False)
    headers = f'-H "Content-Type: {content_type}"'
    if token:
        headers += f' \\\n  -H "X-OMH-Token: {token}"'
    return f"curl -X POST http://localhost:8000/api/bus/in/{slug} \\\n  {headers} \\\n  -d '{body}'"


def onec_http_example(slug: str, input_mode: str, token: str | None = None) -> str:
    content_type = "application/xml" if input_mode == "xml" else "text/plain" if input_mode == "raw_text" else "application/json"
    token_line = f'\nЗапрос.Заголовки.Вставить("X-OMH-Token", "{token}");' if token else ""
    return f'HTTPСоединение = Новый HTTPСоединение("omh-server", 8000);\nЗапрос = Новый HTTPЗапрос("/api/bus/in/{slug}");\nЗапрос.Заголовки.Вставить("Content-Type", "{content_type}");{token_line}\nЗапрос.УстановитьТелоИзСтроки(ТелоЗапроса);\nОтвет = HTTPСоединение.ОтправитьДляОбработки(Запрос);'


async def list_flows(session: AsyncSession) -> list[dict[str, Any]]:
    return [await _read_flow(flow) for flow in await repository.list_flows(session)]


async def get_flow_or_404(session: AsyncSession, flow_id: UUID) -> IntegrationFlow:
    flow = await repository.get_flow(session, flow_id)
    if flow is None:
        raise NotFoundError("Integration flow not found")
    return flow


async def create_flow(session: AsyncSession, request: IntegrationFlowCreate) -> IntegrationFlow:
    validate_matcher_group(request.matcher_group_json)
    connector = await _ensure_target_connector(session, request.action_json, request.target_type)
    workflow = await _upsert_workflow(session, request)
    operation = await _upsert_operation_template(session, request, workflow.id)
    route = await _upsert_route(session, request, workflow.id, operation.id, connector.id if connector else None)
    endpoint = await _upsert_endpoint(session, request, route.id, workflow.id, operation.id)
    route.target_connector_id = connector.id if connector else None
    flow = IntegrationFlow(
        name=request.name,
        slug=request.slug,
        description=request.description,
        enabled=request.enabled,
        source_type=request.source_type,
        target_type=request.target_type,
        endpoint_id=endpoint.id,
        route_id=route.id,
        workflow_id=workflow.id,
        target_connector_id=connector.id if connector else None,
        operation_template_id=operation.id,
        matcher_group_json=request.matcher_group_json,
        action_json=request.action_json,
        response_config_json=request.response_config_json,
        test_payload_json=request.test_payload_json,
        test_payload_text=request.test_payload_text,
    )
    session.add(flow)
    await _upsert_test_case(session, flow, endpoint, request)
    await session.flush()
    return flow


async def patch_flow(session: AsyncSession, flow_id: UUID, request: IntegrationFlowPatch) -> IntegrationFlow:
    flow = await get_flow_or_404(session, flow_id)
    data = request.model_dump(exclude_unset=True)
    if "matcher_group_json" in data:
        validate_matcher_group(data["matcher_group_json"])
    for key, value in data.items():
        setattr(flow, key, value)
    if flow.route_id and ("matcher_group_json" in data or "action_json" in data):
        route = await session.get(IntegrationRoute, flow.route_id)
        if route:
            route.condition_json = {"matcher_group": flow.matcher_group_json, "flow_id": str(flow.id)}
            route.operation = str(flow.action_json.get("operation") or flow.action_json.get("type") or "flow_action")
    if flow.endpoint_id and "enabled" in data:
        endpoint = await session.get(IntegrationEndpoint, flow.endpoint_id)
        if endpoint:
            endpoint.enabled = flow.enabled
    await session.flush()
    return flow


async def duplicate_flow(session: AsyncSession, flow_id: UUID) -> IntegrationFlow:
    flow = await get_flow_or_404(session, flow_id)
    request = IntegrationFlowCreate(
        name=f"{flow.name} Copy",
        slug=f"{flow.slug}-copy",
        description=flow.description,
        enabled=False,
        source_type=flow.source_type,
        target_type=flow.target_type,
        matcher_group_json=flow.matcher_group_json,
        action_json=flow.action_json,
        response_config_json=flow.response_config_json,
        test_payload_json=flow.test_payload_json,
        test_payload_text=flow.test_payload_text,
    )
    return await create_flow(session, request)


async def export_flow(session: AsyncSession, flow_id: UUID) -> dict[str, Any]:
    flow = await get_flow_or_404(session, flow_id)
    return {"flow": await _read_flow(flow), "config": {"matcher_group": flow.matcher_group_json, "action": flow.action_json, "response": flow.response_config_json}}


async def test_flow(session: AsyncSession, flow_id: UUID, request: FlowTestRequest) -> dict[str, Any]:
    flow = await get_flow_or_404(session, flow_id)
    endpoint = await session.get(IntegrationEndpoint, flow.endpoint_id) if flow.endpoint_id else None
    if endpoint is None:
        raise BadRequestError("Flow is not linked to an endpoint")
    parsed = _parsed_test_payload(request)
    matcher = evaluate_matcher_group(flow.matcher_group_json, {"body": parsed.get("payload") or parsed, "text": parsed.get("text") or parsed.get("xml") or str(parsed), "xml": parsed.get("xml"), "headers": request.headers_json, "query": {}})
    bus_response = None if request.dry_run else await bus_service.dispatch_parsed(session, endpoint, {**parsed, "_headers": request.headers_json, "_query": {}})
    return {"matcher": matcher, "target_action": flow.action_json, "bus_response": bus_response, "curl_example": _curl_for_flow(flow, endpoint), "onec_http_example": _onec_for_flow(flow, endpoint)}


async def install_marking_pool_preset(session: AsyncSession) -> IntegrationFlow:
    existing = await repository.get_by_slug(session, MARKING_POOL_PRESET["slug"])
    if existing:
        return existing
    return await create_flow(session, IntegrationFlowCreate(**MARKING_POOL_PRESET))


async def _upsert_endpoint(session: AsyncSession, request: IntegrationFlowCreate, route_id: UUID, workflow_id: UUID, operation_id: UUID) -> IntegrationEndpoint:
    endpoint = await bus_repository.get_endpoint_by_slug(session, request.slug)
    data = {
        "name": f"Flow {request.name} Endpoint",
        "slug": request.slug,
        "enabled": request.enabled,
        "description": request.description,
        "input_mode": request.endpoint.input_mode,
        "response_mode": request.endpoint.response_mode,
        "default_source_system": request.source_type.value,
        "default_target_system": request.target_type.value,
        "default_event_type": f"Flow.{request.slug}",
        "default_entity_type": request.action_json.get("business_object") or request.slug,
        "workflow_id": workflow_id,
        "route_id": route_id,
        "operation_template_id": operation_id,
        "auth_mode": request.endpoint.auth_mode,
        "auth_config_json": request.endpoint.auth_config_json,
    }
    if endpoint is None:
        endpoint = IntegrationEndpoint(**data)
        session.add(endpoint)
    else:
        for key, value in data.items():
            setattr(endpoint, key, value)
    await session.flush()
    return endpoint


async def _upsert_route(session: AsyncSession, request: IntegrationFlowCreate, workflow_id: UUID, operation_id: UUID, connector_id: UUID | None) -> IntegrationRoute:
    name = f"Flow {request.name} Route"
    result = await session.execute(select(IntegrationRoute).where(IntegrationRoute.name == name))
    route = result.scalar_one_or_none()
    data = {
        "name": name,
        "enabled": request.enabled,
        "source_system": request.source_type.value,
        "target_system": request.action_json.get("target_connector") or request.target_type.value,
        "event_type": f"Flow.{request.slug}",
        "message_type": request.action_json.get("business_object") or request.slug,
        "operation": request.action_json.get("operation") or request.action_json.get("type") or "flow_action",
        "condition_json": {"matcher_group": request.matcher_group_json, "flow_slug": request.slug},
        "workflow_id": workflow_id,
        "target_connector_id": connector_id,
        "operation_template_id": operation_id,
        "priority": 10,
    }
    if route is None:
        route = IntegrationRoute(**data)
        session.add(route)
    else:
        for key, value in data.items():
            setattr(route, key, value)
    await session.flush()
    return route


async def _upsert_workflow(session: AsyncSession, request: IntegrationFlowCreate) -> Workflow:
    name = f"Flow {request.name} Workflow"
    result = await session.execute(select(Workflow).where(Workflow.name == name))
    workflow = result.scalar_one_or_none()
    action_type = request.action_json.get("type")
    if action_type == "call_printer":
        steps = [{"name": "receive"}, {"name": "route_by_rule"}, {"name": "call_print_operation"}, {"name": "handle_response"}, {"name": "create_incident", "on": "failure"}]
    elif action_type == "call_odata_lookup":
        steps = [{"name": "receive"}, {"name": "odata_lookup", "config": request.action_json}, {"name": "handle_response"}]
    elif action_type == "create_event_only":
        steps = [{"name": "receive"}, {"name": "handle_response"}]
    else:
        steps = [{"name": "receive"}, {"name": "route_by_rule"}, {"name": "call_connector"}, {"name": "handle_response"}, {"name": "create_incident", "on": "failure"}]
    data = {"name": name, "description": request.description, "event_type": f"Flow.{request.slug}", "source_system": request.source_type.value, "target_system": request.action_json.get("target_connector") or request.target_type.value, "entity_type": request.slug, "enabled": request.enabled, "steps_json": steps, "validation_json": {"required_fields": []}}
    if workflow is None:
        workflow = Workflow(version=1, **data)
        session.add(workflow)
    else:
        for key, value in data.items():
            setattr(workflow, key, value)
    await session.flush()
    return workflow


async def _upsert_operation_template(session: AsyncSession, request: IntegrationFlowCreate, workflow_id: UUID) -> OperationTemplate:
    name = f"Flow {request.name} Action"
    result = await session.execute(select(OperationTemplate).where(OperationTemplate.name == name))
    operation = result.scalar_one_or_none()
    data = {"name": name, "operation_code": f"flow_{request.slug}", "system_type": request.target_type.value, "operation": request.action_json.get("operation") or request.action_json.get("type") or "flow_action", "direction": "outbound", "input_mode": request.endpoint.input_mode, "output_mode": request.endpoint.response_mode, "target_connector_type": request.target_type.value, "default_body_mode": request.action_json.get("body_mode"), "default_content_type": "application/xml" if request.endpoint.input_mode == "xml" else "application/json", "description": request.description, "enabled": request.enabled, "request_template_json": request.action_json, "example_request_json": request.test_payload_json, "default_workflow_id": workflow_id}
    if operation is None:
        operation = OperationTemplate(**data)
        session.add(operation)
    else:
        for key, value in data.items():
            setattr(operation, key, value)
    await session.flush()
    return operation


async def _ensure_target_connector(session: AsyncSession, action: dict[str, Any], target_type: IntegrationFlowTargetType) -> ConnectorInstance | None:
    name = action.get("target_connector") or action.get("printer_connector")
    if not name or action.get("type") in {"create_event_only", "return_response", "call_odata_lookup"}:
        return None
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == name))
    connector = result.scalar_one_or_none()
    if connector is None:
        connector_type = "rest" if target_type in {IntegrationFlowTargetType.EXTERNAL_API, IntegrationFlowTargetType.INTERNAL, IntegrationFlowTargetType.WEBSITE} else "zpl_printer" if target_type == IntegrationFlowTargetType.PRINTER else "onec"
        connector = ConnectorInstance(name=name, connector_type=connector_type, direction=ConnectorDirection.TARGET, enabled=True, status=ConnectorInstanceStatus.ENABLED, config_json={"base_url": action.get("base_url") or "http://replace-me.local", "path": action.get("path")})
        session.add(connector)
        await session.flush()
    return connector


async def _upsert_test_case(session: AsyncSession, flow: IntegrationFlow, endpoint: IntegrationEndpoint, request: IntegrationFlowCreate) -> SavedTestCase:
    name = f"Flow {request.name} Test"
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == name))
    test_case = result.scalar_one_or_none()
    data = {"name": name, "description": request.description, "endpoint_id": endpoint.id, "method": "POST", "headers_json": {"Content-Type": "application/xml" if endpoint.input_mode == "xml" else "application/json"}, "body_text": request.test_payload_text, "body_json": request.test_payload_json, "input_mode": endpoint.input_mode, "expected_status": "success"}
    if test_case is None:
        test_case = SavedTestCase(**data)
        session.add(test_case)
    else:
        for key, value in data.items():
            setattr(test_case, key, value)
    await session.flush()
    return test_case


def _parsed_test_payload(request: FlowTestRequest) -> dict[str, Any]:
    if request.input_mode == "json":
        return request.payload_json or {}
    if request.input_mode == "xml":
        xml = request.payload_text or ""
        return {"xml": xml, "payload": {"xml": xml}, "message_type": "XML", "payload_size_bytes": len(xml.encode("utf-8"))}
    text = request.payload_text or ""
    return {"text": text, "payload": {"text": text}}


async def _read_flow(flow: IntegrationFlow) -> dict[str, Any]:
    return {
        "id": flow.id,
        "name": flow.name,
        "slug": flow.slug,
        "description": flow.description,
        "enabled": flow.enabled,
        "source_type": flow.source_type,
        "target_type": flow.target_type,
        "endpoint_id": flow.endpoint_id,
        "route_id": flow.route_id,
        "workflow_id": flow.workflow_id,
        "mapping_id": flow.mapping_id,
        "target_connector_id": flow.target_connector_id,
        "operation_template_id": flow.operation_template_id,
        "matcher_group_json": flow.matcher_group_json,
        "action_json": flow.action_json,
        "response_config_json": flow.response_config_json,
        "test_payload_json": flow.test_payload_json,
        "test_payload_text": flow.test_payload_text,
        "endpoint_url": endpoint_url(flow.slug),
        "curl_example": _curl_for_flow(flow),
        "onec_http_example": _onec_for_flow(flow),
        "created_at": flow.created_at,
        "updated_at": flow.updated_at,
    }


def _curl_for_flow(flow: IntegrationFlow, endpoint: IntegrationEndpoint | None = None) -> str:
    input_mode = endpoint.input_mode if endpoint else "json"
    token = None
    if endpoint and endpoint.auth_mode == "static_token":
        token = str((endpoint.auth_config_json or {}).get("token") or "...")
    return curl_example(flow.slug, input_mode, flow.test_payload_text or flow.test_payload_json, token)


def _onec_for_flow(flow: IntegrationFlow, endpoint: IntegrationEndpoint | None = None) -> str:
    input_mode = endpoint.input_mode if endpoint else "json"
    token = None
    if endpoint and endpoint.auth_mode == "static_token":
        token = str((endpoint.auth_config_json or {}).get("token") or "...")
    return onec_http_example(flow.slug, input_mode, token)
