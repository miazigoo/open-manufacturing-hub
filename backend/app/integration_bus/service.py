from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.connectors.models import ConnectorInstance
from app.connectors.builtin.onec.odata import read_odata
from app.core.config import get_settings
from app.core.enums import EndpointProcessingMode, IntegrationMessageDirection, IntegrationMessageStatus
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import EventRun, IntegrationEvent
from app.enterprise_runtime import service as runtime_service
from app.integration_bus import repository
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute, ODataLookupTemplate
from app.integration_bus.response_modes import ACCEPTED_EVENT, ACCEPTED_MESSAGE, PROXY_RESPONSE, SYNC_RESPONSE
from app.integration_bus.schemas import (
    AUTH_MODES,
    INPUT_MODES,
    PROCESSING_MODES,
    RESPONSE_MODES,
    IntegrationEndpointCreate,
    IntegrationEndpointPatch,
    IntegrationRouteCreate,
    IntegrationRoutePatch,
    ODataLookupTemplateCreate,
    ODataLookupTemplatePatch,
)
from app.mappings.engine import get_path
from app.matchers.engine import evaluate_matcher_group
from app.onec_workbench.lookup import extract_fields, render_filter_template
from app.onec_workbench.models import IntegrationMessage
from app.secrets import service as secrets_service
from app.secrets.service import SecretResolver
from app.workflows.models import Workflow

XML_FULL_ARTIFACT_MAX_BYTES = 1024 * 1024
XML_MAX_BYTES = 10 * 1024 * 1024


async def create_endpoint(session: AsyncSession, request: IntegrationEndpointCreate) -> IntegrationEndpoint:
    _validate_endpoint_modes(request.input_mode, request.response_mode, request.auth_mode)
    _validate_processing_mode(request.processing_mode)
    await _validate_auth_config(session, request.auth_mode, request.auth_config_json)
    data = request.model_dump()
    if data.get("processing_mode") == EndpointProcessingMode.ASYNC_QUEUE and request.response_mode in {SYNC_RESPONSE, PROXY_RESPONSE}:
        data["processing_mode"] = EndpointProcessingMode.SYNC_THEN_ASYNC_FALLBACK.value
    endpoint = IntegrationEndpoint(**data)
    session.add(endpoint)
    await session.flush()
    return endpoint


async def patch_endpoint(session: AsyncSession, endpoint_id: UUID, request: IntegrationEndpointPatch) -> IntegrationEndpoint:
    endpoint = await get_endpoint_or_404(session, endpoint_id)
    data = request.model_dump(exclude_unset=True)
    _validate_endpoint_modes(data.get("input_mode", endpoint.input_mode), data.get("response_mode", endpoint.response_mode), data.get("auth_mode", endpoint.auth_mode))
    _validate_processing_mode(data.get("processing_mode", endpoint.processing_mode))
    await _validate_auth_config(session, data.get("auth_mode", endpoint.auth_mode), data.get("auth_config_json", endpoint.auth_config_json))
    for key, value in data.items():
        setattr(endpoint, key, value)
    await session.flush()
    return endpoint


async def get_endpoint_or_404(session: AsyncSession, endpoint_id: UUID) -> IntegrationEndpoint:
    endpoint = await repository.get_endpoint(session, endpoint_id)
    if endpoint is None:
        raise NotFoundError("Integration endpoint not found")
    return endpoint


async def create_route(session: AsyncSession, request: IntegrationRouteCreate) -> IntegrationRoute:
    route = IntegrationRoute(**request.model_dump())
    session.add(route)
    await session.flush()
    return route


async def patch_route(session: AsyncSession, route_id: UUID, request: IntegrationRoutePatch) -> IntegrationRoute:
    route = await get_route_or_404(session, route_id)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(route, key, value)
    await session.flush()
    return route


async def get_route_or_404(session: AsyncSession, route_id: UUID) -> IntegrationRoute:
    route = await repository.get_route(session, route_id)
    if route is None:
        raise NotFoundError("Integration route not found")
    return route


async def create_lookup_template(session: AsyncSession, request: ODataLookupTemplateCreate) -> ODataLookupTemplate:
    await _ensure_onec_connector(session, request.connector_id)
    template = ODataLookupTemplate(**request.model_dump())
    session.add(template)
    await session.flush()
    return template


