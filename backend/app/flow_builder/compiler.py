from __future__ import annotations

from typing import Any

from app.flow_builder.validator import validate_builder

HANDLERS = {
    "read_variable": "flow_read_variable",
    "odata_query": "flow_odata_query",
    "resolve_object": "resolve_object",
    "build_json": "flow_build_json",
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
            config["step_id"] = step_id
            config["step_type"] = step_type
            config["display_name"] = step.get("name") or _title(step_id)
            steps.append({"name": step_id, "handler": HANDLERS[step_type], "config": config})
        steps.append({"name": "create_incident", "on": "failure"})
        return {"valid": True, "steps_json": steps, "validation": validation}


def _title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()
