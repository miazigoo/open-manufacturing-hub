from __future__ import annotations

import re
from typing import Any

from app.core.errors import BadRequestError
from app.data_contracts.validator import field_map
from app.mapping_center.renderer import TEMPLATE_RE, MISSING, get_path, render_mapping
from app.mapping_center.schemas import MappingIssue, MappingValidationResponse

ALLOWED_SOURCE_TYPES = {"variable", "constant", "template", "dynamic_object_entry"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,179}$")


def normalize_mapping_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if "name" in normalized and isinstance(normalized["name"], str):
        normalized["name"] = normalized["name"].strip()
    if "code" in normalized and isinstance(normalized["code"], str):
        normalized["code"] = slugify(normalized["code"])
    for key in ["description", "package_id"]:
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalized[key].strip() or None
    return normalized


def validate_profile_data(data: dict[str, Any], *, partial: bool = False) -> None:
    if not partial or "code" in data:
        code = str(data.get("code") or "").strip()
        if not SLUG_RE.match(code):
            raise BadRequestError("Code mapping profile должен начинаться с латинской буквы/цифры и содержать только a-z, 0-9, '.', '_' или '-'.")
    if not partial or "mapping_json" in data:
        mapping = data.get("mapping_json")
        if not isinstance(mapping, dict):
            raise BadRequestError("mapping_json должен быть JSON object.")
        issues = validate_mapping_shape(mapping)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            raise BadRequestError("; ".join(issue.message for issue in errors))
    source_context = data.get("source_context_json")
    if source_context is not None and not isinstance(source_context, dict):
        raise BadRequestError("source_context_json должен быть JSON object.")


def validate_mapping(mapping_json: dict[str, Any], source_context: dict[str, Any] | None, target_contract_schema: dict[str, Any] | None) -> MappingValidationResponse:
    issues = validate_mapping_shape(mapping_json)
    contract_fields = field_map(target_contract_schema)
    source = source_context or {}
    target_paths: set[str] = set()

    for field in mapping_json.get("fields", []) if isinstance(mapping_json.get("fields", []), list) else []:
        if not isinstance(field, dict):
            continue
        target_path = str(field.get("target_path") or "").strip()
        source_type = str(field.get("source_type") or "variable")
        if target_path:
            if target_path in target_paths and not field.get("allow_duplicate"):
                issues.append(_issue("MAPPING_DUPLICATE_TARGET_PATH", f"Целевое поле {target_path} заполнено несколькими правилами.", target_path))
            target_paths.add(target_path)
            if contract_fields and target_path not in contract_fields:
                issues.append(_issue("MAPPING_TARGET_PATH_NOT_IN_CONTRACT", f"Поле {target_path} отсутствует в целевом контракте.", target_path))
        if source_type == "variable":
            _validate_source_exists(str(field.get("source") or ""), source, issues)
            _validate_type_compatibility(field, source, contract_fields, issues)
        elif source_type == "template":
            for path in TEMPLATE_RE.findall(str(field.get("source") or field.get("value") or "")):
                _validate_source_exists(path.strip(), source, issues)
        elif source_type == "constant":
            _validate_constant_type(field, contract_fields, issues)
        elif source_type == "dynamic_object_entry":
            _validate_dynamic_entry({"object_path": target_path, **field}, source, contract_fields, issues)

    dynamic_entries = mapping_json.get("dynamic_entries", []) if isinstance(mapping_json, dict) else []
    if isinstance(dynamic_entries, list):
        for entry in dynamic_entries:
            if isinstance(entry, dict):
                _validate_dynamic_entry(entry, source, contract_fields, issues)

    for path, contract_field in contract_fields.items():
        if contract_field.required and path not in target_paths and not _has_default(contract_field):
            issues.append(_issue("MAPPING_REQUIRED_FIELD_MISSING", f"Обязательное поле {path} не заполнено.", path))

    rendered = render_mapping(mapping_json, source, target_contract_schema)
    issues.extend(rendered.errors)
    deduped = _dedupe(issues)
    errors = [issue for issue in deduped if issue.severity == "error"]
    warnings = [issue for issue in deduped if issue.severity == "warning"]
    return MappingValidationResponse(valid=not errors, errors=errors, warnings=warnings)


