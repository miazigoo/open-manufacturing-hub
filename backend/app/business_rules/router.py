from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import service
from app.business_rules.schemas import BusinessRuleSetCreate, BusinessRuleSetPatch, BusinessRuleSetRead, BusinessRuleTestRequest, RuleEvaluationResult
from app.core.database import get_session

router = APIRouter(prefix="/api/business-rules", tags=["business-rules"])


@router.get("", response_model=list[BusinessRuleSetRead])
async def list_rule_sets(scope: str | None = None, enabled: bool | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_rule_sets(session, scope=scope, enabled=enabled)


@router.post("", response_model=BusinessRuleSetRead)
async def create_rule_set(request: BusinessRuleSetCreate, session: AsyncSession = Depends(get_session)):
    item = await service.create_rule_set(session, request)
    await session.commit()
    return item


@router.post("/install-presets")
async def install_presets(session: AsyncSession = Depends(get_session)):
    result = await service.install_presets(session)
    await session.commit()
    return result


@router.get("/{rule_set_id}", response_model=BusinessRuleSetRead)
async def get_rule_set(rule_set_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_rule_set(session, rule_set_id)


@router.patch("/{rule_set_id}", response_model=BusinessRuleSetRead)
async def patch_rule_set(rule_set_id: UUID, request: BusinessRuleSetPatch, session: AsyncSession = Depends(get_session)):
    item = await service.patch_rule_set(session, rule_set_id, request)
    await session.commit()
    return item


@router.post("/{rule_set_id}/test", response_model=RuleEvaluationResult)
async def test_rule_set(rule_set_id: UUID, request: BusinessRuleTestRequest, session: AsyncSession = Depends(get_session)):
    return await service.evaluate_rule_set(session, rule_set_id, request.payload, variables=request.variables, rules_json=request.rules_json)
