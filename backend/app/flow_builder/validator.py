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
        if step_type == "odata_query":
            for field, code in (("connection", "ODATA_CONNECTION_NOT_SET"), ("resource", "ODATA_RESOURCE_NOT_SET"), ("save_as", "ODATA_SAVE_AS_REQUIRED")):
                if not step.get(field):
                    errors.append(_error(step_id, code, f"OData step needs {field}", "Select connector/resource and save result variable."))
        if step_type == "build_json" and not (step.get("template") or step.get("fields")):
            errors.append(_error(step_id, "JSON_TEMPLATE_REQUIRED", "Build JSON step needs template or visual fields", "Add target fields or switch to advanced JSON template."))
        if step_type == "call_endpoint" and not step.get("connector"):
            errors.append(_error(step_id, "TARGET_CONNECTOR_NOT_SET", "Endpoint step needs connector", "Select a REST/1C target connector."))
    if not any(isinstance(step, dict) and step.get("type") == "call_endpoint" for step in steps):
        warnings.append(_error(None, "TARGET_STEP_MISSING", "Flow has no target endpoint call", "Add Call Endpoint when this flow should send data out."))
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _error(step_id: str | None, code: str, message: str, hint: str | None) -> dict[str, Any]:
    return {"step_id": step_id, "code": code, "message": message, "hint": hint}
