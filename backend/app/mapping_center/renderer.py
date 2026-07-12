from __future__ import annotations

import copy
import re
from typing import Any

from app.data_contracts.validator import field_map
from app.mapping_center.schemas import MappingIssue, MappingPreviewSummary, MappingRenderResponse

TEMPLATE_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
MISSING = object()


def render_mapping(mapping_json: dict[str, Any], variables: dict[str, Any] | None, target_contract_schema: dict[str, Any] | None = None) -> MappingRenderResponse:
    source = variables or {}
    payload: Any = {}
    errors: list[MappingIssue] = []
    warnings: list[MappingIssue] = []

    fields = mapping_json.get("fields", []) if isinstance(mapping_json, dict) else []
    if not isinstance(fields, list):
        errors.append(_issue("MAPPING_INVALID_FORMAT", "mapping_json.fields должен быть массивом."))
        return MappingRenderResponse(success=False, payload={}, preview={}, errors=errors, warnings=warnings, summary=_summary({}))

    for field in fields:
        if not isinstance(field, dict):
            errors.append(_issue("MAPPING_INVALID_FORMAT", "Правило mapping field должно быть объектом."))
            continue
        target_path = str(field.get("target_path") or "").strip()
        if not target_path:
            errors.append(_issue("MAPPING_INVALID_FORMAT", "Правило mapping field должно иметь target_path."))
            continue
        source_type = str(field.get("source_type") or "variable")
        value = _render_field_value(field, source, errors)
        if value is MISSING:
            continue
        if source_type == "dynamic_object_entry":
            _apply_dynamic_entry(payload, {"object_path": target_path, **field}, source, errors)
            continue
        payload = set_path(payload, target_path, value)

    dynamic_entries = mapping_json.get("dynamic_entries", []) if isinstance(mapping_json, dict) else []
    if isinstance(dynamic_entries, list):
        for entry in dynamic_entries:
            if isinstance(entry, dict):
                _apply_dynamic_entry(payload, entry, source, errors)
            else:
                errors.append(_issue("MAPPING_INVALID_FORMAT", "Правило dynamic entry должно быть объектом."))
    else:
        errors.append(_issue("MAPPING_INVALID_FORMAT", "mapping_json.dynamic_entries должен быть массивом."))

    required_errors = required_field_errors(payload, target_contract_schema)
    errors.extend(required_errors)
    preview = compact_preview(payload)
    return MappingRenderResponse(success=not errors, payload=payload, preview=preview, errors=errors, warnings=warnings, summary=_summary(preview))


def _render_field_value(field: dict[str, Any], source: dict[str, Any], errors: list[MappingIssue]) -> Any:
    source_type = str(field.get("source_type") or "variable")
    if source_type == "variable":
        path = str(field.get("source") or "").strip()
        value = get_path(source, path)
        if value is MISSING:
            errors.append(_missing(path))
            return MISSING
        return copy.deepcopy(value)
    if source_type == "constant":
        return copy.deepcopy(field.get("value"))
    if source_type == "template":
        template = str(field.get("source") if field.get("source") is not None else field.get("value") if field.get("value") is not None else "")
        rendered = _render_template(template, source, errors)
        return rendered
    if source_type == "dynamic_object_entry":
        return MISSING
    errors.append(_issue("MAPPING_UNSUPPORTED_SOURCE_TYPE", f"source_type {source_type} не поддерживается.", str(field.get("target_path") or "")))
    return MISSING


def _render_template(template: str, source: dict[str, Any], errors: list[MappingIssue]) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value = get_path(source, path)
        if value is MISSING:
            errors.append(_missing(path))
            return ""
        if isinstance(value, (dict, list)):
            return str(value)
        return "" if value is None else str(value)

    return TEMPLATE_RE.sub(replace, template)


