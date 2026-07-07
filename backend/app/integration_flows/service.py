from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.config import get_settings
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, IntegrationFlowTargetType
from app.core.errors import BadRequestError, NotFoundError
from app.flow_builder.compiler import FlowCompiler
from app.flow_builder.validator import validate_builder
from app.integration_bus import repository as bus_repository
from app.integration_bus import service as bus_service
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute
from app.core.enums import EndpointProcessingMode
from app.integration_flows import repository
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.presets import MARKING_POOL_PRESET, OPERATION_KEY_ODATA_CHAIN_PRESET, TWO_ODATA_TO_ENDPOINT_PRESET
from app.integration_flows.schemas import FlowTestRequest, IntegrationFlowCreate, IntegrationFlowPatch
from app.matchers.engine import evaluate_matcher_group
from app.matchers.validators import validate_matcher_group
from app.operation_templates.models import OperationTemplate
from app.packages import repository as package_repository
from app.secrets.redaction import is_secret_ref
from app.test_console.models import SavedTestCase
from app.workflows.models import Workflow


def endpoint_url(slug: str) -> str:
    return f"/api/bus/in/{slug}"


def public_endpoint_url(slug: str) -> str:
    return f"{_public_api_base_url()}{endpoint_url(slug)}"


def curl_example(slug: str, input_mode: str, sample: dict[str, Any] | str | None, token: str | None = None) -> str:
    content_type = "application/xml" if input_mode == "xml" else "text/plain" if input_mode == "raw_text" else "application/json"
    body = sample if isinstance(sample, str) else json.dumps(sample or {"pool_type": "DNP", "codes": ["..."]}, ensure_ascii=False)
    headers = f'-H "Content-Type: {content_type}"'
    if token:
        headers += f' \\\n  -H "X-OMH-Token: {token}"'
    return f"curl -X POST {public_endpoint_url(slug)} \\\n  {headers} \\\n  -d '{body}'"


def onec_http_example(slug: str, input_mode: str, token: str | None = None) -> str:
    content_type = "application/xml" if input_mode == "xml" else "text/plain" if input_mode == "raw_text" else "application/json"
    token_line = f'\nЗапрос.Заголовки.Вставить("X-OMH-Token", "{token}");' if token else ""
    parsed = urlparse(_public_api_base_url())
    host = parsed.hostname or "omh-server"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = f"{parsed.path.rstrip('/') if parsed.path else ''}{endpoint_url(slug)}"
    return f'HTTPСоединение = Новый HTTPСоединение("{host}", {port});\nЗапрос = Новый HTTPЗапрос("{path}");\nЗапрос.Заголовки.Вставить("Content-Type", "{content_type}");{token_line}\nЗапрос.УстановитьТелоИзСтроки(ТелоЗапроса);\nОтвет = HTTPСоединение.ОтправитьДляОбработки(Запрос);'


def _public_api_base_url() -> str:
    settings = get_settings()
    return (settings.public_api_base_url or settings.public_base_url or "http://localhost:8000").rstrip("/")


async def list_flows(session: AsyncSession) -> list[dict[str, Any]]:
    return [await _read_flow(flow, session) for flow in await repository.list_flows(session)]


async def get_flow_or_404(session: AsyncSession, flow_id: UUID) -> IntegrationFlow:
    flow = await repository.get_flow(session, flow_id)
    if flow is None:
        raise NotFoundError("Integration flow not found")
    return flow


