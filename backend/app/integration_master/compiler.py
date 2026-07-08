from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.flow_builder.compiler import FlowCompiler
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master.schemas import (
    FinalActionConfig,
    ForeachODataStepConfig,
    InputDraftRead,
    ODataObjectStepConfig,
    ODataStepConfig,
    PayloadStepConfig,
)

MasterDraft = InputDraftRead


@dataclass(slots=True)
class CompileIssue:
    section: str
    field: str | None
    message: str


@dataclass(slots=True)
class CompiledIntegration:
    endpoint_config: dict[str, Any]
    route_config: dict[str, Any]
    flow_config: dict[str, Any]
    builder_json: dict[str, Any]
    workflow_steps: list[dict[str, Any]]
    saved_test_case: dict[str, Any] | None
    flow_payload: IntegrationFlowCreate
    will_create: dict[str, Any]


def compile_master_draft(
    draft: MasterDraft,
    *,
    enabled: bool = False,
    create_saved_test_case: bool = True,
    comment: str | None = None,
) -> CompiledIntegration:
    """Compile an Integration Master draft into existing Integration Flow primitives.

    This function is intentionally pure: it builds configs only and performs no DB writes.
    """
    final_action = draft.final_action or FinalActionConfig()
    response_mode = _endpoint_response_mode(final_action)
    builder_json = _builder_json(draft, final_action)
    compiled = FlowCompiler().compile(builder_json)
    workflow_steps = compiled.get("steps_json") if compiled.get("valid") else []
    flow_name = f"{draft.name} [{draft.slug}]"
    endpoint_config = {
        "name": f"Flow {flow_name} Endpoint",
        "slug": draft.slug,
        "method": "POST",
        "url": f"/api/bus/in/{draft.slug}",
        "input_mode": draft.input_mode,
        "response_mode": response_mode,
        "enabled": enabled,
    }
    matcher_group = _matcher_group(draft)
    route_config = {
        "name": f"Flow {flow_name} Route",
        "matcher_group_json": matcher_group,
        "matcher": _matcher_human(draft),
        "enabled": enabled,
    }
    source_type = _source_type(draft.source_system)
    target_type = _target_type(final_action)
    action_json = _action_json(draft, final_action, comment)
    response_config_json = {
        "response_mode": response_mode,
        "final_action": final_action.model_dump(mode="json"),
        "business_key": draft.contract.business_key.model_dump(mode="json"),
    }
    test_payload_json, test_payload_text = _test_payload(draft)
    flow_payload = IntegrationFlowCreate(
        name=flow_name,
        slug=draft.slug,
        description=_description(draft, comment),
        enabled=enabled,
        source_type=source_type,
        target_type=target_type,
        endpoint=EndpointBuilderConfig(input_mode=draft.input_mode, response_mode=response_mode, auth_mode="none", auth_config_json={}),
        matcher_group_json=matcher_group,
        action_json=action_json,
        response_config_json=response_config_json,
        builder_json=builder_json,
        test_payload_json=test_payload_json,
        test_payload_text=test_payload_text,
    )
    saved_test_case = None
    if create_saved_test_case:
        saved_test_case = {
            "name": f"Flow {flow_name} Test",
            "input_mode": draft.input_mode,
            "body_json": test_payload_json,
            "body_text": test_payload_text,
        }
    flow_config = {
        "name": flow_name,
        "slug": draft.slug,
        "enabled": enabled,
        "source_type": source_type.value,
        "target_type": target_type.value,
        "steps_count": len(builder_json.get("steps") or []),
    }
    will_create = {
        "integration_endpoint": endpoint_config,
        "integration_route": route_config,
        "integration_flow": flow_config,
        "workflow": {"steps_count": len(workflow_steps), "compiled": bool(workflow_steps)},
        "saved_test_case": saved_test_case,
    }
    return CompiledIntegration(
        endpoint_config=endpoint_config,
        route_config=route_config,
        flow_config=flow_config,
        builder_json=builder_json,
        workflow_steps=workflow_steps,
        saved_test_case=saved_test_case,
        flow_payload=flow_payload,
        will_create=will_create,
    )


def _builder_json(draft: InputDraftRead, final_action: FinalActionConfig) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for step in draft.odata_steps:
        if isinstance(step, ODataStepConfig):
            steps.append(_odata_step(step))
        elif isinstance(step, ODataObjectStepConfig):
            steps.append(_odata_object_step(step))
        elif isinstance(step, ForeachODataStepConfig):
            steps.append(_foreach_step(step))
        elif isinstance(step, PayloadStepConfig):
            steps.append(_payload_step(step))
    steps.extend(_final_action_steps(final_action))
    return {
        "version": 1,
        "source": {
            "generated_by": "integration_master",
            "draft_id": str(draft.id),
            "input_mode": draft.input_mode,
            "sample": draft.contract.sample,
            "operation_key": draft.contract.operation_key.model_dump(mode="json"),
            "business_key": draft.contract.business_key.model_dump(mode="json"),
            "master_steps": [step.model_dump(mode="json") for step in draft.odata_steps],
        },
        "steps": steps,
        "final_action": final_action.model_dump(mode="json"),
    }