async def patch_lookup_template(session: AsyncSession, template_id: UUID, request: ODataLookupTemplatePatch) -> ODataLookupTemplate:
    template = await get_lookup_template_or_404(session, template_id)
    data = request.model_dump(exclude_unset=True)
    if data.get("connector_id") is not None:
        await _ensure_onec_connector(session, data["connector_id"])
    for key, value in data.items():
        setattr(template, key, value)
    await session.flush()
    return template


async def get_lookup_template_or_404(session: AsyncSession, template_id: UUID) -> ODataLookupTemplate:
    template = await repository.get_lookup_template(session, template_id)
    if template is None:
        raise NotFoundError("OData lookup template not found")
    return template


async def test_lookup_template(session: AsyncSession, template_id: UUID, input_values: dict[str, Any]) -> dict[str, Any]:
    template = await get_lookup_template_or_404(session, template_id)
    connector = await _ensure_onec_connector(session, template.connector_id)
    query = {"$filter": render_filter_template(template.filter_template, input_values)}
    connector_config = await SecretResolver(session).resolve_config(connector.config_json)
    result = await read_odata(connector_config, template.resource, query)
    if not result.success:
        raise BadRequestError(result.error_message or result.error_code or "ODATA_LOOKUP_FAILED")
    if not result.items and template.required:
        raise BadRequestError("ODATA_LOOKUP_NOT_FOUND")
    return {"request": result.request_payload or {}, "response": result.response_payload or {}, "extracted": extract_fields(result.items[0] if result.items else {}, template.extract_json)}


async def dispatch(session: AsyncSession, slug: str, request: Request) -> dict[str, Any]:
    endpoint = await repository.get_endpoint_by_slug(session, slug)
    if endpoint is None:
        raise NotFoundError("Integration endpoint not found")
    if not endpoint.enabled:
        raise BadRequestError("BUS_ENDPOINT_DISABLED")
    await _check_auth(session, endpoint, request)

    parsed = await _parse_request(endpoint, request)
    parsed["_headers"] = {str(key).lower(): value for key, value in request.headers.items()}
    parsed["_query"] = dict(request.query_params)
    return await dispatch_parsed(session, endpoint, parsed)


async def dispatch_parsed(session: AsyncSession, endpoint: IntegrationEndpoint, parsed: dict[str, Any]) -> dict[str, Any]:
    if not endpoint.enabled:
        raise BadRequestError("BUS_ENDPOINT_DISABLED")
    route, route_trace = await select_route_with_trace(session, endpoint, parsed)
    target_system = await _target_system(session, endpoint, route)
    workflow_id = endpoint.workflow_id or (route.workflow_id if route else None)
    if (endpoint.route_id and route is None) or (route is None and workflow_id is None):
        raise BadRequestError("BUS_ROUTE_NOT_FOUND")
    if workflow_id is not None and await session.get(Workflow, workflow_id) is None:
        raise BadRequestError("BUS_WORKFLOW_NOT_FOUND")

    message = await _store_message_if_needed(session, endpoint, parsed, route, target_system)
    event = IntegrationEvent(
        correlation_id=parsed.get("correlation_id"),
        source_system=str(parsed.get("source_system") or endpoint.default_source_system or "Integration Bus"),
        target_system=target_system,
        event_type=str(parsed.get("event_type") or endpoint.default_event_type),
        entity_type=str(parsed.get("message_type") or endpoint.default_entity_type or endpoint.input_mode),
        entity_id=str(message.id) if message else _entity_id(parsed),
    )
    session.add(event)
    await session.flush()
    if message is not None:
        message.event_id = event.id

    payload = dict(parsed["payload"] if isinstance(parsed.get("payload"), dict) else parsed)
    if parsed.get("_headers"):
        payload["_headers"] = parsed["_headers"]
    if parsed.get("_query"):
        payload["_query"] = parsed["_query"]
    payload.update(
        {
            "_bus": {"endpoint_id": str(endpoint.id), "endpoint_slug": endpoint.slug, "route_id": str(route.id) if route else None},
            "source_system": event.source_system,
            "target_system": target_system,
            "message_type": event.entity_type,
        }
    )
    if message is not None:
        payload["message_id"] = str(message.id)
        if message.payload_text and "xml" not in payload:
            payload["xml"] = message.payload_text
    if route and route.operation:
        payload.setdefault("_omh", {})
        if isinstance(payload["_omh"], dict):
            payload["_omh"]["operation"] = route.operation
    if route_trace:
        payload["_route_match_trace"] = route_trace

    queue_item = await runtime_service.ensure_queue_for_event(
        session,
        event_id=event.id,
        message_id=message.id if message else None,
        business_object=event.entity_type,
        operation=(route.operation if route and route.operation else _operation_key(parsed) or endpoint.default_event_type),
        workflow_id=workflow_id,
        payload=payload,
        endpoint_id=endpoint.id,
        route_id=route.id if route else None,
        source_system=event.source_system,
        target_system=target_system,
        business_key=event.entity_id or event.correlation_id,
    )
    processing_mode = endpoint.processing_mode.value if hasattr(endpoint.processing_mode, "value") else str(endpoint.processing_mode)
    if endpoint.response_mode in {ACCEPTED_EVENT, ACCEPTED_MESSAGE} or processing_mode == EndpointProcessingMode.ASYNC_QUEUE.value:
        return _format_response(endpoint, event, message, route, queue_item, None, None)

    runtime_service.lock_item(queue_item, "inline-dispatch")
    try:
        await asyncio.wait_for(runtime_service.process_locked_item(session, queue_item), timeout=get_settings().sync_processing_timeout_seconds)
    except TimeoutError:
        await session.flush()
        return {
            "success": False,
            "accepted": True,
            "status": "processing",
            "queue_item_id": queue_item.id,
            "event_id": event.id,
            "message_id": message.id if message else None,
            "message": "Processing continues asynchronously",
            "timeline_url": f"/events/{event.id}",
        }
    await _update_message_after_run(session, message, "success" if queue_item.status.value == "completed" else "failed")
    run = await session.get(EventRun, queue_item.run_id) if queue_item.run_id else None
    response, external_error = await _response_context_from_run(session, run) if run else (None, None)
    return _format_response(endpoint, event, message, route, queue_item, response, external_error)


