from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.business_rules.schemas import RuleEvaluationResult
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template

OPERATORS = {"always", "exists", "not_exists", "eq", "ne", "contains", "not_contains", "starts_with", "ends_with", "in", "not_in", "gt", "lt", "ge", "le", "regex", "is_empty", "is_not_empty"}
ACTIONS = {"set_variable", "set_payload", "set_target_system", "set_operation", "set_route", "continue", "stop", "fail", "skip_step", "mark_retry"}


class BusinessRulesEngine:
    def evaluate(self, rule_set: dict[str, Any], context: dict[str, Any]) -> RuleEvaluationResult:
        mode = str(rule_set.get("mode") or "first_match")
        rules = rule_set.get("rules") if isinstance(rule_set.get("rules"), list) else []
        payload = deepcopy(context.get("payload") if isinstance(context.get("payload"), dict) else context.get("request") if isinstance(context.get("request"), dict) else {})
        variables = deepcopy(context.get("variables") if isinstance(context.get("variables"), dict) else {})
        result = RuleEvaluationResult(success=True, payload=payload, variables=variables, trace={"rule_set": rule_set.get("name"), "mode": mode, "rules": [], "actions": []})
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            name = str(rule.get("name") or f"Rule {index + 1}")
            matched = self._match(rule.get("if") or {"operator": "always"}, payload, variables, context)
            result.trace["rules"].append({"name": name, "index": index, "matched": matched})
            if not matched:
                continue
            result.matched_rules.append(name)
            for action in rule.get("then") or []:
                action_result = self._apply_action(action, result, context)
                result.actions_applied.append(action_result)
                result.trace["actions"].append(action_result)
                if result.status in {"failed", "stopped", "retry"}:
                    break
            if mode == "first_match" or result.status in {"failed", "stopped", "retry"}:
                break
        result.success = result.status != "failed"
        return result

    def _match(self, condition: dict[str, Any], payload: dict[str, Any], variables: dict[str, Any], context: dict[str, Any]) -> bool:
        operator = str(condition.get("operator") or condition.get("op") or "eq")
        if operator not in OPERATORS:
            raise ValueError(f"RULE_CONDITION_INVALID: unsupported operator {operator}")
        if operator == "always":
            return True
        scope = _scope(payload, variables, context)
        path = condition.get("path") or condition.get("field")
        left = _resolve_optional(scope, str(path)) if path else condition.get("left")
        if condition.get("value_path"):
            right = _resolve_optional(scope, str(condition["value_path"]))
        else:
            right = render_template(condition.get("value"), scope) if isinstance(condition.get("value"), str) and "{{" in str(condition.get("value")) else condition.get("value")
        if operator == "exists":
            return left is not None
        if operator == "not_exists":
            return left is None
        if operator == "is_empty":
            return _is_empty(left)
        if operator == "is_not_empty":
            return not _is_empty(left)
        if operator == "eq":
            return left == right
        if operator == "ne":
            return left != right
        if operator == "contains":
            return str(right) in str(left or "")
        if operator == "not_contains":
            return str(right) not in str(left or "")
        if operator == "starts_with":
            return str(left or "").startswith(str(right or ""))
        if operator == "ends_with":
            return str(left or "").endswith(str(right or ""))
        if operator == "in":
            return left in (right or [])
        if operator == "not_in":
            return left not in (right or [])
        if operator in {"gt", "lt", "ge", "le"}:
            return _compare(operator, left, right)
        if operator == "regex":
            return re.search(str(right or ""), str(left or "")) is not None
        return False

    def _apply_action(self, action: dict[str, Any], result: RuleEvaluationResult, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(action, dict):
            raise ValueError("RULE_ACTION_INVALID: action must be an object")
        action_name = str(action.get("action") or "").strip()
        if action_name not in ACTIONS:
            raise ValueError(f"RULE_ACTION_INVALID: unsupported action {action_name}")
        scope = _scope(result.payload, result.variables, context)
        value = _action_value(action, scope)
        trace = {"action": action_name, "path": action.get("path"), "value": value}
        if action_name == "set_variable":
            _set_target(result.variables, str(action.get("path") or ""), value, strip_prefixes=("variables.",))
        elif action_name == "set_payload":
            _set_target(result.payload, str(action.get("path") or ""), value, strip_prefixes=("payload.", "request.body."))
        elif action_name == "set_target_system":
            result.target_system = str(value)
        elif action_name == "set_operation":
            result.operation = str(value)
        elif action_name == "set_route":
            result.route = str(value)
        elif action_name == "skip_step":
            result.skip_steps.append(str(value or action.get("step") or ""))
        elif action_name == "stop":
            result.status = "stopped"
        elif action_name == "mark_retry":
            result.status = "retry"
            result.error_code = str(action.get("error_code") or "RULE_MARKED_RETRY")
            result.error_message = str(render_template(action.get("message") or "Retry requested by business rule", scope))
        elif action_name == "fail":
            result.status = "failed"
            result.error_code = str(action.get("error_code") or "BUSINESS_RULE_FAILED")
            result.error_message = str(render_template(action.get("message") or "Business rule failed", scope))
            trace["error_code"] = result.error_code
            trace["message"] = result.error_message
        return trace


def _scope(payload: dict[str, Any], variables: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    merged_variables = {**variables, **{key: value for key, value in context.items() if key not in {"payload", "variables", "request"}}}
    return build_runtime_scope(request_body=payload, variables=merged_variables, context=context)


def _resolve_optional(scope: dict[str, Any], path: str) -> Any:
    try:
        return resolve_path(scope, path)
    except PathResolutionError:
        return None


def _action_value(action: dict[str, Any], scope: dict[str, Any]) -> Any:
    if "value_path" in action:
        return _resolve_optional(scope, str(action["value_path"]))
    value = action.get("value")
    return render_template(value, scope) if isinstance(value, str) else value


def _set_target(target: dict[str, Any], path: str, value: Any, strip_prefixes: tuple[str, ...]) -> None:
    clean = path
    for prefix in strip_prefixes:
        clean = clean.removeprefix(prefix)
    parts = [part for part in clean.split(".") if part]
    if not parts:
        raise ValueError("RULE_ACTION_INVALID: target path is empty")
    current = target
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _is_empty(value: Any) -> bool:
    return value in (None, "", [], {})


def _compare(operator: str, left: Any, right: Any) -> bool:
    try:
        left_number = float(left)
        right_number = float(right)
    except (TypeError, ValueError):
        left_number = str(left)
        right_number = str(right)
    if operator == "gt":
        return left_number > right_number
    if operator == "lt":
        return left_number < right_number
    if operator == "ge":
        return left_number >= right_number
    return left_number <= right_number


engine = BusinessRulesEngine()
