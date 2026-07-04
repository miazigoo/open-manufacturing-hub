from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import repository
from app.business_rules.engine import engine
from app.business_rules.presets import SMART_ROUTER_RULE_SET
from app.business_rules.schemas import BusinessRuleSetCreate, BusinessRuleSetPatch, RuleEvaluationResult
from app.core.errors import BadRequestError


async def list_rule_sets(session: AsyncSession, scope: str | None = None, enabled: bool | None = None):
    return await repository.list_rule_sets(session, scope=scope, enabled=enabled)


async def create_rule_set(session: AsyncSession, request: BusinessRuleSetCreate):
    return await repository.upsert_rule_set(session, request)


async def get_rule_set(session: AsyncSession, rule_set_id: UUID):
    return await repository.get_rule_set_or_404(session, rule_set_id)


async def patch_rule_set(session: AsyncSession, rule_set_id: UUID, request: BusinessRuleSetPatch):
    return await repository.patch_rule_set(session, rule_set_id, request)


async def evaluate_rule_set(session: AsyncSession, rule_set_id: UUID, payload: dict, variables: dict | None = None, rules_json: dict | None = None) -> RuleEvaluationResult:
    item = await repository.get_rule_set_or_404(session, rule_set_id)
    if not item.enabled:
        raise BadRequestError("Business rule set is disabled")
    return engine.evaluate(rules_json or item.rules_json, {"payload": payload, "variables": variables or {}})


async def install_presets(session: AsyncSession) -> dict[str, int]:
    await create_rule_set(session, BusinessRuleSetCreate(**SMART_ROUTER_RULE_SET))
    return {"rule_sets": 1}