async def select_route(session: AsyncSession, endpoint: IntegrationEndpoint, parsed: dict[str, Any]) -> IntegrationRoute | None:
    route, _ = await select_route_with_trace(session, endpoint, parsed)
    return route


async def select_route_with_trace(session: AsyncSession, endpoint: IntegrationEndpoint, parsed: dict[str, Any]) -> tuple[IntegrationRoute | None, dict[str, Any]]:
    if endpoint.route_id is not None:
        route = await repository.get_route(session, endpoint.route_id)
        if route is None or not route.enabled:
            return None, {"selected_route": None, "matched": False, "checked_routes": []}
        matcher_group = _matcher_group(route.condition_json)
        matcher_result = evaluate_matcher_group(matcher_group, _matcher_context(parsed))
        selected = route if matcher_result["matched"] else None
        return selected, {
            "selected_route": selected.name if selected else None,
            "matched": selected is not None,
            "checked_routes": [{"route": route.name, "matched": matcher_result["matched"], "score": 100 if matcher_result["matched"] else 0, "trace": matcher_result["trace"]}],
        }
    source_system = parsed.get("source_system") or endpoint.default_source_system
    target_system = parsed.get("target_system") or endpoint.default_target_system
    event_type = parsed.get("event_type") or endpoint.default_event_type
    message_type = parsed.get("message_type") or endpoint.default_entity_type
    operation = _operation_key(parsed)
    result = await session.execute(
        select(IntegrationRoute)
        .where(IntegrationRoute.enabled.is_(True))
        .where(or_(IntegrationRoute.source_system == source_system, IntegrationRoute.source_system.is_(None)))
        .where(or_(IntegrationRoute.target_system == target_system, IntegrationRoute.target_system.is_(None)))
        .where(or_(IntegrationRoute.event_type == event_type, IntegrationRoute.event_type.is_(None)))
        .where(or_(IntegrationRoute.message_type == message_type, IntegrationRoute.message_type.is_(None)))
        .where(or_(IntegrationRoute.operation == operation, IntegrationRoute.operation.is_(None)))
    )
    routes = list(result.scalars().all())
    checked = []
    matched_routes: list[tuple[IntegrationRoute, int]] = []
    context = _matcher_context(parsed)
    for route in routes:
        matcher_group = _matcher_group(route.condition_json)
        matcher_result = evaluate_matcher_group(matcher_group, context)
        score = _route_score(route, source_system, target_system, event_type, message_type, operation) + (50 if matcher_result["matched"] and matcher_group else 0)
        checked.append({"route": route.name, "matched": matcher_result["matched"], "score": score, "trace": matcher_result["trace"]})
        if matcher_result["matched"]:
            matched_routes.append((route, score))
    if not matched_routes:
        return None, {"selected_route": None, "matched": False, "checked_routes": checked}
    matched_routes.sort(key=lambda item: (item[0].priority, -item[1]))
    selected = matched_routes[0][0]
    return selected, {"selected_route": selected.name, "matched": True, "checked_routes": checked}