async def create_flow(session: AsyncSession, request: IntegrationFlowCreate) -> IntegrationFlow:
    validate_matcher_group(request.matcher_group_json)
    if request.builder_json:
        validation = validate_builder(request.builder_json)
        if not validation["valid"]:
            raise BadRequestError(json.dumps(validation, ensure_ascii=False))
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
        compiled_workflow_id=workflow.id if request.builder_json else None,
        target_connector_id=connector.id if connector else None,
        operation_template_id=operation.id,
        matcher_group_json=request.matcher_group_json,
        action_json=request.action_json,
        response_config_json=request.response_config_json,
        builder_json=request.builder_json,
        last_validation_json=validate_builder(request.builder_json) if request.builder_json else None,
        compiled_at=datetime.now(timezone.utc) if request.builder_json else None,
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
    if "builder_json" in data and data["builder_json"] is not None:
        data["last_validation_json"] = validate_builder(data["builder_json"])
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
        builder_json=flow.builder_json,
        test_payload_json=flow.test_payload_json,
        test_payload_text=flow.test_payload_text,
    )
    return await create_flow(session, request)


async def export_flow(session: AsyncSession, flow_id: UUID) -> dict[str, Any]:
    flow = await get_flow_or_404(session, flow_id)
    return {"flow": await _read_flow(flow, session), "config": {"matcher_group": flow.matcher_group_json, "action": flow.action_json, "response": flow.response_config_json, "builder": flow.builder_json}}


async def save_builder(session: AsyncSession, flow_id: UUID, builder_json: dict[str, Any]) -> IntegrationFlow:
    flow = await get_flow_or_404(session, flow_id)
    flow.builder_json = builder_json
    flow.last_validation_json = validate_builder(builder_json)
    await session.flush()
    return flow


async def compile_flow(session: AsyncSession, flow_id: UUID) -> dict[str, Any]:
    flow = await get_flow_or_404(session, flow_id)
    if not flow.builder_json:
        raise BadRequestError("FLOW_BUILDER_NOT_CONFIGURED")
    compiled = FlowCompiler().compile(flow.builder_json)
    flow.last_validation_json = compiled["validation"]
    if not compiled["valid"]:
        await session.flush()
        return {"valid": False, "workflow_id": None, "steps_json": [], "validation": compiled["validation"]}
    workflow = await _upsert_compiled_workflow(session, flow, compiled["steps_json"])
    flow.workflow_id = workflow.id
    flow.compiled_workflow_id = workflow.id
    flow.compiled_at = datetime.now(timezone.utc)
    if flow.endpoint_id:
        endpoint = await session.get(IntegrationEndpoint, flow.endpoint_id)
        if endpoint:
            endpoint.workflow_id = workflow.id
    if flow.route_id:
        route = await session.get(IntegrationRoute, flow.route_id)
        if route:
            route.workflow_id = workflow.id
    await session.flush()
    return {"valid": True, "workflow_id": str(workflow.id), "steps_json": compiled["steps_json"], "validation": compiled["validation"]}


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


async def install_two_odata_to_endpoint_preset(session: AsyncSession) -> IntegrationFlow:
    await _ensure_mock_onec_erp(session)
    existing = await repository.get_by_slug(session, TWO_ODATA_TO_ENDPOINT_PRESET["slug"])
    if existing:
        return existing
    return await create_flow(session, IntegrationFlowCreate(**TWO_ODATA_TO_ENDPOINT_PRESET))


async def install_operation_key_odata_chain_preset(session: AsyncSession) -> IntegrationFlow:
    existing = await repository.get_by_slug(session, OPERATION_KEY_ODATA_CHAIN_PRESET["slug"])
    if existing:
        await patch_flow(
            session,
            existing.id,
            IntegrationFlowPatch(
                description=OPERATION_KEY_ODATA_CHAIN_PRESET["description"],
                matcher_group_json=OPERATION_KEY_ODATA_CHAIN_PRESET["matcher_group_json"],
                action_json=OPERATION_KEY_ODATA_CHAIN_PRESET["action_json"],
                response_config_json=OPERATION_KEY_ODATA_CHAIN_PRESET["response_config_json"],
                builder_json=OPERATION_KEY_ODATA_CHAIN_PRESET["builder_json"],
                test_payload_json=OPERATION_KEY_ODATA_CHAIN_PRESET["test_payload_json"],
            ),
        )
        await compile_flow(session, existing.id)
        return existing
    return await create_flow(session, IntegrationFlowCreate(**OPERATION_KEY_ODATA_CHAIN_PRESET))


