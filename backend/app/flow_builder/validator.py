from __future__ import annotations

from typing import Any

from app.flow_steps.registry import BUILDER_STEP_TYPES


def validate_builder(builder_json: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not isinstance(builder_json, dict):
        return {"valid": False, "errors": [{"step_id": None, "code": "BUILDER_INVALID", "message": "Builder JSON must be an object", "hint": "Open the visual builder and save again."}], "warnings": []}
    steps = builder_json.get("steps") or []
    if not isinstance(steps, list) or not steps:
        errors.append(_error(None, "STEPS_REQUIRED", "At least one builder step is required", "Add OData, JSON builder or endpoint steps."))
    seen: set[str] = set()
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(_error(None, "STEP_INVALID", f"Step #{index + 1} must be an object", None))
            continue
        step_id = str(step.get("id") or "").strip()
        step_type = str(step.get("type") or "").strip()
        if not step_id:
            errors.append(_error(None, "STEP_ID_REQUIRED", f"Step #{index + 1} has no id", "Use stable ids like get_contractor or build_payload."))
        elif step_id in seen:
            errors.append(_error(step_id, "STEP_ID_DUPLICATE", f"Step id {step_id} is duplicated", "Each step id must be unique."))
        seen.add(step_id)
        if step_type not in BUILDER_STEP_TYPES:
            errors.append(_error(step_id or None, "STEP_TYPE_UNSUPPORTED", f"Unsupported step type: {step_type}", "Use one of the visual builder block types."))
            continue
        if step_type == "read_variable" and not (step.get("name") or step.get("save_as")):
            errors.append(_error(step_id, "VARIABLE_NAME_REQUIRED", "Read variable step needs name/save_as", "Choose a variable name such as inn."))
        if step_type == "read_variable" and not step.get("path"):
            errors.append(_error(step_id, "VARIABLE_PATH_REQUIRED", "Read variable step needs source path", "Example: request.body.inn."))
        if step_type == "apply_transforms":
            chains = step.get("chains")
            if not isinstance(chains, list) or not chains:
                errors.append(_error(step_id, "TRANSFORM_CHAINS_REQUIRED", "Transform step needs at least one chain", "Map source -> transforms -> target."))
        if step_type == "evaluate_rules":
            if not (step.get("rule_set") or step.get("rules") or step.get("rules_json")):
                errors.append(_error(step_id, "RULE_SET_REQUIRED", "Rule step needs rule_set or inline rules", "Select a saved rule set or use advanced JSON."))
        if step_type == "odata_query":
            for field, code in (("connection", "ODATA_CONNECTION_NOT_SET"), ("resource", "ODATA_RESOURCE_NOT_SET"), ("save_as", "ODATA_SAVE_AS_REQUIRED")):
                if not step.get(field):
                    errors.append(_error(step_id, code, f"OData step needs {field}", "Select connector/resource and save result variable."))
        if step_type == "resolve_object":
            if not (step.get("resolver") or step.get("resolver_code")):
                errors.append(_error(step_id, "RESOLVER_CODE_REQUIRED", "Resolve step needs resolver code", "Select a resolver such as resolve_customer or resolve_product."))
            if not isinstance(step.get("input") or {}, dict):
                errors.append(_error(step_id, "RESOLVER_INPUT_INVALID", "Resolve step input must be a JSON object", "Map fields like inn -> request.body.inn."))
            if not step.get("save_as"):
                errors.append(_error(step_id, "RESOLVER_SAVE_AS_REQUIRED", "Resolve step needs save_as", "Save the canonical object as customer, product or warehouse."))
        if step_type == "build_json" and not (step.get("template") or step.get("fields")):
            errors.append(_error(step_id, "JSON_TEMPLATE_REQUIRED", "Build JSON step needs template or visual fields", "Add target fields or switch to advanced JSON template."))
        if step_type == "call_endpoint" and not step.get("connector"):
            errors.append(_error(step_id, "TARGET_CONNECTOR_NOT_SET", "Endpoint step needs connector", "Select a REST/1C target connector."))
    has_terminal_response = any(isinstance(step, dict) and step.get("type") in {"call_endpoint", "return_response"} for step in steps)
    if not has_terminal_response:
        warnings.append(_error(None, "TARGET_STEP_MISSING", "Flow has no target endpoint call", "Add Call Endpoint when this flow should send data out."))
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _error(step_id: str | None, code: str, message: str, hint: str | None) -> dict[str, Any]:
    return {"step_id": step_id, "code": code, "message": message, "hint": hint}