async def install_presets(session: AsyncSession) -> tuple[list[IntegrationEndpoint], list[IntegrationRoute], list[ODataLookupTemplate]]:
    json_workflow = await _upsert_workflow(
        session,
        "Bus 1C JSON to Website API",
        "Bus preset for 1C JSON/XML requests forwarded to a target API connector.",
        "BusRequestReceived",
        ["receive", "route_by_rule", "map_payload", "call_connector", "handle_response", "create_incident"],
    )
    lookup_workflow = await _upsert_workflow(
        session,
        "Bus Website Contractor Lookup",
        "Bus preset for synchronous INN to contractor UUID lookup.",
        "ContractorLookupRequested",
        ["receive", {"name": "odata_lookup", "config": {"template": "Find contractor by INN", "input": {"inn": "payload.inn"}, "inject": {"payload.contractor_uuid": "contractor_uuid"}}}, "handle_response"],
    )
    xml_workflow = await _upsert_workflow(
        session,
        "Bus UPD XML Raw Bridge",
        "Bus preset for raw UPD XML forwarding.",
        "OneCXmlReceived",
        ["receive", "save_integration_message", "route_by_rule", "call_connector", "handle_response", "create_incident"],
    )
    print_workflow = await _upsert_workflow(
        session,
        "Bus 1C Print ZPL",
        "Bus preset for 1C print requests.",
        "OneCPrintRequest",
        ["receive", "route_by_rule", "call_print_operation", "handle_response", "create_incident"],
    )
    endpoints = [
        await _upsert_endpoint(session, "1C to Website API", "onec-to-site", "json", ACCEPTED_EVENT, "BusRequestReceived", json_workflow.id, "1C ERP", "Website API", EndpointProcessingMode.ASYNC_QUEUE.value),
        await _upsert_endpoint(session, "Site Contractor Lookup", "site-contractor-lookup", "json", SYNC_RESPONSE, "ContractorLookupRequested", lookup_workflow.id, "Website", "1C ERP", EndpointProcessingMode.SYNC_INLINE.value),
        await _upsert_endpoint(session, "UPD XML Raw Bridge", "upd-xml", "xml", ACCEPTED_MESSAGE, "OneCXmlReceived", xml_workflow.id, "1C UPD", "1C ERP", EndpointProcessingMode.ASYNC_QUEUE.value),
        await _upsert_endpoint(session, "1C Print ZPL", "print-zpl", "json", ACCEPTED_EVENT, "OneCPrintRequest", print_workflow.id, "1C ERP", None, EndpointProcessingMode.ASYNC_QUEUE.value),
    ]
    routes = [
        await _upsert_route(session, "Default 1C to Website API", "BusRequestReceived", "Website API", json_workflow.id, 50),
        await _upsert_route(session, "Default Contractor Lookup", "ContractorLookupRequested", "1C ERP", lookup_workflow.id, 40),
        await _upsert_route(session, "Default UPD XML Raw Bridge", "OneCXmlReceived", "1C ERP", xml_workflow.id, 30, message_type="UPD", operation="receive_upd_xml"),
        await _upsert_route(session, "Default 1C Print ZPL", "OneCPrintRequest", None, print_workflow.id, 20, message_type="PRINT_ZPL", operation="print_zpl"),
    ]
    lookups = await repository.list_lookup_templates(session)
    return endpoints, routes, lookups


def _validate_endpoint_modes(input_mode: str, response_mode: str, auth_mode: str) -> None:
    if input_mode not in INPUT_MODES:
        raise BadRequestError(f"Unsupported input_mode: {input_mode}")
    if response_mode not in RESPONSE_MODES:
        raise BadRequestError(f"Unsupported response_mode: {response_mode}")
    if auth_mode not in AUTH_MODES:
        raise BadRequestError(f"Unsupported auth_mode: {auth_mode}")


def _validate_processing_mode(processing_mode: Any) -> None:
    value = processing_mode.value if hasattr(processing_mode, "value") else str(processing_mode)
    if value not in PROCESSING_MODES:
        raise BadRequestError(f"Unsupported processing_mode: {value}")


