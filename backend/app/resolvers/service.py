from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_objects.registry import registry as object_registry
from app.core.errors import BadRequestError, NotFoundError
from app.resolvers import cache, repository
from app.resolvers.engine import ResolverEngine
from app.resolvers.presets import DEFAULT_RESOLVER_PRESETS
from app.resolvers.schemas import ResolverDefinitionCreate, ResolverDefinitionPatch, ResolverResult

SUPPORTED_STRATEGIES = {"odata", "rest", "static_map", "chain"}


def validate_definition(request: ResolverDefinitionCreate | ResolverDefinitionPatch) -> None:
    data = request.model_dump(exclude_unset=True)
    object_type = data.get("object_type")
    if object_type and not object_registry.exists(str(object_type)):
        raise BadRequestError(f"Unknown business object type: {object_type}")
    strategy = data.get("strategy")
    if strategy and strategy not in SUPPORTED_STRATEGIES:
        raise BadRequestError(f"Unsupported resolver strategy: {strategy}")
    if int(data.get("cache_ttl_seconds") or 1) < 0:
        raise BadRequestError("cache_ttl_seconds must be >= 0")


async def list_resolvers(session: AsyncSession, object_type: str | None = None, enabled: bool | None = None):
    return await repository.list_definitions(session, object_type=object_type, enabled=enabled)


async def create_resolver(session: AsyncSession, request: ResolverDefinitionCreate):
    validate_definition(request)
    return await repository.upsert_definition(session, request)


async def get_resolver(session: AsyncSession, resolver_id: UUID):
    return await repository.get_definition_or_404(session, resolver_id)


async def patch_resolver(session: AsyncSession, resolver_id: UUID, request: ResolverDefinitionPatch):
    validate_definition(request)
    return await repository.patch_definition(session, resolver_id, request)


async def resolve_by_id(session: AsyncSession, resolver_id: UUID, input_data: dict, context: dict | None = None, use_cache: bool = True) -> ResolverResult:
    resolver = await repository.get_definition_or_404(session, resolver_id)
    return await ResolverEngine(session).resolve(resolver.resolver_code, input_data, context=context, use_cache=use_cache)


async def resolve_by_code(session: AsyncSession, resolver_code: str, input_data: dict, context: dict | None = None, use_cache: bool = True) -> ResolverResult:
    return await ResolverEngine(session).resolve(resolver_code, input_data, context=context, use_cache=use_cache)


async def install_presets(session: AsyncSession) -> dict[str, int]:
    created_or_updated = 0
    for item in DEFAULT_RESOLVER_PRESETS:
        await create_resolver(session, ResolverDefinitionCreate(**item))
        created_or_updated += 1
    return {"resolvers": created_or_updated}


async def list_cache(session: AsyncSession, resolver_code: str | None = None, object_type: str | None = None):
    return await cache.list_entries(session, resolver_code=resolver_code, object_type=object_type)


async def delete_cache_entry(session: AsyncSession, entry_id: UUID) -> dict[str, bool]:
    deleted = await cache.delete_entry(session, entry_id)
    if not deleted:
        raise NotFoundError("Resolver cache entry not found")
    return {"deleted": True}


async def clear_cache_for_resolver(session: AsyncSession, resolver_id: UUID) -> dict[str, int]:
    await repository.get_definition_or_404(session, resolver_id)
    return {"deleted": await cache.clear_resolver(session, resolver_id)}
