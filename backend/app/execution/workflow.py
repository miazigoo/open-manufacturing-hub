from __future__ import annotations

from typing import Any

DEFAULT_EXECUTION_STEPS: list[dict[str, Any]] = [
    {"name": "receive"},
    {"name": "maintenance_guard"},
    {"name": "normalize"},
    {"name": "validate"},
    {"name": "map_payload"},
    {"name": "call_connector"},
    {"name": "handle_response"},
    {"name": "create_incident", "on": "failure"},
    {"name": "send_notifications", "on": "failure"},
]
DEFAULT_VALIDATION = {"required_fields": ["order_id", "warehouse_id", "items"]}


def normalize_step_configs(steps_json: list[Any] | None) -> list[dict[str, Any]]:
    configs = steps_json or DEFAULT_EXECUTION_STEPS
    normalized: list[dict[str, Any]] = []
    for item in configs:
        if isinstance(item, str):
            normalized.append({"name": item})
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            normalized.append(dict(item))
        else:
            raise ValueError("Workflow step config must be a string or object with name")
    return normalized


def step_condition(config: dict[str, Any]) -> str:
    condition = str(config.get("on") or "always")
    return "failure" if condition == "on_failure" else condition
