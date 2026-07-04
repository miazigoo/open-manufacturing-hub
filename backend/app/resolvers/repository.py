from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.resolvers.models import ResolverDefinitionV2
from app.resolvers.schemas import ResolverDefinitionCreate, ResolverDefinitionPatch


async def list_definitions(session: AsyncSession, object_type: str | None = None, enabled: bool | None = None) -> list[ResolverDefinitionV2]:
    query = select(ResolverDefinitionV2).order_by(ResolverDefinitionV2.object_type.asc(), ResolverDefinitionV2.name.asc())
    if object_type:
        query = query.where(ResolverDefinitionV2.object_type == object_type)
    if enabled is not None:
        query = query.where(ResolverDefinitionV2.enabled.is_(enabled))
    return list((await session.execute(query)).scalars().all())


async def get_definition(session: AsyncSession, resolver_id: UUID) -> ResolverDefinitionV2 | None:
    return await session.get(ResolverDefinitionV2, resolver_id)


async def get_definition_or_404(session: AsyncSession, resolver_id: UUID) -> ResolverDefinitionV2:
    item = await get_definition(session, resolver_id)
    if item is None:
        raise NotFoundError("Resolver definition not found")
    return item


async def get_by_code(session: AsyncSession, resolver_code: str) -> ResolverDefinitionV2 | None:
    return (await session.execute(select(ResolverDefinitionV2).where(ResolverDefinitionV2.resolver_code == resolver_code))).scalar_one_or_none()


async def get_by_code_or_404(session: AsyncSession, resolver_code: str) -> ResolverDefinitionV2:
    item = await get_by_code(session, resolver_code)
    if item is None:
        raise NotFoundError(f"Resolver {resolver_code} not found")
    return item


async def upsert_definition(session: AsyncSession, request: ResolverDefinitionCreate) -> ResolverDefinitionV2:
    existing = await get_by_code(session, request.resolver_code)
    data = request.model_dump()
    if existing is None:
        existing = ResolverDefinitionV2(**data)
        session.add(existing)
    else:
        for key, value in data.items():
            setattr(existing, key, value)
    await session.flush()
    return existing


async def patch_definition(session: AsyncSession, resolver_id: UUID, request: ResolverDefinitionPatch) -> ResolverDefinitionV2:
    item = await get_definition_or_404(session, resolver_id)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await session.flush()
    return item