def _odata_step(step: ODataStepConfig) -> dict[str, Any]:
    return {
        "id": step.id or f"find_{step.save_as}",
        "type": "odata_query",
        "name": _title(step.id or step.save_as),
        "connection": step.connection_name or str(step.connection_id or ""),
        "resource": step.resource,
        "filter": step.filter,
        "select": step.select,
        "top": step.top,
        "orderby": step.orderby,
        "paginate": step.paginate,
        "save_as": step.save_as,
        "required": step.required,
    }


def _odata_object_step(step: ODataObjectStepConfig) -> dict[str, Any]:
    resource = step.resource_template or _object_resource_template(step)
    return {
        "id": step.id or f"read_{step.save_as}",
        "type": "odata_query",
        "name": _title(step.id or step.save_as),
        "connection": step.connection_name or str(step.connection_id or ""),
        "resource": resource,
        "filter": step.filter,
        "select": step.select,
        "top": step.top,
        "paginate": step.paginate,
        "save_as": step.save_as,
        "required": step.required,
        "source_master_type": "odata_object_query",
        "object_variable": step.object_variable,
        "nested_resource": step.nested_resource,
    }


def _foreach_step(step: ForeachODataStepConfig) -> dict[str, Any]:
    return {
        "id": step.id or f"find_{step.save_as}",
        "type": "foreach",
        "name": _title(step.id or step.save_as),
        "items": step.items,
        "item_as": step.item_as,
        "index_as": "index",
        "save_as": step.save_as,
        "flatten": step.merge == "flatten",
        "continue_on_error": False,
        "limits": step.limits.model_dump(mode="json"),
        "source_master_type": "foreach_odata",
        "step": {
            "type": "odata_query",
            "connection": step.connection_name or str(step.connection_id or ""),
            "resource": step.resource,
            "filter": step.filter,
            "select": step.select,
            "top": step.top,
            "paginate": step.paginate,
            "save_as": step.save_as,
            "required": step.required,
        },
    }


def _payload_step(step: PayloadStepConfig) -> dict[str, Any]:
    return {
        "id": step.id or f"build_{step.save_as}",
        "type": "build_payload",
        "name": _title(step.id or step.save_as),
        "body_type": step.body_type,
        "save_as": step.save_as,
        "json_mode": step.json_mode,
        "template": step.template,
        "fields": [field.model_dump(mode="json") for field in step.fields],
        "dynamic_entries": [entry.model_dump(mode="json") for entry in step.dynamic_entries],
    }


def _final_action_steps(action: FinalActionConfig) -> list[dict[str, Any]]:
    if action.type == "accepted_event":
        return [_return_step(action.return_to_caller, fallback_body=_accepted_body(), status_code=202)]
    if action.type == "return_response":
        return [_return_step(action.return_to_caller, fallback_body="{{target_payload}}")]

    call = {
        "id": "final_action",
        "type": "call_endpoint",
        "name": "Final Action",
        "method": action.method,
        "url": action.url,
        "headers": action.headers,
        "body": _final_action_body(action),
        "timeout_seconds": action.timeout_seconds,
        "body_type": action.body_type,
    }
    if action.type == "send_and_return_response" or action.return_to_caller.type == "proxy_response":
        return [call, _return_step(action.return_to_caller, fallback_body="{{response.body}}")]
    return [call, _return_step(action.return_to_caller, fallback_body={"ok": True})]


def _return_step(return_config: Any, *, fallback_body: Any, status_code: int | None = None) -> dict[str, Any]:
    return_type = str(getattr(return_config, "type", "fixed_success"))
    body = getattr(return_config, "body", None)
    if body in (None, {}, "") and return_type == "accepted_event":
        body = _accepted_body()
    if body in (None, ""):
        body = fallback_body
    response_body_type = "xml" if return_type == "custom_xml" else "raw_text" if return_type == "custom_raw" else "json"
    step = {
        "id": "return_response",
        "type": "return_response",
        "name": "Return Response",
        "status_code": status_code or int(getattr(return_config, "status_code", 200) or 200),
        "headers": getattr(return_config, "headers", {}) or {},
        "response_body_type": response_body_type,
    }
    if response_body_type == "xml":
        step["body_template"] = str(body)
    else:
        step["body"] = body
    return step


def _final_action_body(action: FinalActionConfig) -> Any:
    if action.body_source == "none":
        return ""
    if action.body_source == "custom":
        return action.custom_body if action.custom_body is not None else ""
    return "{{target_payload}}"


def _accepted_body() -> dict[str, Any]:
    return {"accepted": True, "event_id": "{{context.event_id}}", "run_id": "{{context.run_id}}", "timeline_url": "/events/{{context.event_id}}"}