async def _validate_auth_config(session: AsyncSession, auth_mode: str, config: dict[str, Any]) -> None:
    validation = await secrets_service.validate_config(session, config or {})
    if not validation.valid:
        errors = [f"{item.path}: {item.status} {item.name}" for item in validation.references if item.status != "ok"]
        raise BadRequestError("; ".join(errors) or "SECRET_REFERENCE_INVALID")
    if auth_mode == "static_token":
        resolved = await SecretResolver(session).resolve_config(config or {})
        if not str(resolved.get("token") or ""):
            raise BadRequestError("Static token auth requires auth_config_json.token")


async def _check_auth(session: AsyncSession, endpoint: IntegrationEndpoint, request: Request) -> None:
    if endpoint.auth_mode == "none":
        return
    if endpoint.auth_mode == "static_token":
        auth_config = await SecretResolver(session).resolve_config(endpoint.auth_config_json or {})
        expected = str(auth_config.get("token") or "")
        supplied = request.headers.get("x-omh-token") or request.headers.get("authorization", "").removeprefix("Bearer ")
        if not expected or not hmac.compare_digest(supplied, expected):
            raise BadRequestError("BUS_AUTH_FAILED")


async def _parse_request(endpoint: IntegrationEndpoint, request: Request) -> dict[str, Any]:
    if endpoint.input_mode == "json":
        body = await request.json()
        return body if isinstance(body, dict) else {"payload": body}
    if endpoint.input_mode == "xml":
        xml = (await request.body()).decode("utf-8")
        size = len(xml.encode("utf-8"))
        if size > XML_MAX_BYTES:
            raise BadRequestError("XML_TOO_LARGE")
        return {"xml": xml, "payload": {"xml": xml}, "message_type": endpoint.default_entity_type or "XML", "payload_sha256": _sha256_text(xml), "payload_size_bytes": size}
    if endpoint.input_mode == "raw_text":
        text = (await request.body()).decode("utf-8")
        return {"text": text, "payload": {"text": text}}
    if endpoint.input_mode == "form":
        form = await request.form()
        return {key: value for key, value in form.items()}
    if endpoint.input_mode == "multipart_file":
        form = await request.form()
        upload = form.get("file")
        content = await upload.read() if hasattr(upload, "read") else b""
        text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
        return {"file_name": getattr(upload, "filename", None), "text": text, "payload": {"text": text}}
    raise BadRequestError(f"Unsupported input_mode: {endpoint.input_mode}")


async def _store_message_if_needed(session: AsyncSession, endpoint: IntegrationEndpoint, parsed: dict[str, Any], route: IntegrationRoute | None, target_system: str | None) -> IntegrationMessage | None:
    text = parsed.get("xml") if endpoint.input_mode == "xml" else parsed.get("text") if endpoint.input_mode in {"raw_text", "multipart_file"} else None
    if not isinstance(text, str):
        return None
    size = len(text.encode("utf-8"))
    preview = text[:4000]
    message = IntegrationMessage(
        direction=IntegrationMessageDirection.INBOUND,
        source_system=str(parsed.get("source_system") or endpoint.default_source_system or "Integration Bus"),
        target_system=target_system,
        message_type=str(parsed.get("message_type") or endpoint.default_entity_type or endpoint.input_mode),
        document_type=str(parsed.get("document_type") or endpoint.default_entity_type or endpoint.input_mode),
        document_number=parsed.get("document_number"),
        correlation_id=parsed.get("correlation_id"),
        external_id=parsed.get("external_id"),
        status=IntegrationMessageStatus.RECEIVED,
        route_key=route.name if route else endpoint.slug,
        content_type="application/xml" if endpoint.input_mode == "xml" else "text/plain",
        payload_text=text if size <= XML_FULL_ARTIFACT_MAX_BYTES else preview,
        payload_json={"preview": preview, "full_stored": size <= XML_FULL_ARTIFACT_MAX_BYTES, "forward_mode": "raw_forward" if endpoint.input_mode == "xml" else "raw_text"},
        payload_sha256=_sha256_text(text),
        payload_size_bytes=size,
    )
    session.add(message)
    await session.flush()
    return message


