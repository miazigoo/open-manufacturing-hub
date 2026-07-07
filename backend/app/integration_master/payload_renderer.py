from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape as xml_escape

from app.integration_master.schemas import PayloadStepConfig

PLACEHOLDER_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
FULL_PLACEHOLDER_RE = re.compile(r"^{{\s*([^{}]+?)\s*}}$")
TOKEN_RE = re.compile(r"([^.[\]]+)|\[(\d+)\]")
MAX_PREVIEW_ARRAY_ITEMS = 3


@dataclass(slots=True)
class PayloadRenderError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class PayloadRenderResult:
    rendered_body: Any
    rendered_preview: Any
    size_bytes: int
    warnings: list[str]


def render_payload_step(step: PayloadStepConfig, variables: dict[str, Any]) -> PayloadRenderResult:
    warnings: list[str] = []
    if step.body_type == "json":
        rendered = _render_json_step(step, variables)
        body_for_size = json.dumps(rendered, ensure_ascii=False, separators=(",", ":"))
    elif step.body_type == "xml":
        template = _template_as_text(step.template)
        rendered = render_xml_template(template, variables)
        body_for_size = rendered
    elif step.body_type == "raw_text":
        template = _template_as_text(step.template)
        rendered = render_text_template(template, variables)
        body_for_size = rendered
    else:
        raise PayloadRenderError("PAYLOAD_BODY_TYPE_INVALID", "Выберите формат тела: JSON, XML или raw text.")

    rendered_preview = _truncate_preview(rendered, warnings)
    return PayloadRenderResult(
        rendered_body=rendered,
        rendered_preview=rendered_preview,
        size_bytes=len(body_for_size.encode("utf-8")),
        warnings=warnings,
    )


def render_json_template(template: Any, variables: dict[str, Any]) -> Any:
    if isinstance(template, str):
        full = FULL_PLACEHOLDER_RE.fullmatch(template)
        if full:
            return resolve_template_path(full.group(1).strip(), variables)
        return PLACEHOLDER_RE.sub(lambda match: _stringify(resolve_template_path(match.group(1).strip(), variables)), template)
    if isinstance(template, list):
        return [render_json_template(item, variables) for item in template]
    if isinstance(template, dict):
        rendered: dict[str, Any] = {}
        for key, value in template.items():
            rendered_key = render_json_key(str(key), variables)
            rendered[rendered_key] = render_json_template(value, variables)
        return rendered
    return template


def render_json_key(template: str, variables: dict[str, Any]) -> str:
    value = PLACEHOLDER_RE.sub(lambda match: _stringify(resolve_template_path(match.group(1).strip(), variables)), template)
    if not value:
        raise PayloadRenderError("PAYLOAD_DYNAMIC_KEY_EMPTY", "Динамический JSON-ключ не может быть пустым.")
    return value