async def install_dnp_pull_codes_preset(session: AsyncSession) -> IntegrationFlow:
    return await install_operation_key_odata_chain_preset(session)


async def _upsert_endpoint(session: AsyncSession, request: IntegrationFlowCreate, route_id: UUID, workflow_id: UUID, operation_id: UUID) -> IntegrationEndpoint:
    endpoint_name = f"Flow {request.name} Endpoint"
    endpoint = await bus_repository.get_endpoint_by_slug(session, request.slug) or await bus_repository.get_endpoint_by_name(session, endpoint_name)
    data = {
        "name": endpoint_name,
        "slug": request.slug,
        "enabled": request.enabled,
        "description": request.description,
        "input_mode": request.endpoint.input_mode,
        "response_mode": request.endpoint.response_mode,
        "processing_mode": EndpointProcessingMode.SYNC_THEN_ASYNC_FALLBACK.value if request.endpoint.response_mode in {"sync_response", "proxy_response"} else EndpointProcessingMode.ASYNC_QUEUE.value,
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
    compiled = FlowCompiler().compile(request.builder_json) if request.builder_json else None
    action_type = request.action_json.get("type")
    if compiled and compiled["valid"]:
        steps = compiled["steps_json"]
    elif action_type == "call_printer":
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


async def _upsert_compiled_workflow(session: AsyncSession, flow: IntegrationFlow, steps_json: list[dict[str, Any]]) -> Workflow:
    name = f"Flow {flow.name} Workflow"
    result = await session.execute(select(Workflow).where(Workflow.name == name))
    workflow = result.scalar_one_or_none()
    data = {
        "name": name,
        "description": flow.description,
        "event_type": f"Flow.{flow.slug}",
        "source_system": flow.source_type.value,
        "target_system": flow.action_json.get("target_connector") or flow.target_type.value,
        "entity_type": flow.slug,
        "enabled": flow.enabled,
        "steps_json": steps_json,
        "validation_json": {"required_fields": []},
    }
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
        config_json = {"base_url": action.get("base_url") or "http://replace-me.local", "path": action.get("path")}
        if connector_type == "rest":
            config_json["url"] = action.get("url") or f"{str(action.get('base_url') or 'http://replace-me.local').rstrip('/')}{action.get('path') or ''}"
            config_json["method"] = action.get("method") or "POST"
        if action.get("mock_response_json") is not None:
            config_json["mock_response_json"] = action["mock_response_json"]
        connector = ConnectorInstance(name=name, connector_type=connector_type, direction=ConnectorDirection.TARGET, enabled=True, status=ConnectorInstanceStatus.ENABLED, config_json=config_json)
        session.add(connector)
        await session.flush()
    elif action.get("mock_response_json") is not None:
        connector.config_json = {**(connector.config_json or {}), "mock_response_json": action["mock_response_json"]}
    return connector


async def _ensure_mock_onec_erp(session: AsyncSession) -> ConnectorInstance:
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == "1C ERP"))
    connector = result.scalar_one_or_none()
    mock_config = {
        "base_url": "http://mock-1c.local/odata/standard.odata",
        "http_service_base_url": "http://mock-1c.local",
        "auth": {"type": "none"},
        "odata": {"enabled": True, "default_page_size": 100, "max_pages": 1},
        "mock_odata": {
            "Catalog_Контрагенты": [{"Ref_Key": "contractor-uuid-001", "Description": "ООО Производство", "ИНН": "1234567890"}],
            "Catalog_Номенклатура": [{"Ref_Key": "product-uuid-abc-123", "Description": "Product ABC-123", "Артикул": "ABC-123"}],
        },
    }
    if connector is None:
        connector = ConnectorInstance(name="1C ERP", connector_type="onec", direction=ConnectorDirection.TARGET, enabled=True, status=ConnectorInstanceStatus.ENABLED, config_json=mock_config)
        session.add(connector)
    else:
        connector.config_json = {**mock_config, **(connector.config_json or {}), "mock_odata": mock_config["mock_odata"]}
        connector.connector_type = "onec"
        connector.enabled = True
        connector.status = ConnectorInstanceStatus.ENABLED
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


