from __future__ import annotations

from typing import Any

from app.mappings.engine import get_path


def render_filter_template(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", _escape_odata_value(value))
    return rendered


def extract_fields(item: dict[str, Any], extract: dict[str, str]) -> dict[str, Any]:
    return {target: get_path(item, source) for target, source in extract.items()}


def _escape_odata_value(value: Any) -> str:
    return str(value).replace("'", "''")