def _object_resource_template(step: ODataObjectStepConfig) -> str:
    key = f"{{{{{step.object_variable}.{step.key_field or 'Ref_Key'}}}}}"
    if step.key_type == "guid":
        key = f"guid'{key}'"
    elif step.key_type == "string":
        key = f"'{key}'"
    return f"{step.base_resource}({key})/{step.nested_resource.strip('/')}"


def _endpoint_response_mode(action: FinalActionConfig) -> str:
    if action.type == "accepted_event" or action.return_to_caller.type == "accepted_event":
        return "accepted_event"
    if action.type == "send_and_return_response" or action.return_to_caller.type == "proxy_response":
        return "proxy_response"
    return "sync_response"


def _source_type(source_system: str) -> IntegrationFlowSourceType:
    value = str(source_system or "").lower()
    mapping = {
        "onec": IntegrationFlowSourceType.ONEC,
        "1c": IntegrationFlowSourceType.ONEC,
        "website": IntegrationFlowSourceType.WEBSITE,
        "web": IntegrationFlowSourceType.WEBSITE,
        "wms": IntegrationFlowSourceType.WMS,
        "printer": IntegrationFlowSourceType.PRINTER,
        "manual": IntegrationFlowSourceType.MANUAL,
        "webhook": IntegrationFlowSourceType.WEBHOOK,
        "external_api": IntegrationFlowSourceType.EXTERNAL_API,
    }
    return mapping.get(value, IntegrationFlowSourceType.EXTERNAL_API)


def _target_type(action: FinalActionConfig) -> IntegrationFlowTargetType:
    if action.type in {"send_endpoint", "send_and_return_response"}:
        return IntegrationFlowTargetType.EXTERNAL_API
    return IntegrationFlowTargetType.INTERNAL


def _matcher_group(draft: InputDraftRead) -> dict[str, Any]:
    operation_key = draft.contract.operation_key
    if operation_key.type in {"endpoint", "none"}:
        return {"mode": "all", "rules": [{"type": "always"}]}
    rules = []
    if operation_key.field_path and operation_key.value is not None:
        rules.append(_matcher_rule(draft.input_mode, operation_key.field_path, operation_key.value))
    for fallback in operation_key.fallback_paths:
        if operation_key.value is not None:
            rules.append(_matcher_rule(draft.input_mode, fallback, operation_key.value))
    return {"mode": "any", "rules": rules or [{"type": "always"}]}


def _matcher_rule(input_mode: str, path: str, value: Any) -> dict[str, Any]:
    if input_mode == "xml" or path.startswith("xml."):
        return {"type": "xml_path_equals", "path": _relative_matcher_path(path), "value": value}
    if input_mode == "raw_text" or path.startswith("request.raw_text"):
        return {"type": "text_contains", "value": str(value)}
    return {"type": "body_path_equals", "path": _relative_matcher_path(path), "value": value}


def _matcher_human(draft: InputDraftRead) -> str:
    operation_key = draft.contract.operation_key
    if operation_key.type == "endpoint":
        return f"endpoint /api/bus/in/{draft.slug}"
    if operation_key.type == "none":
        return "always"
    paths = [operation_key.field_path, *operation_key.fallback_paths]
    parts = [f"{_relative_matcher_path(path or '')} = {operation_key.value}" for path in paths if path]
    return " OR ".join(parts) if parts else "always"


def _relative_matcher_path(path: str) -> str:
    if path.startswith("request.body."):
        return path.removeprefix("request.body.")
    if path.startswith("request.raw_text."):
        return path.removeprefix("request.raw_text.")
    if path.startswith("xml."):
        return path.removeprefix("xml.")
    return path


def _action_json(draft: InputDraftRead, action: FinalActionConfig, comment: str | None) -> dict[str, Any]:
    return {
        "type": "call_rest_api" if action.type in {"send_endpoint", "send_and_return_response"} else "create_event_only" if action.type == "accepted_event" else "return_response",
        "operation": action.type,
        "business_object": draft.slug,
        "method": action.method,
        "url": action.url,
        "body_mode": action.body_type,
        "response_mode": _endpoint_response_mode(action),
        "comment": comment,
    }


def _test_payload(draft: InputDraftRead) -> tuple[dict[str, Any] | None, str | None]:
    sample = draft.contract.sample
    if draft.input_mode == "json":
        if isinstance(sample, dict):
            return sample, None
        if isinstance(sample, str):
            try:
                parsed = json.loads(sample)
                return parsed if isinstance(parsed, dict) else {"payload": parsed}, None
            except json.JSONDecodeError:
                return {"payload": sample}, None
        return {"payload": sample}, None
    if isinstance(sample, str):
        return None, sample
    return None, json.dumps(sample, ensure_ascii=False, indent=2)


def _description(draft: InputDraftRead, comment: str | None) -> str:
    lines = ["Created from Integration Master draft.", f"Draft ID: {draft.id}"]
    if comment:
        lines.append(f"Comment: {comment}")
    return "\n".join(lines)


def _title(value: str | None) -> str:
    return str(value or "step").replace("_", " ").replace("-", " ").strip().title()
