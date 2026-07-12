from __future__ import annotations

import re
from typing import Any

from app.core.errors import BadRequestError
from app.data_contracts.schemas import DataContractField

ALLOWED_CONTRACT_KINDS = {"input", "output", "operation_request", "operation_response", "intermediate"}
ALLOWED_OWNER_TYPES = {"operation_profile", "integration_pattern", "package"}
ALLOWED_FIELD_TYPES = {"string", "number", "boolean", "null", "object", "array", "date", "datetime", "guid", "raw"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,179}$")
PATH_RE = re.compile(r"^[A-Za-z0-9_А-Яа-яёЁ.$\[\]-]+$")


def normalize_contract_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if "name" in normalized and isinstance(normalized["name"], str):
        normalized["name"] = normalized["name"].strip()
    if "code" in normalized and isinstance(normalized["code"], str):
        normalized["code"] = slugify(normalized["code"])
    for key in ["owner_type", "description"]:
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalized[key].strip() or None
    return normalized


def validate_contract_data(data: dict[str, Any], *, partial: bool = False) -> None:
    if not partial or "code" in data:
        code = str(data.get("code") or "").strip()
        if not SLUG_RE.match(code):
            raise BadRequestError("Code контракта должен начинаться с латинской буквы/цифры и содержать только a-z, 0-9, '.', '_' или '-'.")
    if (not partial or "kind" in data) and data.get("kind") not in ALLOWED_CONTRACT_KINDS:
        raise BadRequestError("Неподдерживаемый kind контракта данных.")
    owner_type = data.get("owner_type")
    if owner_type is not None and owner_type not in ALLOWED_OWNER_TYPES:
        raise BadRequestError("owner_type должен быть operation_profile, integration_pattern или package.")
    if not partial or "schema_json" in data:
        validate_contract_schema(data.get("schema_json"))


def validate_contract_schema(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise BadRequestError("schema_json должен быть JSON object.")
    if schema.get("type", "object") != "object":
        raise BadRequestError("schema_json.type должен быть object.")
    fields = schema.get("fields", [])
    if not isinstance(fields, list):
        raise BadRequestError("schema_json.fields должен быть массивом полей.")
    seen: set[str] = set()
    for raw in fields:
        if not isinstance(raw, dict):
            raise BadRequestError("Каждое поле контракта должно быть JSON object.")
        path = str(raw.get("path") or "").strip()
        field_type = str(raw.get("type") or "raw").strip()
        if not path:
            raise BadRequestError("Поле контракта должно иметь path.")
        if not PATH_RE.match(path):
            raise BadRequestError(f"Path поля {path} содержит неподдерживаемые символы.")
        if path in seen:
            raise BadRequestError(f"Поле контракта {path} указано дважды.")
        if field_type not in ALLOWED_FIELD_TYPES:
            raise BadRequestError(f"Поле {path} имеет неподдерживаемый type {field_type}.")
        seen.add(path)


def extract_contract_fields(schema: dict[str, Any] | None) -> list[DataContractField]:
    if not isinstance(schema, dict):
        return []
    result: list[DataContractField] = []
    for raw in schema.get("fields", []):
        if isinstance(raw, dict):
            result.append(DataContractField.model_validate(raw))
    return result


def field_map(schema: dict[str, Any] | None) -> dict[str, DataContractField]:
    return {field.path: field for field in extract_contract_fields(schema)}


def slugify(value: str) -> str:
    slug = value.strip().lower().replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_.-]+", "_", slug)
    return slug.strip("_.-") or "data_contract"