def validate_mapping_shape(mapping_json: dict[str, Any]) -> list[MappingIssue]:
    issues: list[MappingIssue] = []
    if not isinstance(mapping_json, dict):
        return [_issue("MAPPING_INVALID_FORMAT", "mapping_json должен быть object.")]
    if int(mapping_json.get("version") or 1) != 1:
        issues.append(_issue("MAPPING_UNSUPPORTED_VERSION", "Поддерживается только mapping_json.version = 1."))
    fields = mapping_json.get("fields", [])
    if not isinstance(fields, list):
        issues.append(_issue("MAPPING_INVALID_FORMAT", "mapping_json.fields должен быть массивом."))
    else:
        for field in fields:
            if not isinstance(field, dict):
                issues.append(_issue("MAPPING_INVALID_FORMAT", "Правило fields должно быть object."))
                continue
            if not str(field.get("target_path") or "").strip():
                issues.append(_issue("MAPPING_INVALID_FORMAT", "Правило fields должно иметь target_path."))
            source_type = str(field.get("source_type") or "variable")
            if source_type not in ALLOWED_SOURCE_TYPES:
                issues.append(_issue("MAPPING_UNSUPPORTED_SOURCE_TYPE", f"source_type {source_type} не поддерживается.", str(field.get("target_path") or "")))
            if source_type in {"variable", "template"} and not str(field.get("source") or "").strip():
                issues.append(_issue("MAPPING_INVALID_FORMAT", "Для variable/template укажите source.", str(field.get("target_path") or "")))
    dynamic_entries = mapping_json.get("dynamic_entries", [])
    if not isinstance(dynamic_entries, list):
        issues.append(_issue("MAPPING_INVALID_FORMAT", "mapping_json.dynamic_entries должен быть массивом."))
    else:
        for entry in dynamic_entries:
            if not isinstance(entry, dict):
                issues.append(_issue("MAPPING_INVALID_FORMAT", "dynamic_entries item должен быть object."))
                continue
            if not entry.get("object_path") or not entry.get("key_source") or not entry.get("value_source"):
                issues.append(_issue("MAPPING_INVALID_FORMAT", "dynamic entry должен иметь object_path, key_source и value_source."))
    return issues


def _validate_source_exists(path: str, source: dict[str, Any], issues: list[MappingIssue]) -> None:
    if not path:
        return
    if get_path(source, path) is MISSING:
        issues.append(_issue("MAPPING_SOURCE_NOT_FOUND", f"Переменная {path} не найдена.", path))


def _validate_type_compatibility(field: dict[str, Any], source: dict[str, Any], contract_fields: dict[str, Any], issues: list[MappingIssue]) -> None:
    target_path = str(field.get("target_path") or "")
    contract_field = contract_fields.get(target_path)
    if contract_field is None:
        return
    value = get_path(source, str(field.get("source") or ""))
    if value is MISSING:
        return
    _check_type(contract_field.type, value, target_path, issues)


def _validate_constant_type(field: dict[str, Any], contract_fields: dict[str, Any], issues: list[MappingIssue]) -> None:
    target_path = str(field.get("target_path") or "")
    contract_field = contract_fields.get(target_path)
    if contract_field is None:
        return
    _check_type(contract_field.type, field.get("value"), target_path, issues)


def _validate_dynamic_entry(entry: dict[str, Any], source: dict[str, Any], contract_fields: dict[str, Any], issues: list[MappingIssue]) -> None:
    object_path = str(entry.get("object_path") or "").strip()
    key_source = str(entry.get("key_source") or "").strip()
    value_source = str(entry.get("value_source") or "").strip()
    _validate_source_exists(key_source, source, issues)
    _validate_source_exists(value_source, source, issues)
    if contract_fields and object_path not in contract_fields:
        issues.append(_issue("MAPPING_TARGET_PATH_NOT_IN_CONTRACT", f"Объект {object_path} отсутствует в целевом контракте.", object_path, severity="warning"))


def _check_type(expected: str, value: Any, path: str, issues: list[MappingIssue]) -> None:
    if expected in {"raw", "date", "datetime", "guid"}:
        if expected in {"date", "datetime", "guid"} and value is not None and not isinstance(value, str):
            issues.append(_issue("MAPPING_TYPE_MISMATCH", f"Поле {path} ожидает {expected}, но получает {type_name(value)}.", path))
        return
    checks = {
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }
    if expected in checks and not checks[expected]:
        issues.append(_issue("MAPPING_TYPE_MISMATCH", f"Поле {path} ожидает {expected}, но получает {type_name(value)}.", path))


def _has_default(contract_field: Any) -> bool:
    return getattr(contract_field, "default", None) is not None


def type_name(value: Any) -> str:
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


def slugify(value: str) -> str:
    slug = value.strip().lower().replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_.-]+", "_", slug)
    return slug.strip("_.-") or "mapping_profile"


def _issue(code: str, message: str, path: str | None = None, severity: str = "error") -> MappingIssue:
    return MappingIssue(error_code=code, message=message, path=path, severity=severity)  # type: ignore[arg-type]


def _dedupe(issues: list[MappingIssue]) -> list[MappingIssue]:
    seen: set[tuple[str, str, str | None, str]] = set()
    result: list[MappingIssue] = []
    for issue in issues:
        key = (issue.error_code, issue.message, issue.path, issue.severity)
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result
