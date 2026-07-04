from __future__ import annotations

from app.core.errors import BadRequestError
from app.matchers.schemas import MATCHER_MODES, MATCHER_TYPES


def validate_matcher_group(group: dict) -> None:
    mode = group.get("mode", "all")
    if mode not in MATCHER_MODES:
        raise BadRequestError(f"Unsupported matcher mode: {mode}")
    rules = group.get("rules") or []
    if not isinstance(rules, list):
        raise BadRequestError("matcher_group.rules must be a list")
    for rule in rules:
        if not isinstance(rule, dict):
            raise BadRequestError("matcher rule must be an object")
        rule_type = rule.get("type")
        if rule_type not in MATCHER_TYPES:
            raise BadRequestError(f"Unsupported matcher type: {rule_type}")
