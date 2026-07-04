from __future__ import annotations

from typing import Any

from app.variables.resolver import render_template
from app.variables.paths import resolve_path
from app.transforms.engine import engine as transform_engine


def build_json_from_template(template: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    result = render_template(template, scope)
    if not isinstance(result, dict):
        raise ValueError("JSON builder template must render to an object")
    return result


def build_json_from_fields(fields: list[dict[str, Any]], scope: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in fields:
        target = str(field.get("target") or "").strip()
        if not target:
            raise ValueError("JSON builder field target is required")
        mode = str(field.get("mode") or "path")
        raw_value = field.get("value")
        if mode == "constant":
            value = raw_value
        elif mode == "template":
            value = render_template(raw_value, scope)
        else:
            value = resolve_path(scope, str(raw_value))
        if field.get("transforms"):
            transformed = transform_engine.apply_chain(value, field.get("transforms") or [], scope)
            if not transformed.success:
                raise ValueError(transformed.error_message or transformed.error_code or "JSON field transform failed")
            value = transformed.value
        _set_path(result, target, value)
    return result


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ValueError("JSON builder target path is empty")
    current = target
    for part in parts[:-1]:
        current = current.setdefault(part, {})
        if not isinstance(current, dict):
            raise ValueError(f"Target path {path} collides with non-object value")
    current[parts[-1]] = value
