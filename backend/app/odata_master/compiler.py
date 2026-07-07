from __future__ import annotations

import json
import re
from typing import Any

from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import BadRequestError
from app.flow_builder.validator import validate_builder
from app.integration_flows.schemas import IntegrationFlowCreate
from app.odata_master.schemas import ODataFinalAction, ODataObjectStep, ODataQueryStep, ODataResponseSpec, ODataWizardSpec

ODATA_TOP_MAX = 500


def compile_wizard_spec(spec: ODataWizardSpec, *, enabled: bool = True) -> dict[str, Any]:
    _validate_top_limits(spec)
    builder_json = _builder_json(spec)
    validation = validate_builder(builder_json)
    if not validation["valid"]:
        raise BadRequestError(json.dumps(validation, ensure_ascii=False))
    flow_payload = _flow_payload(spec, builder_json, enabled=enabled)
    return {"builder_json": builder_json, "flow_payload": flow_payload.model_dump(mode="json"), "validation": validation}


def build_onec_object_resource(base_resource: str, object_key: str, tabular_part: str | None = None) -> str:
    key = _placeholder(object_key)
    suffix = f"/{tabular_part.strip()}" if tabular_part and tabular_part.strip() else ""
    return f"{base_resource.strip()}(guid'{key}'){suffix}"


def _builder_json(spec: ODataWizardSpec) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    variables = _variables(spec)
    operation_key = _operation_key(spec)
    operation_field = _operation_field(spec)
    if operation_field and operation_key:
        steps.append(
            {
                "id": "read_request_key",
                "type": "read_variable",
                "name": "Прочитать ключ запроса",
                "path": f"request.body.{operation_field}",
                "fallback_paths": _operation_fallback_paths(operation_field),
                "save_as": "request_key",
            }
        )

    for index, step in enumerate(spec.steps, start=1):
        if step.type == "foreach_odata":
            steps.append(_foreach_step(step, index))
        else:
            steps.append(_odata_step(step, index))

    steps.extend(_final_steps(spec.final_action))
    return {
        "version": 1,
        "kind": "odata_master",
        "input": {
            "endpoint_slug": spec.slug,
            "input_mode": spec.source.input_mode,
            "response_mode": _endpoint_response_mode(spec.final_action),
            "source_system": spec.source.system,
        },
        "variables": variables,
        "steps": steps,
    }


def _flow_payload(spec: ODataWizardSpec, builder_json: dict[str, Any], *, enabled: bool) -> IntegrationFlowCreate:
    sample_json, sample_text = _test_payload(spec)
    action = {
        "type": "create_event_only",
        "operation": _operation_key(spec) or spec.slug,
        "business_object": "ODataIntegration",
        "description": spec.description or spec.name,
    }
    return IntegrationFlowCreate(
        name=spec.name,
        slug=spec.slug,
        description=spec.description or "OData Master integration",
        enabled=enabled,
        source_type=_source_type(spec.source.system),
        target_type=_target_type(spec.final_action),
        endpoint={
            "input_mode": spec.source.input_mode,
            "response_mode": _endpoint_response_mode(spec.final_action),
            "auth_mode": spec.source.auth_mode,
            "auth_config_json": spec.source.auth_config_json,
        },
        matcher_group_json=_matcher_group(spec),
        action_json=action,
        response_config_json={"response_mode": _endpoint_response_mode(spec.final_action)},
        builder_json=builder_json,
        test_payload_json=sample_json,
        test_payload_text=sample_text,
    )


def _odata_step(step: ODataQueryStep | ODataObjectStep, index: int) -> dict[str, Any]:
    resource = build_onec_object_resource(step.base_resource, step.object_key, step.tabular_part) if isinstance(step, ODataObjectStep) else step.resource
    save_as = _safe_identifier(step.save_as, f"odata_{index}")
    compiled: dict[str, Any] = {
        "id": _step_id(save_as, index),
        "type": "odata_query",
        "name": step.name or f"OData: {resource}",
        "connection": step.connection,
        "resource": resource,
        "select": step.select,
        "top": step.top or 100,
        "paginate": step.paginate,
        "save_as": save_as,
        "required": step.required,
    }
    if step.filter:
        compiled["filter"] = step.filter
    if step.orderby:
        compiled["orderby"] = step.orderby
    return compiled


