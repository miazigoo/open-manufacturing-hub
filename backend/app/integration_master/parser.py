from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any

from app.core.errors import BadRequestError
from app.integration_master.schemas import InputContractField, InputMode
from app.xml_bridge.parser import XMLBridgeError, reject_unsafe_xml

MAX_SAMPLE_SIZE = 256 * 1024


def parse_input(input_mode: InputMode, sample: Any) -> dict[str, Any]:
    _ensure_not_empty(sample)
    _ensure_size(sample)
    if input_mode == "json":
        return _parse_json(sample)
    if input_mode == "xml":
        return _parse_xml(sample)
    return _parse_raw_text(sample)


def _parse_json(sample: Any) -> dict[str, Any]:
    if isinstance(sample, str):
        try:
            normalized = json.loads(sample)
        except json.JSONDecodeError as exc:
            raise BadRequestError(f"JSON не удалось разобрать. Проверьте кавычки, запятые и скобки. Строка {exc.lineno}, колонка {exc.colno}: {exc.msg}") from exc
    else:
        normalized = sample
    if not isinstance(normalized, (dict, list)):
        raise BadRequestError("JSON sample должен быть объектом или массивом.")
    fields: list[InputContractField] = []
    _walk_json(normalized, "request.body", fields)
    return {"normalized_sample": normalized, "fields": fields, "warnings": []}


def _walk_json(value: Any, path: str, fields: list[InputContractField]) -> None:
    if isinstance(value, dict):
        if not value and path != "request.body":
            fields.append(_field(_name_from_path(path), path, "object", {}))
        for key, child in value.items():
            _walk_json(child, f"{path}.{key}", fields)
        return
    if isinstance(value, list):
        fields.append(_field(_name_from_path(path), f"{path}[]", "array", _compact_example(value)))
        if value:
            first = value[0]
            if isinstance(first, dict):
                for key, child in first.items():
                    _walk_json(child, f"{path}[0].{key}", fields)
            elif isinstance(first, list):
                _walk_json(first, f"{path}[0]", fields)
            else:
                fields.append(_field(_name_from_path(path), f"{path}[0]", _infer_json_type(first), first))
        return
    fields.append(_field(_name_from_path(path), path, _infer_json_type(value), value))


def _parse_xml(sample: Any) -> dict[str, Any]:
    text = sample if isinstance(sample, str) else str(sample)
    try:
        reject_unsafe_xml(text)
        root = ET.fromstring(text)
    except XMLBridgeError as exc:
        raise BadRequestError(str(exc)) from exc
    except ET.ParseError as exc:
        position = getattr(exc, "position", None)
        if position:
            raise BadRequestError(f"XML не удалось разобрать. Строка {position[0]}, колонка {position[1]}: {exc}") from exc
        raise BadRequestError(f"XML не удалось разобрать: {exc}") from exc
    fields: list[InputContractField] = []
    _walk_xml(root, f"/{_strip_namespace(root.tag)}", fields)
    return {"normalized_sample": text, "fields": fields, "warnings": []}


def _walk_xml(element: ET.Element, path: str, fields: list[InputContractField]) -> None:
    children = list(element)
    text = (element.text or "").strip()
    if not children:
        fields.append(
            InputContractField(
                name=_strip_namespace(element.tag),
                path=f"xml.{path}",
                display_path=path,
                type=_infer_text_type(text),
                required=True,
                example=text,
                description=None,
            )
        )
        return
    for child in children:
        _walk_xml(child, f"{path}/{_strip_namespace(child.tag)}", fields)


def _parse_raw_text(sample: Any) -> dict[str, Any]:
    text = sample if isinstance(sample, str) else str(sample)
    fields = [InputContractField(name="raw_text", path="request.raw_text", display_path="request.raw_text", type="string", required=True, example=_compact_text(text), description="Полное тело входящего запроса")]
    for key, value in _parse_key_values(text).items():
        fields.append(InputContractField(name=key, path=f"request.raw_text.{key}", display_path=f"{key}=...", type=_infer_text_type(value), required=True, example=value, description="Распознано из key=value raw text"))
    return {"normalized_sample": text, "fields": fields, "warnings": []}


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in re.split(r"[;\n&]", text):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip()
        value = value.strip()
        if re.fullmatch(r"[A-Za-zА-Яа-я0-9_.-]{1,80}", key) and value:
            result[key] = value
    return result


def _field(name: str, path: str, field_type: str, example: Any) -> InputContractField:
    return InputContractField(name=name, path=path, display_path=path, type=field_type, required=True, example=example, description=None)


def _name_from_path(path: str) -> str:
    clean = path.replace("[]", "").replace("[0]", "")
    return clean.split(".")[-1]


def _infer_json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, str):
        return "string"
    return "string"


def _infer_text_type(value: str) -> str:
    stripped = value.strip()
    if stripped == "":
        return "string"
    if re.fullmatch(r"-?\d+(\.\d+)?", stripped):
        return "number"
    if stripped.lower() in {"true", "false"}:
        return "boolean"
    return "string"


def _compact_example(value: Any) -> Any:
    if isinstance(value, list):
        return value[:1]
    return value


def _compact_text(value: str) -> str:
    return value if len(value) <= 160 else f"{value[:160]}..."


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _ensure_not_empty(sample: Any) -> None:
    if sample is None or (isinstance(sample, str) and not sample.strip()):
        raise BadRequestError("Вставьте пример запроса, который будет приходить в OMH.")


def _ensure_size(sample: Any) -> None:
    if isinstance(sample, str):
        size = len(sample.encode("utf-8"))
    else:
        size = len(json.dumps(sample, ensure_ascii=False).encode("utf-8"))
    if size > MAX_SAMPLE_SIZE:
        raise BadRequestError("Пример входящего запроса слишком большой. Максимум 256 KB.")
