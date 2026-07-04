from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules.models import BusinessRuleSet
from app.business_rules.schemas import BusinessRuleSetCreate, BusinessRuleSetPatch
from app.core.errors import NotFoundError


async def list_rule_sets(session: AsyncSession, scope: str | None = None, enabled: bool | None = None) -> list[BusinessRuleSet]:
    query = select(BusinessRuleSet).order_by(BusinessRuleSet.name.asc())
    if scope:
        query = query.where(BusinessRuleSet.scope == scope)
    if enabled is not None:
        query = query.where(BusinessRuleSet.enabled.is_(enabled))
    return list((await session.execute(query)).scalars().all())


async def get_rule_set(session: AsyncSession, rule_set_id: UUID) -> BusinessRuleSet | None:
    return await session.get(BusinessRuleSet, rule_set_id)


async def get_rule_set_or_404(session: AsyncSession, rule_set_id: UUID) -> BusinessRuleSet:
    item = await get_rule_set(session, rule_set_id)
    if item is None:
        raise NotFoundError("Business rule set not found")
    return item


async def get_by_name(session: AsyncSession, name: str) -> BusinessRuleSet | None:
    return (await session.execute(select(BusinessRuleSet).where(BusinessRuleSet.name == name))).scalar_one_or_none()


async def get_by_name_or_404(session: AsyncSession, name: str) -> BusinessRuleSet:
    item = await get_by_name(session, name)
    if item is None:
        raise NotFoundError(f"Business rule set {name} not found")
    return item


async def upsert_rule_set(session: AsyncSession, request: BusinessRuleSetCreate) -> BusinessRuleSet:
    item = await get_by_name(session, request.name)
    data = request.model_dump()
    if item is None:
        item = BusinessRuleSet(**data)
        session.add(item)
    else:
        for key, value in data.items():
            setattr(item, key, value)
    await session.flush()
    return item


async def patch_rule_set(session: AsyncSession, rule_set_id: UUID, request: BusinessRuleSetPatch) -> BusinessRuleSet:
    item = await get_rule_set_or_404(session, rule_set_id)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await session.flush()
    return item