def _foreach_step(step: Any, index: int) -> dict[str, Any]:
    save_as = _safe_identifier(step.save_as, f"foreach_{index}")
    nested: dict[str, Any] = {
        "type": "odata_query",
        "connection": step.connection,
        "resource": step.resource,
        "select": step.select,
        "top": step.top or 100,
        "paginate": step.paginate,
        "required": step.required,
    }
    if step.filter:
        nested["filter"] = step.filter
    if step.orderby:
        nested["orderby"] = step.orderby
    if step.merge == "first":
        nested["top"] = 1
    return {
        "id": _step_id(save_as, index),
        "type": "foreach",
        "name": step.name or f"Повторить OData по {step.items}",
        "items": step.items,
        "item_as": _safe_identifier(step.item_as, "item"),
        "save_as": save_as,
        "flatten": step.merge == "flatten",
        "continue_on_error": False,
        "step": nested,
    }


def _final_steps(action: ODataFinalAction) -> list[dict[str, Any]]:
    if action.type == "async_accepted":
        return [_response_step(ODataResponseSpec(mode="accepted_event", body_type="json", body={"accepted": True}))]
    if action.type == "return_response":
        return [_response_step(action.response_to_caller)]

    if action.type in {"send_endpoint", "send_onec_http_service"} and not str(action.url or "").strip():
        raise BadRequestError("Для итогового действия 'отправить на endpoint' укажите URL.")

    steps: list[dict[str, Any]] = []
    body_ref: Any = action.body
    if action.body_type == "json":
        steps.append(
            {
                "id": "build_target_payload",
                "type": "build_json",
                "name": "Собрать JSON для отправки",
                "save_as": "target_payload",
                "template": action.body if isinstance(action.body, dict) else {},
            }
        )
        body_ref = "{{target_payload}}"
    headers = {**_content_type_header(action.body_type), **action.headers}
    steps.append(
        {
            "id": "send_to_endpoint",
            "type": "call_endpoint",
            "name": "Отправить результат",
            "method": action.method,
            "url": str(action.url or ""),
            "headers": headers,
            "body": body_ref,
            "response_mode": action.response_to_caller.mode,
        }
    )
    if action.response_to_caller.return_target_response or action.response_to_caller.mode == "proxy_response":
        steps.append(
            {
                "id": "return_target_response",
                "type": "return_response",
                "name": "Вернуть ответ endpoint",
                "body": "{{response}}",
            }
        )
    else:
        steps.append(_response_step(action.response_to_caller))
    return steps


def _response_step(response: ODataResponseSpec) -> dict[str, Any]:
    step: dict[str, Any] = {
        "id": "return_response",
        "type": "return_response",
        "name": "Вернуть ответ вызывающему",
        "status_code": 200,
        "response_body_type": response.body_type,
        "headers": _content_type_header(response.body_type),
    }
    if response.body_type == "json":
        step["body"] = response.body
    else:
        step["body_template"] = str(response.body or "")
    return step


def _endpoint_response_mode(action: ODataFinalAction) -> str:
    if action.type == "async_accepted" or action.response_to_caller.mode == "accepted_event":
        return "accepted_event"
    if action.response_to_caller.mode == "proxy_response":
        return "proxy_response"
    return "sync_response"


def _matcher_group(spec: ODataWizardSpec) -> dict[str, Any]:
    field = _operation_field(spec)
    value = _operation_key(spec)
    if spec.source.input_mode == "json" and field and value:
        rules = [{"type": "body_path_equals", "path": field, "value": value}]
        if field == "operation":
            rules.append({"type": "body_path_equals", "path": "sinc", "value": value})
        elif field == "sinc":
            rules.append({"type": "body_path_equals", "path": "operation", "value": value})
        return {"mode": "any", "rules": rules}
    if spec.source.input_mode == "xml" and value:
        return {"mode": "any", "rules": [{"type": "xml_contains", "value": value}, {"type": "text_contains", "value": value}]}
    return {"mode": "all", "rules": [{"type": "always"}]}