async def _target_system(session: AsyncSession, endpoint: IntegrationEndpoint, route: IntegrationRoute | None) -> str | None:
    if route and route.target_connector_id:
        connector = await session.get(ConnectorInstance, route.target_connector_id)
        if connector is None:
            raise BadRequestError("BUS_TARGET_NOT_FOUND")
        return connector.name
    return (route.target_system if route else None) or endpoint.default_target_system


async def _update_message_after_run(session: AsyncSession, message: IntegrationMessage | None, status: str) -> None:
    if message is None:
        return
    message.status = IntegrationMessageStatus.SENT if status == "success" else IntegrationMessageStatus.FAILED
    await session.flush()


async def _response_context_from_run(session: AsyncSession, run: EventRun) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    result = await session.execute(
        select(Artifact)
        .where(Artifact.run_id == run.id)
        .where(Artifact.artifact_type == "incoming_response")
        .order_by(Artifact.created_at.desc())
    )
    artifacts = list(result.scalars().all())
    artifact = next((item for item in artifacts if item.name == "incoming_response.json"), None)
    artifact = artifact or next((item for item in artifacts if item.name == "return_response.json"), None)
    artifact = artifact or (artifacts[0] if artifacts else None)
    from app.external_errors.models import ExternalErrorRecord

    error_result = await session.execute(
        select(ExternalErrorRecord).where(ExternalErrorRecord.run_id == run.id).order_by(ExternalErrorRecord.created_at.desc()).limit(1)
    )
    external_error = error_result.scalar_one_or_none()
    return artifact.content_json if artifact else None, _external_error_payload(external_error)


def _format_response(
    endpoint: IntegrationEndpoint,
    event: IntegrationEvent,
    message: IntegrationMessage | None,
    route: IntegrationRoute | None,
    queue_item: Any,
    response: dict[str, Any] | None,
    external_error: dict[str, Any] | None,
) -> dict[str, Any]:
    queue_status = queue_item.status.value if hasattr(queue_item.status, "value") else str(queue_item.status)
    base = {"accepted": True, "queue_item_id": queue_item.id, "event_id": event.id, "message_id": message.id if message else None, "status": queue_status, "timeline_url": f"/events/{event.id}", "route_id": route.id if route else None}
    if endpoint.response_mode == ACCEPTED_EVENT:
        return {key: value for key, value in base.items() if key != "message_id" or value is not None}
    if endpoint.response_mode == ACCEPTED_MESSAGE:
        return base
    if event.status.value != "success" and external_error:
        failure = {
            "success": False,
            **base,
            "error_code": external_error.get("external_error_code") or external_error.get("normalized_code"),
            "error_message": external_error.get("external_error_message") or external_error.get("normalized_message"),
            "human_summary": external_error.get("human_summary"),
            "external_error": external_error,
            "response": response,
        }
        return failure
    if endpoint.response_mode == PROXY_RESPONSE:
        if response:
            return {**response, "success": queue_status == "completed", **base, "response": response}
        return {**base, "response": None}
    if endpoint.response_mode == SYNC_RESPONSE:
        if response and "response_body_type" in response and "body" in response:
            response_meta = {key: response.get(key) for key in ("status_code", "response_body_type", "headers") if key in response}
            body = response.get("body")
            if response.get("response_body_type") == "xml" and isinstance(body, dict) and isinstance(body.get("xml"), str):
                body = body["xml"]
            return {"success": event.status.value == "success", **base, "response": body, "body": body, "response_meta": response_meta}
        return {"success": event.status.value == "success", **base, "response": response, "body": response}
    return base


def _external_error_payload(record: Any | None) -> dict[str, Any] | None:
    if record is None:
        return None
    body = record.response_body_json if record.response_body_json is not None else record.response_body_xml or record.response_body_text
    return {
        "id": record.id,
        "system": record.connector_name or record.target_system,
        "normalized_code": record.normalized_code,
        "normalized_message": record.normalized_message,
        "external_error_code": record.external_error_code,
        "external_error_message": record.external_error_message,
        "human_title": record.human_title,
        "human_summary": record.human_summary,
        "hint": record.hint,
        "status_code": record.http_status,
        "content_type": record.response_content_type,
        "body": body,
        "body_preview": record.response_body_preview,
        "body_sha256": record.response_body_sha256,
    }


def _route_score(route: IntegrationRoute, source_system: Any, target_system: Any, event_type: Any, message_type: Any, operation: Any) -> int:
    return sum([
        8 if route.source_system == source_system and source_system else 0,
        8 if route.target_system == target_system and target_system else 0,
        6 if route.event_type == event_type and event_type else 0,
        4 if route.message_type == message_type and message_type else 0,
        3 if route.operation == operation and operation else 0,
    ])


