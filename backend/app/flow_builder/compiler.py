from __future__ import annotations

from typing import Any

from app.flow_builder.validator import validate_builder

HANDLERS = {
    "read_variable": "flow_read_variable",
    "apply_transforms": "apply_transforms",
    "evaluate_rules": "evaluate_rules",
    "odata_query": "flow_odata_query",
    "xml_extract": "xml_extract",
    "raw_xml_forward": "raw_xml_forward",
    "resolve_object": "resolve_object",
    "build_json": "flow_build_json",
    "build_payload": "flow_build_payload",
    "foreach": "flow_foreach",
    "extract": "flow_extract",
    "filter_array": "flow_filter_array",
    "build_xml": "flow_build_xml",
    "call_operation": "flow_call_operation",
    "call_flow": "flow_call_flow",
    "ozon_action": "flow_ozon_action",
    "print_labels": "flow_print_labels",
    "marking_code_pool_export": "flow_marking_code_pool_export",
    "build_xml_response": "flow_return_response",
    "condition": "flow_condition",
    "call_endpoint": "flow_call_endpoint",
    "return_response": "flow_return_response",
}


class FlowCompiler:
    def compile(self, builder_json: dict[str, Any]) -> dict[str, Any]:
        validation = validate_builder(builder_json)
        if not validation["valid"]:
            return {"valid": False, "steps_json": [], "validation": validation}
        steps = []
        for step in builder_json.get("steps") or []:
            step_type = str(step.get("type"))
            step_id = str(step.get("id") or step_type)
            config = {key: value for key, value in step.items() if key not in {"id", "type", "name"}}
            if step_type == "build_xml_response":
                config["response_body_type"] = "xml"
                config["body_template"] = config.get("body_template") or config.get("template") or ""
                config.setdefault("headers", {"Content-Type": "application/xml"})
            config["step_id"] = step_id
            config["step_type"] = step_type
            config["display_name"] = step.get("name") or _title(step_id)
            steps.append({"name": step_id, "handler": HANDLERS[step_type], "config": config})
        steps.append({"name": "create_incident", "on": "failure"})
        return {"valid": True, "steps_json": steps, "validation": validation}


def _title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()
