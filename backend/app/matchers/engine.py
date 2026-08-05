from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from app.matchers.validators import validate_matcher_group


def evaluate_matcher_group(group: dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]:
    if not group:
        return {"matched": True, "trace": []}
    validate_matcher_group(group)
    mode = group.get("mode", "all")
    traces = [_evaluate_item(item, context) for item in group.get("rules") or []]
    if not traces:
        matched = True
    elif mode == "all":
        matched = all(item["matched"] for item in traces)
    elif mode == "any":
        matched = any(item["matched"] for item in traces)
    else:
        matched = not any(item["matched"] for item in traces)
    return {"matched": matched, "trace": traces}


def _evaluate_item(item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if item.get("group") is not None:
        subgroup = item.get("group") or {}
        result = evaluate_matcher_group(subgroup, context)
        return {
            "rule": "group",
            "path": None,
            "actual": None,
            "expected": None,
            "matched": result["matched"],
            "message": None,
            "mode": subgroup.get("mode", "all"),
            "trace": result["trace"],
        }
    return _evaluate_rule(item, context)


def _evaluate_rule(rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    rule_type = rule.get("type")
    path = rule.get("path")
    expected = rule.get("value", rule.get("values", rule.get("pattern")))
    actual = None
    matched = False
    message = None
    try:
        if rule_type == "always":
            matched = True
        elif rule_type.startswith("body_path_"):
            actual = _get_path(context.get("body") or {}, str(path or ""))
            matched = _match_path_rule(rule_type, actual, rule)
        elif rule_type == "header_equals":
            actual = _case_get(context.get("headers") or {}, str(path or ""))
            matched = str(actual) == str(rule.get("value"))
        elif rule_type == "query_equals":
            actual = _case_get(context.get("query") or {}, str(path or ""))
            matched = str(actual) == str(rule.get("value"))
        elif rule_type.startswith("xml_path_"):
            actual = _xml_path(context.get("xml") or context.get("text") or "", str(path or ""))
            matched = actual is not None if rule_type == "xml_path_exists" else str(actual) == str(rule.get("value"))
        elif rule_type == "xml_contains":
            actual = context.get("xml") or context.get("text") or ""
            matched = str(rule.get("value") or "") in str(actual)
        elif rule_type == "text_contains":
            actual = _text(context)
            matched = str(rule.get("value") or "") in actual
        elif rule_type == "regex":
            actual = _text(context)
            matched = re.search(str(rule.get("pattern") or ""), actual) is not None
    except Exception as exc:  # defensive trace, never break route selection
        message = str(exc)
        matched = False
    return {"rule": str(rule_type), "path": path, "actual": actual, "expected": expected, "matched": matched, "message": message}


def _match_path_rule(rule_type: str, actual: Any, rule: dict[str, Any]) -> bool:
    if rule_type == "body_path_exists":
        return actual is not None
    if rule_type == "body_path_equals":
        return actual == rule.get("value")
    if rule_type == "body_path_not_equals":
        return actual != rule.get("value")
    if rule_type == "body_path_contains":
        return str(rule.get("value") or "") in str(actual or "")
    if rule_type == "body_path_not_contains":
        return str(rule.get("value") or "") not in str(actual or "")
    if rule_type == "body_path_in":
        return actual in (rule.get("values") or [])
    if rule_type == "body_path_not_in":
        return actual not in (rule.get("values") or [])
    if rule_type == "body_path_starts_with":
        return str(actual or "").startswith(str(rule.get("value") or ""))
    if rule_type == "body_path_ends_with":
        return str(actual or "").endswith(str(rule.get("value") or ""))
    if rule_type == "body_path_regex":
        return re.search(str(rule.get("pattern") or rule.get("value") or ""), str(actual or "")) is not None
    if rule_type in {"body_path_gt", "body_path_lt", "body_path_ge", "body_path_le"}:
        return _numeric_compare(rule_type, actual, rule.get("value"))
    return False


def _numeric_compare(rule_type: str, actual: Any, expected: Any) -> bool:
    try:
        left = float(actual)
        right = float(expected)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"numeric comparison requires numbers, got {actual!r} and {expected!r}") from exc
    if rule_type == "body_path_gt":
        return left > right
    if rule_type == "body_path_lt":
        return left < right
    if rule_type == "body_path_ge":
        return left >= right
    return left <= right


def _get_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split(".") if path else []:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def _case_get(values: dict[str, Any], key: str) -> Any:
    if key in values:
        return values[key]
    lowered = key.lower()
    for item_key, item_value in values.items():
        if str(item_key).lower() == lowered:
            return item_value
    return None


def _xml_path(xml: str, path: str) -> str | None:
    if not xml.strip() or not path:
        return None
    root = ET.fromstring(xml)
    current = root
    parts = path.split(".")
    if parts and _strip_ns(current.tag) == parts[0]:
        parts = parts[1:]
    for part in parts:
        next_node = next((child for child in list(current) if _strip_ns(child.tag) == part), None)
        if next_node is None:
            return None
        current = next_node
    return (current.text or "").strip()


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(context: dict[str, Any]) -> str:
    if context.get("text") is not None:
        return str(context["text"])
    if context.get("xml") is not None:
        return str(context["xml"])
    return str(context.get("body") or "")