def render_json_fields(fields: list[Any], dynamic_entries: list[Any], variables: dict[str, Any]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    for field in fields:
        target_path = _field_value(field, "target_path").strip()
        if not target_path:
            raise PayloadRenderError("PAYLOAD_TARGET_PATH_REQUIRED", "Укажите target path для каждой JSON-строки.")
        value = _render_field_value(field, variables)
        _set_object_path(rendered, target_path, value)

    for entry in dynamic_entries:
        object_path = _field_value(entry, "object_path").strip()
        key_source = _field_value(entry, "key_source").strip()
        value_source = _field_value(entry, "value_source").strip()
        if not object_path or not key_source or not value_source:
            raise PayloadRenderError("PAYLOAD_DYNAMIC_ENTRY_REQUIRED", "Для dynamic object нужны object path, key source и value source.")
        container = _ensure_object_path(rendered, object_path)
        dynamic_key = render_json_key(_placeholder(key_source), variables)
        value_type = _field_value(entry, "value_type") or "variable"
        container[dynamic_key] = _render_value_by_type(value_source, value_type, variables)
    return rendered


def render_xml_template(template: str, variables: dict[str, Any]) -> str:
    rendered = PLACEHOLDER_RE.sub(lambda match: _stringify_xml(resolve_template_path(match.group(1).strip(), variables)), template)
    try:
        ElementTree.fromstring(rendered)
    except ElementTree.ParseError as exc:
        raise PayloadRenderError("PAYLOAD_XML_INVALID", f"Rendered XML не является well-formed: {exc}") from exc
    return rendered


def render_text_template(template: str, variables: dict[str, Any]) -> str:
    return PLACEHOLDER_RE.sub(lambda match: _stringify(resolve_template_path(match.group(1).strip(), variables)), template)


def resolve_template_path(path: str, variables: dict[str, Any]) -> Any:
    normalized = str(path or "").strip()
    if not normalized:
        raise PayloadRenderError("VARIABLE_NOT_FOUND", "Переменная  не найдена.")
    current: Any = variables
    for token in _tokens(normalized):
        try:
            current = _read_token(current, token, normalized)
        except (KeyError, IndexError, TypeError) as exc:
            raise PayloadRenderError("VARIABLE_NOT_FOUND", f"Переменная {normalized} не найдена.") from exc
    return current


def _render_json_step(step: PayloadStepConfig, variables: dict[str, Any]) -> Any:
    if step.json_mode == "table":
        return render_json_fields(step.fields, step.dynamic_entries, variables)
    template = _json_template_object(step.template)
    return render_json_template(template, variables)


def _json_template_object(template: Any) -> Any:
    if isinstance(template, str):
        try:
            return json.loads(template)
        except json.JSONDecodeError as exc:
            raise PayloadRenderError("PAYLOAD_JSON_INVALID", f"JSON template невалиден до рендера: {exc.msg} at line {exc.lineno}, column {exc.colno}.") from exc
    if template is None:
        raise PayloadRenderError("PAYLOAD_TEMPLATE_REQUIRED", "Укажите JSON template или JSON field table.")
    return template


def _template_as_text(template: Any) -> str:
    if template is None:
        return ""
    if isinstance(template, str):
        return template
    return json.dumps(template, ensure_ascii=False, indent=2)


def _render_field_value(field: Any, variables: dict[str, Any]) -> Any:
    source = _field_value(field, "value_source")
    value_type = _field_value(field, "value_type") or "variable"
    return _render_value_by_type(source, value_type, variables)


def _render_value_by_type(source: Any, value_type: str, variables: dict[str, Any]) -> Any:
    if value_type in {"variable", "array", "object"}:
        return resolve_template_path(str(source).strip(), variables)
    if value_type == "template_string":
        return render_text_template(str(source or ""), variables)
    if value_type == "constant_string":
        return "" if source is None else str(source)
    if value_type == "constant_number":
        try:
            numeric = float(str(source).strip())
        except (TypeError, ValueError) as exc:
            raise PayloadRenderError("PAYLOAD_NUMBER_INVALID", f"Значение {source!r} не является числом.") from exc
        return int(numeric) if numeric.is_integer() else numeric
    if value_type == "constant_boolean":
        return str(source).strip().lower() in {"true", "1", "yes", "да"}
    if value_type == "constant_null":
        return None
    raise PayloadRenderError("PAYLOAD_VALUE_TYPE_INVALID", f"Неизвестный тип значения payload: {value_type}.")


def _set_object_path(root: dict[str, Any], path: str, value: Any) -> None:
    parts = _object_path_parts(path)
    current = root
    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            current[part] = {}
            existing = current[part]
        if not isinstance(existing, dict):
            raise PayloadRenderError("PAYLOAD_TARGET_PATH_CONFLICT", f"Путь {path} конфликтует с уже заданным значением {part}.")
        current = existing
    current[parts[-1]] = value


def _ensure_object_path(root: dict[str, Any], path: str) -> dict[str, Any]:
    parts = _object_path_parts(path)
    current = root
    for part in parts:
        existing = current.get(part)
        if existing is None:
            current[part] = {}
            existing = current[part]
        if not isinstance(existing, dict):
            raise PayloadRenderError("PAYLOAD_DYNAMIC_OBJECT_CONFLICT", f"Путь {path} должен быть JSON-объектом.")
        current = existing
    return current


def _object_path_parts(path: str) -> list[str]:
    parts = [item.strip() for item in path.split(".") if item.strip()]
    if not parts:
        raise PayloadRenderError("PAYLOAD_TARGET_PATH_REQUIRED", "JSON target path не может быть пустым.")
    return parts


def _tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    position = 0
    for match in TOKEN_RE.finditer(path):
        if match.start() != position and path[position : match.start()] not in {".", ""}:
            raise PayloadRenderError("VARIABLE_NOT_FOUND", f"Переменная {path} не найдена.")
        if match.group(1) is not None:
            tokens.append(match.group(1))
        else:
            tokens.append(int(match.group(2)))
        position = match.end()
        if position < len(path) and path[position] == ".":
            position += 1
    if position != len(path):
        raise PayloadRenderError("VARIABLE_NOT_FOUND", f"Переменная {path} не найдена.")
    return tokens


def _read_token(current: Any, token: str | int, path: str) -> Any:
    if isinstance(token, int):
        if not isinstance(current, list) or token < 0 or token >= len(current):
            raise IndexError(path)
        return current[token]
    if token == "length" and not (isinstance(current, dict) and token in current):
        if isinstance(current, (list, dict, str)):
            return len(current)
        raise TypeError(path)
    if isinstance(current, dict) and token in current:
        return current[token]
    raise KeyError(path)


def _field_value(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        value = item.get(name)
    else:
        value = getattr(item, name, None)
    return "" if value is None else value


def _placeholder(source: str) -> str:
    value = source.strip()
    if value.startswith("{{"):
        return value
    return f"{{{{{value}}}}}"


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _stringify_xml(value: Any) -> str:
    return xml_escape(_stringify(value), {'"': "&quot;", "'": "&apos;"})


def _truncate_preview(value: Any, warnings: list[str]) -> Any:
    if isinstance(value, list):
        if len(value) > MAX_PREVIEW_ARRAY_ITEMS:
            hidden = len(value) - MAX_PREVIEW_ARRAY_ITEMS
            warnings.append(f"Array has {len(value)} items; preview is truncated")
            return value[:MAX_PREVIEW_ARRAY_ITEMS] + [{"_preview_truncated": hidden}]
        return [_truncate_preview(item, warnings) for item in value]
    if isinstance(value, dict):
        return {key: _truncate_preview(item, warnings) for key, item in value.items()}
    return value
