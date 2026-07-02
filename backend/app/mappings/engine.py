from __future__ import annotations

import copy
import re
from typing import Any

from app.core.errors import BadRequestError

_PATH_RE = re.compile(r"^[A-Za-z0-9_.$-]+$")


class MappingEngine:
    def validate(self, rules: list[dict[str, Any]], sample_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        targets: set[str] = set()
        for index, rule in enumerate(rules):
            prefix = f"rule[{index}]"
            target = rule.get("target")
            if not isinstance(target, str) or not target:
                errors.append(f"{prefix}: target is required")
            elif target in targets:
                warnings.append(f"{prefix}: target {target} is assigned more than once")
            else:
                targets.add(target)
            has_source = "source" in rule
            has_constant = "constant" in rule
            has_expression = "expression" in rule
            if sum([has_source, has_constant, has_expression]) != 1:
                errors.append(f"{prefix}: exactly one of source, constant or expression is required")
            if has_source and not isinstance(rule.get("source"), str):
                errors.append(f"{prefix}: source must be a string path")
            if has_expression and not isinstance(rule.get("expression"), str):
                errors.append(f"{prefix}: expression must be a string")
            if rule.get("type") == "array" and not isinstance(rule.get("items", []), list):
                errors.append(f"{prefix}: array rule items must be a list")
        preview = None
        if not errors and sample_payload is not None:
            try:
                preview = self.apply(sample_payload, rules)
            except BadRequestError as exc:
                errors.append(str(exc))
        return {"valid": not errors, "errors": errors, "warnings": warnings, "preview": preview}

    def apply(self, payload: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for rule in rules:
            target = rule["target"]
            if rule.get("type") == "array":
                source_value = self._value_for_rule(payload, rule)
                if source_value is None:
                    mapped_value = []
                elif not isinstance(source_value, list):
                    raise BadRequestError(f"Mapping source {rule.get('source')} is not an array")
                else:
                    item_rules = rule.get("items", [])
                    mapped_value = [self.apply(item if isinstance(item, dict) else {"value": item}, item_rules) for item in source_value]
            else:
                mapped_value = self._value_for_rule(payload, rule)
            set_path(output, target, mapped_value)
        return output

    def _value_for_rule(self, payload: dict[str, Any], rule: dict[str, Any]) -> Any:
        if "constant" in rule:
            return copy.deepcopy(rule["constant"])
        if "expression" in rule:
            return evaluate_expression(rule["expression"], payload)
        value = get_path(payload, rule["source"])
        transform = rule.get("transform")
        if transform is None:
            return copy.deepcopy(value)
        return apply_transform(value, transform)


def get_path(payload: dict[str, Any], path: str) -> Any:
    clean_path = path.removeprefix("$.").removeprefix(".")
    if not clean_path:
        return payload
    value: Any = payload
    for part in clean_path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            index = int(part)
            value = value[index] if 0 <= index < len(value) else None
        else:
            return None
    return value


def set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    if not _PATH_RE.match(path):
        raise BadRequestError(f"Invalid target path: {path}")
    clean_path = path.removeprefix("$.").removeprefix(".")
    parts = clean_path.split(".")
    cursor = payload
    for part in parts[:-1]:
        existing = cursor.get(part)
        if not isinstance(existing, dict):
            existing = {}
            cursor[part] = existing
        cursor = existing
    cursor[parts[-1]] = value


def apply_transform(value: Any, transform: str) -> Any:
    if transform == "str":
        return None if value is None else str(value)
    if transform == "int":
        return None if value is None else int(value)
    if transform == "float":
        return None if value is None else float(value)
    if transform == "upper":
        return None if value is None else str(value).upper()
    if transform == "lower":
        return None if value is None else str(value).lower()
    raise BadRequestError(f"Unsupported transform: {transform}")


def evaluate_expression(expression: str, payload: dict[str, Any]) -> Any:
    expression = expression.strip()
    for function_name in ["upper", "lower", "str", "int", "float"]:
        prefix = f"{function_name}("
        if expression.startswith(prefix) and expression.endswith(")"):
            arg = expression[len(prefix) : -1]
            return apply_transform(resolve_token(arg, payload), function_name)
    if expression.startswith("concat(") and expression.endswith(")"):
        args = split_args(expression[len("concat(") : -1])
        return "".join("" if (value := resolve_token(arg, payload)) is None else str(value) for arg in args)
    raise BadRequestError(f"Unsupported expression: {expression}")


def split_args(value: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in value:
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        if char == "," and quote is None:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        args.append("".join(current).strip())
    return args


def resolve_token(token: str, payload: dict[str, Any]) -> Any:
    token = token.strip()
    if (token.startswith("'") and token.endswith("'")) or (token.startswith('"') and token.endswith('"')):
        return token[1:-1]
    return get_path(payload, token)
