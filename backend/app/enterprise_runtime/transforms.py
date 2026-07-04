from __future__ import annotations

import base64
import hashlib
import html
from datetime import datetime
from typing import Any
from uuid import uuid4


def list_transforms() -> list[dict[str, str]]:
    return [
        {"name": name, "description": description}
        for name, description in {
            "uppercase": "Convert text to uppercase",
            "lowercase": "Convert text to lowercase",
            "trim": "Trim leading and trailing whitespace",
            "replace": "Replace substring",
            "concat": "Concatenate values",
            "split": "Split text by separator",
            "uuid": "Generate UUID4",
            "hash": "SHA-256 hash",
            "base64": "Base64 encode",
            "xml_encode": "Escape XML entities",
            "xml_decode": "Unescape XML entities",
            "date_format": "Format ISO datetime",
            "default_value": "Return fallback when value is empty",
        }.items()
    ]


def apply_transform(name: str, value: Any = None, params: dict[str, Any] | None = None) -> Any:
    params = params or {}
    if name == "uppercase":
        return str(value or "").upper()
    if name == "lowercase":
        return str(value or "").lower()
    if name == "trim":
        return str(value or "").strip()
    if name == "replace":
        return str(value or "").replace(str(params.get("old", "")), str(params.get("new", "")))
    if name == "concat":
        values = params.get("values", [])
        return str(value or "") + "".join(str(item) for item in values)
    if name == "split":
        return str(value or "").split(str(params.get("separator", ",")))
    if name == "uuid":
        return str(uuid4())
    if name == "hash":
        return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()
    if name == "base64":
        return base64.b64encode(str(value or "").encode("utf-8")).decode("ascii")
    if name == "xml_encode":
        return html.escape(str(value or ""), quote=True)
    if name == "xml_decode":
        return html.unescape(str(value or ""))
    if name == "date_format":
        source = datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else datetime.utcnow()
        return source.strftime(str(params.get("format", "%Y-%m-%d")))
    if name == "default_value":
        return value if value not in (None, "", [], {}) else params.get("default")
    raise ValueError(f"Unknown transform: {name}")
