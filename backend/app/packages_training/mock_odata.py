from __future__ import annotations

import re
from typing import Any


def metadata_xml(resources: dict[str, list[dict[str, Any]]], namespace: str = "Training") -> str:
    entity_sets = "\n".join(f'<EntitySet Name="{name}" EntityType="{namespace}.{name}" />' for name in resources)
    entity_types = "\n".join(f'<EntityType Name="{name}"><Key><PropertyRef Name="Ref_Key" /></Key></EntityType>' for name in resources)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="{namespace}" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      {entity_types}
      <EntityContainer Name="StandardOData">
        {entity_sets}
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""


def query_mock_odata(resources: dict[str, list[dict[str, Any]]], resource: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    items = [dict(item) for item in resources.get(resource, []) if isinstance(item, dict)]
    filter_value = str(params.get("$filter") or "").strip()
    if filter_value:
        items = [item for item in items if _matches_filter(item, filter_value)]
    orderby = str(params.get("$orderby") or "").strip()
    if orderby:
        parts = orderby.split()
        field = parts[0]
        reverse = len(parts) > 1 and parts[1].lower() == "desc"
        items.sort(key=lambda item: str(item.get(field, "")), reverse=reverse)
    skip = _to_int(params.get("$skip"), 0)
    top = _to_int(params.get("$top"), len(items))
    items = items[skip: skip + top]
    select = str(params.get("$select") or "").strip()
    if select:
        fields = [field.strip() for field in select.split(",") if field.strip()]
        items = [{field: item.get(field) for field in fields if field in item} for item in items]
    return {
        "@odata.context": "$metadata#" + resource,
        "value": items,
    }


def _matches_filter(item: dict[str, Any], filter_value: str) -> bool:
    parts = [part.strip() for part in re.split(r"\s+and\s+", filter_value, flags=re.IGNORECASE) if part.strip()]
    return all(_matches_condition(item, part) for part in parts)


def _matches_condition(item: dict[str, Any], condition: str) -> bool:
    contains = re.fullmatch(r"contains\(([^,]+),\s*'((?:''|[^'])*)'\)", condition, flags=re.IGNORECASE)
    if contains:
        field, raw = contains.groups()
        return _unquote(raw).lower() in str(item.get(field.strip(), "")).lower()
    match = re.fullmatch(r"([A-Za-zА-Яа-яЁё0-9_]+)\s+(eq|ne|gt|lt|ge|le)\s+(.+)", condition, flags=re.IGNORECASE)
    if not match:
        return False
    field, op, raw_value = match.groups()
    expected = _parse_literal(raw_value.strip())
    actual = item.get(field)
    if op.lower() == "eq":
        return actual == expected
    if op.lower() == "ne":
        return actual != expected
    left = _comparable(actual)
    right = _comparable(expected)
    if op.lower() == "gt":
        return left > right
    if op.lower() == "lt":
        return left < right
    if op.lower() == "ge":
        return left >= right
    if op.lower() == "le":
        return left <= right
    return False


def _parse_literal(value: str) -> Any:
    cast = re.fullmatch(r"cast\((.+),\s*'[^']+'\)", value, flags=re.IGNORECASE)
    if cast:
        return _parse_literal(cast.group(1).strip())
    guid = re.fullmatch(r"guid'((?:''|[^'])*)'", value, flags=re.IGNORECASE)
    if guid:
        return _unquote(guid.group(1))
    dt = re.fullmatch(r"datetime'((?:''|[^'])*)'", value, flags=re.IGNORECASE)
    if dt:
        return _unquote(dt.group(1))
    if value.lower() == "false":
        return False
    if value.lower() == "true":
        return True
    if value.startswith("'") and value.endswith("'"):
        return _unquote(value[1:-1])
    try:
        return int(value)
    except ValueError:
        return value


def _unquote(value: str) -> str:
    return value.replace("''", "'")


def _comparable(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _to_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default