def _matcher_group(condition_json: dict[str, Any] | None) -> dict[str, Any] | None:
    if not condition_json:
        return None
    if isinstance(condition_json.get("matcher_group"), dict):
        return condition_json["matcher_group"]
    if condition_json.get("mode") and isinstance(condition_json.get("rules"), list):
        return condition_json
    return None


def _matcher_context(parsed: dict[str, Any]) -> dict[str, Any]:
    body = parsed.get("payload") if isinstance(parsed.get("payload"), dict) else parsed if isinstance(parsed, dict) else {}
    return {
        "body": body,
        "text": parsed.get("text") or parsed.get("xml") or str(body),
        "xml": parsed.get("xml"),
        "headers": parsed.get("_headers") or {},
        "query": parsed.get("_query") or {},
    }


def _operation_key(parsed: dict[str, Any]) -> Any:
    omh = parsed.get("_omh")
    if isinstance(omh, dict) and omh.get("operation"):
        return omh.get("operation")
    payload = parsed.get("payload") if isinstance(parsed.get("payload"), dict) else {}
    return parsed.get("operation") or parsed.get("sinc") or payload.get("operation") or payload.get("sinc")


def _entity_id(parsed: dict[str, Any]) -> str | None:
    for key in ("entity_id", "id", "document_number", "external_id"):
        if parsed.get(key) is not None:
            return str(parsed[key])
    payload = parsed.get("payload") if isinstance(parsed.get("payload"), dict) else {}
    for key in ("entity_id", "id", "order_id", "document_number"):
        if payload.get(key) is not None:
            return str(payload[key])
    return None


async def _ensure_onec_connector(session: AsyncSession, connector_id: UUID) -> ConnectorInstance:
    connector = await session.get(ConnectorInstance, connector_id)
    if connector is None:
        raise NotFoundError("Connector not found")
    if connector.connector_type != "onec":
        raise BadRequestError("Connector must be connector_type=onec")
    return connector


async def _upsert_workflow(session: AsyncSession, name: str, description: str, event_type: str, steps: list[Any]) -> Workflow:
    result = await session.execute(select(Workflow).where(Workflow.name == name))
    workflow = result.scalar_one_or_none()
    steps_json = [{"name": item} if isinstance(item, str) else item for item in steps]
    if workflow is None:
        workflow = Workflow(name=name, description=description, event_type=event_type, enabled=True, steps_json=steps_json, validation_json={"required_fields": []})
        session.add(workflow)
    else:
        workflow.description = description
        workflow.event_type = event_type
        workflow.enabled = True
        workflow.steps_json = steps_json
        workflow.validation_json = {"required_fields": []}
    await session.flush()
    return workflow


async def _upsert_endpoint(session: AsyncSession, name: str, slug: str, input_mode: str, response_mode: str, event_type: str, workflow_id: UUID, source: str | None, target: str | None, processing_mode: str = "async_queue") -> IntegrationEndpoint:
    endpoint = await repository.get_endpoint_by_slug(session, slug)
    data = {"name": name, "slug": slug, "input_mode": input_mode, "response_mode": response_mode, "processing_mode": processing_mode, "default_event_type": event_type, "workflow_id": workflow_id, "default_source_system": source, "default_target_system": target, "enabled": True, "auth_mode": "none", "auth_config_json": {}}
    if endpoint is None:
        endpoint = IntegrationEndpoint(**data)
        session.add(endpoint)
    else:
        for key, value in data.items():
            setattr(endpoint, key, value)
    await session.flush()
    return endpoint


async def _upsert_route(session: AsyncSession, name: str, event_type: str, target: str | None, workflow_id: UUID, priority: int, *, message_type: str | None = None, operation: str | None = None) -> IntegrationRoute:
    result = await session.execute(select(IntegrationRoute).where(IntegrationRoute.name == name))
    route = result.scalar_one_or_none()
    data = {"name": name, "event_type": event_type, "target_system": target, "workflow_id": workflow_id, "priority": priority, "message_type": message_type, "operation": operation, "enabled": True, "condition_json": {}}
    if route is None:
        route = IntegrationRoute(**data)
        session.add(route)
    else:
        for key, value in data.items():
            setattr(route, key, value)
    await session.flush()
    return route


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
