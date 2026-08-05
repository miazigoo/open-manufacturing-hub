from __future__ import annotations

from app.core.errors import BadRequestError
from app.matchers.schemas import MATCHER_MODES, MATCHER_TYPES, MAX_GROUP_DEPTH


def validate_matcher_group(group: dict, _depth: int = 1) -> None:
    if _depth > MAX_GROUP_DEPTH:
        raise BadRequestError(f"Matcher groups can be nested at most {MAX_GROUP_DEPTH} levels deep")
    mode = group.get("mode", "all")
    if mode not in MATCHER_MODES:
        raise BadRequestError(f"Unsupported matcher mode: {mode}")
    rules = group.get("rules") or []
    if not isinstance(rules, list):
        raise BadRequestError("matcher_group.rules must be a list")
    for rule in rules:
        if not isinstance(rule, dict):
            raise BadRequestError("matcher rule must be an object")
        if rule.get("group") is not None:
            subgroup = rule.get("group")
            if not isinstance(subgroup, dict):
                raise BadRequestError("matcher subgroup must be an object")
            validate_matcher_group(subgroup, _depth + 1)
            continue
        rule_type = rule.get("type")
        if rule_type not in MATCHER_TYPES:
            raise BadRequestError(f"Unsupported matcher type: {rule_type}")