def _operation_field(spec: ODataWizardSpec) -> str | None:
    raw = spec.source.operation_key.field
    if raw in {None, "", "none", "no_key", "endpoint_slug"}:
        return None
    if raw == "custom":
        return spec.source.operation_key.custom_field
    return raw


def _operation_key(spec: ODataWizardSpec) -> str | None:
    explicit = spec.source.operation_key.value
    if explicit:
        return explicit
    field = _operation_field(spec)
    sample = _json_sample(spec.source.sample)
    if field and isinstance(sample.get(field), str) and sample[field].strip():
        return sample[field].strip()
    for fallback in ("sinc", "operation"):
        if isinstance(sample.get(fallback), str) and sample[fallback].strip():
            return sample[fallback].strip()
    return spec.source.endpoint_slug or spec.slug


def _operation_fallback_paths(field: str) -> list[str]:
    if field == "operation":
        return ["request.body.sinc"]
    if field == "sinc":
        return ["request.body.operation"]
    return []


def _variables(spec: ODataWizardSpec) -> list[dict[str, str]]:
    variables: list[dict[str, str]] = []
    field = _operation_field(spec)
    if field:
        variables.append({"name": "request_key", "source": f"request.body.{field}"})
    if spec.source.input_mode == "json":
        for key in _json_sample(spec.source.sample):
            if key not in {"operation", "sinc"}:
                variables.append({"name": _safe_identifier(key, key), "source": f"request.body.{key}"})
    variables.extend({"name": step.save_as, "source": f"steps.{_step_id(step.save_as, index)}"} for index, step in enumerate(spec.steps, start=1))
    variables.extend([{"name": "context.event_id", "source": "context.event_id"}, {"name": "context.run_id", "source": "context.run_id"}])
    return variables


def _test_payload(spec: ODataWizardSpec) -> tuple[dict[str, Any] | None, str | None]:
    if spec.source.input_mode == "json":
        return _json_sample(spec.source.sample), None
    return None, str(spec.source.sample or "")


def _json_sample(sample: Any) -> dict[str, Any]:
    if isinstance(sample, dict):
        return sample
    if isinstance(sample, str) and sample.strip():
        try:
            parsed = json.loads(sample)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _source_type(system: str) -> IntegrationFlowSourceType:
    normalized = (system or "").lower().strip()
    if normalized in {"1c", "onec", "1с"}:
        return IntegrationFlowSourceType.ONEC
    if normalized == "wms":
        return IntegrationFlowSourceType.WMS
    if normalized in {"website", "web"}:
        return IntegrationFlowSourceType.WEBSITE
    if normalized == "webhook":
        return IntegrationFlowSourceType.WEBHOOK
    return IntegrationFlowSourceType.EXTERNAL_API


def _target_type(action: ODataFinalAction) -> IntegrationFlowTargetType:
    if action.type in {"send_endpoint", "send_onec_http_service"}:
        return IntegrationFlowTargetType.EXTERNAL_API if action.type == "send_endpoint" else IntegrationFlowTargetType.ONEC
    return IntegrationFlowTargetType.ODATA_LOOKUP


def _content_type_header(body_type: str) -> dict[str, str]:
    if body_type == "xml":
        return {"Content-Type": "application/xml"}
    if body_type == "raw_text":
        return {"Content-Type": "text/plain; charset=utf-8"}
    return {"Content-Type": "application/json"}


def _validate_top_limits(spec: ODataWizardSpec) -> None:
    for index, step in enumerate(spec.steps, start=1):
        top = getattr(step, "top", None)
        if top is not None and int(top) > ODATA_TOP_MAX:
            raise BadRequestError(f"OData-шаг #{index}: $top не может быть больше {ODATA_TOP_MAX}. Установите $top = {ODATA_TOP_MAX} и включите пагинацию.")


def _placeholder(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("{{") and stripped.endswith("}}"):
        return stripped
    return "{{" + stripped + "}}"


def _safe_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_")
    if not cleaned:
        cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", fallback).strip("_") or "value"
    if cleaned[0].isdigit():
        cleaned = f"v_{cleaned}"
    return cleaned[:80]


def _step_id(save_as: str, index: int) -> str:
    return f"step_{index}_{_safe_identifier(save_as, f'odata_{index}')}"
