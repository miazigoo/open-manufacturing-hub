"""Routing rules for marking code pools.

Rules let an operator split an incoming 1C code pool into segments without any
programming: each rule has a matcher group (evaluated per code against its GS1
fields and document context) and a list of targets (laser file, local outbox
name template, HTTP forward). The first matching rule by priority wins; codes
that match nothing go to the default segment, which keeps the classic behavior.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.matchers.engine import evaluate_matcher_group
from app.matchers.validators import validate_matcher_group
from app.marking_code_pools.gs1 import GS, parse_code
from app.marking_code_pools.models import MarkingCodePoolRoutingRule
from app.marking_code_pools.schemas import (
    MarkingCodePoolRoutingRuleCreate,
    MarkingCodePoolRoutingRulePatch,
    RoutingRuleTestCodeResult,
    RoutingRuleTestRequest,
    RoutingRuleTestResponse,
)

DEFAULT_SEGMENT = "default"


async def list_rules(session: AsyncSession, *, enabled_only: bool = False) -> list[MarkingCodePoolRoutingRule]:
    query = select(MarkingCodePoolRoutingRule).order_by(MarkingCodePoolRoutingRule.priority, MarkingCodePoolRoutingRule.created_at)
    if enabled_only:
        query = query.where(MarkingCodePoolRoutingRule.enabled.is_(True))
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_rule_or_404(session: AsyncSession, rule_id: UUID) -> MarkingCodePoolRoutingRule:
    rule = await session.get(MarkingCodePoolRoutingRule, rule_id)
    if rule is None:
        raise NotFoundError("Routing rule not found")
    return rule


async def create_rule(session: AsyncSession, payload: MarkingCodePoolRoutingRuleCreate) -> MarkingCodePoolRoutingRule:
    if payload.match_json:
        validate_matcher_group(payload.match_json)
    rule = MarkingCodePoolRoutingRule(
        name=payload.name.strip(),
        enabled=payload.enabled,
        priority=payload.priority,
        match_json=payload.match_json,
        targets_json=[target.model_dump() for target in payload.targets_json],
    )
    session.add(rule)
    await session.flush()
    return rule


async def patch_rule(session: AsyncSession, rule_id: UUID, patch: MarkingCodePoolRoutingRulePatch) -> MarkingCodePoolRoutingRule:
    rule = await get_rule_or_404(session, rule_id)
    if patch.name is not None:
        rule.name = patch.name.strip()
    if patch.enabled is not None:
        rule.enabled = patch.enabled
    if patch.priority is not None:
        rule.priority = patch.priority
    if patch.match_json is not None:
        if patch.match_json:
            validate_matcher_group(patch.match_json)
        rule.match_json = patch.match_json
    if patch.targets_json is not None:
        rule.targets_json = [target.model_dump() for target in patch.targets_json]
    await session.flush()
    return rule


async def delete_rule(session: AsyncSession, rule_id: UUID) -> None:
    rule = await get_rule_or_404(session, rule_id)
    await session.delete(rule)
    await session.flush()


def code_context(
    code: str,
    *,
    order_number: str,
    source_document_id: str | None,
    source_system: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = parse_code(code)
    return {
        "body": {
            **parsed,
            "order_number": order_number or "",
            "source_document_id": source_document_id,
            "source_system": source_system,
            "metadata": metadata or {},
        }
    }


def match_code(rules: list[MarkingCodePoolRoutingRule], context: dict[str, Any]) -> MarkingCodePoolRoutingRule | None:
    for rule in rules:
        if evaluate_matcher_group(rule.match_json, context)["matched"]:
            return rule
    return None


def route_codes(
    rules: list[MarkingCodePoolRoutingRule],
    codes: list[str],
    *,
    order_number: str,
    source_document_id: str | None,
    source_system: str,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Split codes into ordered segments: {key, rule, codes}. Default segment is last."""
    segments: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for code in codes:
        rule = match_code(rules, code_context(
            code,
            order_number=order_number,
            source_document_id=source_document_id,
            source_system=source_system,
            metadata=metadata,
        ))
        key = f"rule:{rule.name}" if rule is not None else DEFAULT_SEGMENT
        segment = by_key.get(key)
        if segment is None:
            segment = {"key": key, "rule": rule, "codes": []}
            by_key[key] = segment
            segments.append(segment)
        segment["codes"].append(code)
    segments.sort(key=lambda item: item["key"] == DEFAULT_SEGMENT)
    return segments


async def test_rules(session: AsyncSession, request: RoutingRuleTestRequest) -> RoutingRuleTestResponse:
    from app.marking_code_pools import service  # local import to avoid a module cycle

    if request.full_codes_base64 is not None:
        codes = service._normalize_base64_full_codes(request.full_codes_base64)
    else:
        codes = service._normalize_codes(request.codes or [], request.gs_marker)
    rules = await list_rules(session, enabled_only=True)
    results: list[RoutingRuleTestCodeResult] = []
    for code in codes:
        parsed = parse_code(code)
        rule = match_code(rules, code_context(
            code,
            order_number=request.order_number,
            source_document_id=request.source_document_id,
            source_system=request.source_system,
        ))
        results.append(RoutingRuleTestCodeResult(
            code_preview=code.replace(GS, "<GS>")[:120],
            gtin=parsed["gtin"],
            serial=parsed["serial"],
            segment=f"rule:{rule.name}" if rule is not None else DEFAULT_SEGMENT,
            rule_id=rule.id if rule is not None else None,
            rule_name=rule.name if rule is not None else None,
            targets=list(rule.targets_json) if rule is not None else [],
        ))
    matched = sum(1 for item in results if item.rule_id is not None)
    return RoutingRuleTestResponse(
        total_codes=len(results),
        matched_codes=matched,
        default_codes=len(results) - matched,
        results=results,
    )
