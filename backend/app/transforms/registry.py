from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from app.transforms.schemas import TransformDefinition

TransformFn = Callable[[Any, dict[str, Any], dict[str, Any]], Any]


class TransformRegistry:
    def __init__(self) -> None:
        self._items: dict[str, tuple[TransformDefinition, TransformFn]] = {}
        self._register_defaults()

    def register(self, definition: TransformDefinition, fn: TransformFn) -> None:
        self._items[definition.name] = (definition, fn)

    def get(self, name: str) -> tuple[TransformDefinition, TransformFn] | None:
        return self._items.get(name)

    def list(self) -> list[TransformDefinition]:
        return [item[0] for item in sorted(self._items.values(), key=lambda pair: (pair[0].category, pair[0].name))]

    def _register_defaults(self) -> None:
        self.register(TransformDefinition(name="trim", category="string", description="Trim leading and trailing whitespace"), lambda v, a, c: str(v or "").strip())
        self.register(TransformDefinition(name="uppercase", category="string", description="Convert text to uppercase"), lambda v, a, c: str(v or "").upper())
        self.register(TransformDefinition(name="lowercase", category="string", description="Convert text to lowercase"), lambda v, a, c: str(v or "").lower())
        self.register(TransformDefinition(name="replace", category="string", description="Replace substring", args_schema={"old": "string", "new": "string"}), lambda v, a, c: str(v or "").replace(str(a.get("old", "")), str(a.get("new", ""))))
        self.register(TransformDefinition(name="remove_spaces", category="string", description="Remove all whitespace characters"), lambda v, a, c: re.sub(r"\s+", "", str(v or "")))
        self.register(TransformDefinition(name="normalize_whitespace", category="string", description="Collapse whitespace to single spaces"), lambda v, a, c: re.sub(r"\s+", " ", str(v or "")).strip())
        self.register(TransformDefinition(name="substring", category="string", description="Extract substring", args_schema={"start": "int", "end": "int|null"}), lambda v, a, c: str(v or "")[int(a.get("start", 0)): int(a["end"]) if a.get("end") is not None else None])
        self.register(TransformDefinition(name="split", category="string", description="Split text by separator", args_schema={"separator": "string"}), lambda v, a, c: str(v or "").split(str(a.get("separator", ","))))
        self.register(TransformDefinition(name="join", category="string", description="Join list values", args_schema={"separator": "string"}), lambda v, a, c: str(a.get("separator", ",")).join(str(x) for x in (v if isinstance(v, list) else [v])))
        self.register(TransformDefinition(name="concat", category="string", description="Concatenate value and args.values", args_schema={"values": "array"}), lambda v, a, c: str(v or "") + "".join(str(x) for x in a.get("values", [])))
        self.register(TransformDefinition(name="regex_replace", category="string", description="Regex replace", args_schema={"pattern": "string", "replacement": "string"}), lambda v, a, c: re.sub(str(a.get("pattern", "")), str(a.get("replacement", "")), str(v or "")))

        self.register(TransformDefinition(name="to_int", category="number", description="Convert value to integer"), lambda v, a, c: int(float(str(v).strip())))
        self.register(TransformDefinition(name="to_float", category="number", description="Convert value to float"), lambda v, a, c: float(str(v).strip()))
        self.register(TransformDefinition(name="round", category="number", description="Round number", args_schema={"digits": "int"}), lambda v, a, c: round(float(v), int(a.get("digits", 0))))
        self.register(TransformDefinition(name="abs", category="number", description="Absolute numeric value"), lambda v, a, c: abs(float(v)))

        self.register(TransformDefinition(name="date_parse", category="date", description="Parse ISO date/datetime"), lambda v, a, c: _parse_date(v).isoformat())
        self.register(TransformDefinition(name="date_format", category="date", description="Format date/datetime", args_schema={"format": "strftime"}), lambda v, a, c: _parse_date(v).strftime(str(a.get("format", "%Y-%m-%d"))))
        self.register(TransformDefinition(name="now", category="date", description="Current UTC datetime"), lambda v, a, c: datetime.now(timezone.utc).isoformat())

        self.register(TransformDefinition(name="uuid", category="technical", description="Generate UUID4"), lambda v, a, c: str(uuid4()))
        self.register(TransformDefinition(name="hash_sha256", category="technical", description="SHA-256 hash"), lambda v, a, c: hashlib.sha256(str(v or "").encode("utf-8")).hexdigest())
        self.register(TransformDefinition(name="base64_encode", category="technical", description="Base64 encode UTF-8 text"), lambda v, a, c: base64.b64encode(str(v or "").encode("utf-8")).decode("ascii"))
        self.register(TransformDefinition(name="base64_decode", category="technical", description="Base64 decode UTF-8 text"), lambda v, a, c: base64.b64decode(str(v or "").encode("ascii")).decode("utf-8"))
        self.register(TransformDefinition(name="json_stringify", category="technical", description="Serialize value to JSON"), lambda v, a, c: json.dumps(v, ensure_ascii=False, sort_keys=bool(a.get("sort_keys", False))))
        self.register(TransformDefinition(name="json_parse", category="technical", description="Parse JSON text"), lambda v, a, c: json.loads(str(v or "null")))
        self.register(TransformDefinition(name="xml_escape", category="technical", description="Escape XML entities"), lambda v, a, c: html.escape(str(v or ""), quote=True))
        self.register(TransformDefinition(name="xml_unescape", category="technical", description="Unescape XML entities"), lambda v, a, c: html.unescape(str(v or "")))

        self.register(TransformDefinition(name="default_value", category="defaults", description="Fallback when value is empty", args_schema={"default": "any"}), lambda v, a, c: v if not _is_empty(v) else a.get("default"))
        self.register(TransformDefinition(name="coalesce", category="defaults", description="First non-empty value from value,args.values"), lambda v, a, c: _coalesce([v, *(a.get("values") or [])]))
        self.register(TransformDefinition(name="empty_to_null", category="defaults", description="Convert empty value to null"), lambda v, a, c: None if _is_empty(v) else v)
        self.register(TransformDefinition(name="null_to_empty", category="defaults", description="Convert null to empty string"), lambda v, a, c: "" if v is None else v)


def _parse_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value in (None, ""):
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _is_empty(value: Any) -> bool:
    return value in (None, "", [], {})


def _coalesce(values: list[Any]) -> Any:
    for value in values:
        if not _is_empty(value):
            return value
    return None


registry = TransformRegistry()
