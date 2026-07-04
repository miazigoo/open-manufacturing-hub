from __future__ import annotations

from typing import Any


def get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    current = payload
    parts = path.split(".")
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def evaluate_condition(condition: dict[str, Any], payload: dict[str, Any], variables: dict[str, Any]) -> bool:
    field = condition.get("field")
    left = get_path(payload, str(field)) if field else condition.get("value")
    if condition.get("variable"):
        left = variables.get(str(condition["variable"]))
    op = condition.get("op", "eq")
    right = condition.get("equals", condition.get("value"))
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "exists":
        return left is not None
    if op == "contains":
        return str(right) in str(left or "")
    if op == "in":
        return left in (right or [])
    return False


def run_rules(rules: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    output = dict(payload)
    variables: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []
    stopped = False
    failed: str | None = None
    for index, rule in enumerate(rules):
        action = str(rule.get("action", "IF")).upper()
        matched = evaluate_condition(rule.get("if", {}), output, variables) if "if" in rule else True
        trace.append({"index": index, "action": action, "matched": matched})
        if action == "IF" and not matched:
            continue
        if action == "SWITCH":
            value = get_path(output, str(rule.get("field", "")))
            case = (rule.get("cases") or {}).get(str(value), rule.get("default"))
            if isinstance(case, dict) and "set" in case:
                set_path(output, str(case["set"]), case.get("value"))
        elif action == "SET VARIABLE":
            variables[str(rule.get("name"))] = rule.get("value")
        elif action == "SET":
            set_path(output, str(rule.get("field")), rule.get("value"))
        elif action == "STOP" and matched:
            stopped = True
            break
        elif action == "FAIL" and matched:
            failed = str(rule.get("message") or "Business rule failed")
            break
    return {"payload": output, "variables": variables, "trace": trace, "stopped": stopped, "failed": failed}