def _apply_dynamic_entry(payload: Any, entry: dict[str, Any], source: dict[str, Any], errors: list[MappingIssue]) -> Any:
    object_path = str(entry.get("object_path") or entry.get("target_path") or "").strip()
    key_source = str(entry.get("key_source") or "").strip()
    value_source = str(entry.get("value_source") or entry.get("source") or "").strip()
    if not object_path or not key_source or not value_source:
        errors.append(_issue("MAPPING_INVALID_FORMAT", "Dynamic entry должен иметь object_path, key_source и value_source.", object_path or None))
        return payload
    key_value = get_path(source, key_source)
    if key_value is MISSING:
        errors.append(_missing(key_source))
        return payload
    value = get_path(source, value_source)
    if value is MISSING:
        errors.append(_missing(value_source))
        return payload
    existing = get_path(payload, object_path)
    if existing is MISSING or existing is None:
        payload = set_path(payload, object_path, {})
        existing = get_path(payload, object_path)
    if not isinstance(existing, dict):
        errors.append(_issue("MAPPING_DYNAMIC_TARGET_NOT_OBJECT", f"Цель {object_path} должна быть object для dynamic entry.", object_path))
        return payload
    existing[str(key_value)] = copy.deepcopy(value)
    return payload


def required_field_errors(payload: Any, target_contract_schema: dict[str, Any] | None) -> list[MappingIssue]:
    errors: list[MappingIssue] = []
    for path, field in field_map(target_contract_schema).items():
        if not field.required:
            continue
        value = get_path(payload, path)
        if value is MISSING or value is None:
            errors.append(_issue("MAPPING_REQUIRED_FIELD_MISSING", f"Обязательное поле {path} не заполнено.", path))
    return errors


def get_path(data: Any, path: str) -> Any:
    if not path:
        return MISSING
    current = data
    for part in parse_path(path):
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                return MISSING
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                return MISSING
            current = current[part]
    return current


def set_path(data: Any, path: str, value: Any) -> Any:
    parts = parse_path(path)
    if not parts:
        return value
    if not isinstance(data, (dict, list)):
        data = [] if isinstance(parts[0], int) else {}
    current = data
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        next_part = None if last else parts[index + 1]
        if isinstance(part, int):
            if not isinstance(current, list):
                raise TypeError(f"Cannot set numeric path segment {part} inside non-list")
            while len(current) <= part:
                current.append({} if not isinstance(next_part, int) else [])
            if last:
                current[part] = value
            else:
                if not isinstance(current[part], (dict, list)):
                    current[part] = {} if not isinstance(next_part, int) else []
                current = current[part]
        else:
            if not isinstance(current, dict):
                raise TypeError(f"Cannot set object path segment {part} inside non-object")
            if last:
                current[part] = value
            else:
                if part not in current or not isinstance(current[part], (dict, list)):
                    current[part] = [] if isinstance(next_part, int) else {}
                current = current[part]
    return data


def parse_path(path: str) -> list[str | int]:
    parts: list[str | int] = []
    for segment in path.split("."):
        rest = segment
        while rest:
            bracket = rest.find("[")
            if bracket == -1:
                if rest:
                    parts.append(rest)
                break
            if bracket > 0:
                parts.append(rest[:bracket])
            close = rest.find("]", bracket)
            if close == -1:
                parts.append(rest[bracket + 1 :])
                break
            raw_index = rest[bracket + 1 : close]
            parts.append(int(raw_index) if raw_index.isdigit() else raw_index)
            rest = rest[close + 1 :]
    return [part for part in parts if part != ""]


def compact_preview(value: Any, *, max_array_items: int = 3) -> Any:
    if isinstance(value, list):
        return [compact_preview(item, max_array_items=max_array_items) for item in value[:max_array_items]]
    if isinstance(value, dict):
        return {key: compact_preview(item, max_array_items=max_array_items) for key, item in value.items()}
    return value


def _summary(preview: Any) -> MappingPreviewSummary:
    truncated: dict[str, int] = {}
    _collect_truncated(preview, "", truncated)
    return MappingPreviewSummary(
        root_type="array" if isinstance(preview, list) else "object" if isinstance(preview, dict) else type(preview).__name__,
        top_level_keys=list(preview.keys()) if isinstance(preview, dict) else [],
        truncated_arrays=truncated,
    )


def _collect_truncated(_: Any, __: str, ___: dict[str, int]) -> None:
    # Renderer keeps the full payload and caps preview arrays at 3 items; UI can disclose the full payload explicitly.
    return None


def _missing(path: str) -> MappingIssue:
    return _issue("MAPPING_SOURCE_NOT_FOUND", f"Переменная {path} не найдена.", path)


def _issue(code: str, message: str, path: str | None = None, severity: str = "error") -> MappingIssue:
    return MappingIssue(error_code=code, message=message, path=path, severity=severity)  # type: ignore[arg-type]