async def _read_flow(flow: IntegrationFlow, session: AsyncSession | None = None) -> dict[str, Any]:
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
        "compiled_workflow_id": flow.compiled_workflow_id,
        "mapping_id": flow.mapping_id,
        "target_connector_id": flow.target_connector_id,
        "operation_template_id": flow.operation_template_id,
        "matcher_group_json": flow.matcher_group_json,
        "action_json": flow.action_json,
        "response_config_json": flow.response_config_json,
        "builder_json": flow.builder_json,
        "last_validation_json": flow.last_validation_json,
        "compiled_at": flow.compiled_at,
        "test_payload_json": flow.test_payload_json,
        "test_payload_text": flow.test_payload_text,
        "endpoint_url": endpoint_url(flow.slug),
        "curl_example": _curl_for_flow(flow),
        "onec_http_example": _onec_for_flow(flow),
        "package_warnings": await _package_warnings(flow, session) if session else [],
        "created_at": flow.created_at,
        "updated_at": flow.updated_at,
    }


async def _package_warnings(flow: IntegrationFlow, session: AsyncSession) -> list[dict[str, Any]]:
    required = _required_package_ids(flow)
    warnings: list[dict[str, Any]] = []
    for package_id in sorted(required):
        package = await package_repository.get_installed(session, package_id)
        if package is None:
            warnings.append({"package_id": package_id, "code": "PACKAGE_NOT_INSTALLED", "message": f"Flow references capability from {package_id}, but package is not installed."})
        elif not package.enabled:
            warnings.append({"package_id": package_id, "code": "PACKAGE_DISABLED", "message": f"Flow references capability from {package_id}, but package is disabled."})
    return warnings


def _required_package_ids(flow: IntegrationFlow) -> set[str]:
    text = " ".join(
        [
            getattr(flow.source_type, "value", str(flow.source_type)),
            getattr(flow.target_type, "value", str(flow.target_type)),
            json.dumps(flow.action_json or {}, ensure_ascii=False),
            json.dumps(flow.builder_json or {}, ensure_ascii=False),
            flow.slug or "",
            flow.name or "",
        ]
    ).lower()
    required: set[str] = set()
    if any(marker in text for marker in ("onec", "1c", "odata", "xml")):
        required.add("omh-package-onec")
    if any(marker in text for marker in ("printer", "print", "zpl")):
        required.add("omh-package-printer")
    return required


def _curl_for_flow(flow: IntegrationFlow, endpoint: IntegrationEndpoint | None = None) -> str:
    input_mode = endpoint.input_mode if endpoint else "json"
    token = None
    if endpoint and endpoint.auth_mode == "static_token":
        token = _safe_auth_token_preview(endpoint.auth_config_json or {})
    return curl_example(flow.slug, input_mode, flow.test_payload_text or flow.test_payload_json, token)


def _onec_for_flow(flow: IntegrationFlow, endpoint: IntegrationEndpoint | None = None) -> str:
    input_mode = endpoint.input_mode if endpoint else "json"
    token = None
    if endpoint and endpoint.auth_mode == "static_token":
        token = _safe_auth_token_preview(endpoint.auth_config_json or {})
    return onec_http_example(flow.slug, input_mode, token)


def _safe_auth_token_preview(auth_config: dict[str, Any]) -> str:
    token = auth_config.get("token")
    if is_secret_ref(token):
        return f"<secret:{token['$secret']}>"
    return "..."
