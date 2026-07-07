from __future__ import annotations

import re
from typing import Any

from app.variables.paths import PathResolutionError, resolve_path

_PLACEHOLDER_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
_FULL_PLACEHOLDER_RE = re.compile(r"^{{\s*([^{}]+?)\s*}}$")


def build_runtime_scope(*, request_body: Any, variables: dict[str, Any] | None = None, headers: dict[str, Any] | None = None, query: dict[str, Any] | None = None, raw_text: str | None = None, xml: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    variable_values = variables or {}
    body = request_body if request_body is not None else {}
    scope = {
        "request": {
            "body": body,
            "headers": headers or {},
            "query": query or {},
            "raw_text": raw_text,
            "xml": xml,
        },
        "variables": variable_values,
        "steps": variable_values.get("steps", {}),
        "context": context or {},
    }
    scope.update(variable_values)
    return scope


def render_template(value: Any, scope: dict[str, Any]) -> Any:
    if isinstance(value, str):
        full = _FULL_PLACEHOLDER_RE.match(value)
        if full:
            return _resolve_expression(scope, full.group(1).strip())
        return _PLACEHOLDER_RE.sub(lambda match: _stringify(_resolve_expression(scope, match.group(1).strip())), value)
    if isinstance(value, list):
        return [render_template(item, scope) for item in value]
    if isinstance(value, dict):
        return {
            _stringify(render_template(key, scope)) if isinstance(key, str) else key: render_template(item, scope)
            for key, item in value.items()
        }
    return value


def _resolve_expression(scope: dict[str, Any], expression: str) -> Any:
    if expression in scope:
        return scope[expression]
    if not expression.startswith(("request.", "variables.", "steps.", "context.")) and f"variables.{expression}" in _candidate_paths(expression):
        try:
            return resolve_path(scope, f"variables.{expression}")
        except PathResolutionError:
            pass
    return resolve_path(scope, expression)


def _candidate_paths(expression: str) -> list[str]:
    return [expression, f"variables.{expression}"]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False)
    return str(value)
