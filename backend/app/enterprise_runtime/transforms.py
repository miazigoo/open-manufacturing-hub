from __future__ import annotations

from typing import Any

from app.transforms.engine import engine as transform_engine
from app.transforms.registry import registry

ALIASES = {
    "hash": "hash_sha256",
    "base64": "base64_encode",
    "xml_encode": "xml_escape",
    "xml_decode": "xml_unescape",
}


def list_transforms() -> list[dict[str, str]]:
    return [{"name": item.name, "description": item.description} for item in registry.list()]


def apply_transform(name: str, value: Any = None, params: dict[str, Any] | None = None) -> Any:
    real_name = ALIASES.get(name, name)
    result = transform_engine.apply_chain(value, [{"name": real_name, "args": params or {}}], {})
    if not result.success:
        raise ValueError(result.error_message or result.error_code or f"Unknown transform: {name}")
    return result.value
