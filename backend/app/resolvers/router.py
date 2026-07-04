from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.resolvers import service
from app.resolvers.schemas import ResolverCacheRead, ResolverDefinitionCreate, ResolverDefinitionPatch, ResolverDefinitionRead, ResolverResolveRequest, ResolverResult

router = APIRouter(prefix="/api/resolvers", tags=["resolvers"])


@router.get("", response_model=list[ResolverDefinitionRead])
async def list_resolvers(object_type: str | None = None, enabled: bool | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_resolvers(session, object_type=object_type, enabled=enabled)


@router.post("", response_model=ResolverDefinitionRead)
async def create_resolver(request: ResolverDefinitionCreate, session: AsyncSession = Depends(get_session)):
    item = await service.create_resolver(session, request)
    await session.commit()
    return item


@router.post("/install-presets")
async def install_presets(session: AsyncSession = Depends(get_session)):
    result = await service.install_presets(session)
    await session.commit()
    return result


@router.get("/cache", response_model=list[ResolverCacheRead])
async def list_cache(resolver_code: str | None = None, object_type: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_cache(session, resolver_code=resolver_code, object_type=object_type)


@router.delete("/cache/{entry_id}")
async def delete_cache_entry(entry_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.delete_cache_entry(session, entry_id)
    await session.commit()
    return result


@router.post("/code/{resolver_code}/resolve", response_model=ResolverResult)
async def resolve_by_code(resolver_code: str, request: ResolverResolveRequest, session: AsyncSession = Depends(get_session)):
    result = await service.resolve_by_code(session, resolver_code, request.input_data, context=request.context, use_cache=request.use_cache)
    await session.commit()
    return result


@router.get("/{resolver_id}", response_model=ResolverDefinitionRead)
async def get_resolver(resolver_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_resolver(session, resolver_id)


@router.patch("/{resolver_id}", response_model=ResolverDefinitionRead)
async def patch_resolver(resolver_id: UUID, request: ResolverDefinitionPatch, session: AsyncSession = Depends(get_session)):
    item = await service.patch_resolver(session, resolver_id, request)
    await session.commit()
    return item


@router.post("/{resolver_id}/resolve", response_model=ResolverResult)
async def resolve_by_id(resolver_id: UUID, request: ResolverResolveRequest, session: AsyncSession = Depends(get_session)):
    result = await service.resolve_by_id(session, resolver_id, request.input_data, context=request.context, use_cache=request.use_cache)
    await session.commit()
    return result


@router.post("/{resolver_id}/cache/clear")
async def clear_cache_for_resolver(resolver_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.clear_cache_for_resolver(session, resolver_id)
    await session.commit()
    return result
