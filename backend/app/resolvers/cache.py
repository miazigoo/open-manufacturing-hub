from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resolvers.models import ResolverCacheEntry, ResolverDefinitionV2


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_key_for(input_data: dict[str, Any], config: dict[str, Any]) -> str:
    fields = config.get("cache_key_fields")
    if isinstance(fields, list) and fields:
        parts = [str(input_data.get(str(field), "")) for field in fields]
        key = "|".join(parts).strip("|")
        if key:
            return key
    return stable_hash(input_data)


async def get_entry(session: AsyncSession, resolver: ResolverDefinitionV2, cache_key: str) -> tuple[ResolverCacheEntry | None, bool]:
    item = (await session.execute(select(ResolverCacheEntry).where(ResolverCacheEntry.resolver_id == resolver.id, ResolverCacheEntry.cache_key == cache_key))).scalar_one_or_none()
    if item is None:
        return None, False
    expires_at = item.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    expired = expires_at is not None and expires_at <= utcnow()
    if not expired:
        item.hit_count += 1
        item.last_hit_at = utcnow()
        await session.flush()
    return item, expired


async def store_entry(
    session: AsyncSession,
    resolver: ResolverDefinitionV2,
    *,
    cache_key: str,
    input_data: dict[str, Any],
    object_json: dict[str, Any],
    source_system: str | None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> ResolverCacheEntry:
    input_hash = stable_hash(input_data)
    expires_at = utcnow() + timedelta(seconds=max(resolver.cache_ttl_seconds, 1)) if resolver.cache_ttl_seconds > 0 else None
    entry, _ = await get_entry(session, resolver, cache_key)
    if entry is None:
        entry = ResolverCacheEntry(
            resolver_id=resolver.id,
            resolver_code=resolver.resolver_code,
            cache_key=cache_key,
            input_hash=input_hash,
            object_type=resolver.object_type,
            resolved_object_json=object_json,
            source_connector_id=resolver.connector_id,
            source_system=source_system,
            expires_at=expires_at,
            error_code=error_code,
            error_message=error_message,
        )
        session.add(entry)
    else:
        entry.input_hash = input_hash
        entry.object_type = resolver.object_type
        entry.resolved_object_json = object_json
        entry.source_connector_id = resolver.connector_id
        entry.source_system = source_system
        entry.expires_at = expires_at
        entry.error_code = error_code
        entry.error_message = error_message
    await session.flush()
    return entry


async def list_entries(session: AsyncSession, resolver_code: str | None = None, object_type: str | None = None) -> list[ResolverCacheEntry]:
    query = select(ResolverCacheEntry).order_by(ResolverCacheEntry.updated_at.desc())
    if resolver_code:
        query = query.where(ResolverCacheEntry.resolver_code == resolver_code)
    if object_type:
        query = query.where(ResolverCacheEntry.object_type == object_type)
    return list((await session.execute(query)).scalars().all())


async def delete_entry(session: AsyncSession, entry_id: UUID) -> bool:
    item = await session.get(ResolverCacheEntry, entry_id)
    if item is None:
        return False
    await session.delete(item)
    await session.flush()
    return True


async def clear_resolver(session: AsyncSession, resolver_id: UUID) -> int:
    result = await session.execute(delete(ResolverCacheEntry).where(ResolverCacheEntry.resolver_id == resolver_id))
    await session.flush()
    return int(result.rowcount or 0)
