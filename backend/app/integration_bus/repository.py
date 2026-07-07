from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute, ODataLookupTemplate


async def list_endpoints(session: AsyncSession) -> list[IntegrationEndpoint]:
    result = await session.execute(select(IntegrationEndpoint).order_by(IntegrationEndpoint.name))
    return list(result.scalars().all())


async def get_endpoint(session: AsyncSession, endpoint_id: UUID) -> IntegrationEndpoint | None:
    return await session.get(IntegrationEndpoint, endpoint_id)


async def get_endpoint_by_slug(session: AsyncSession, slug: str) -> IntegrationEndpoint | None:
    result = await session.execute(select(IntegrationEndpoint).where(IntegrationEndpoint.slug == slug))
    return result.scalar_one_or_none()


async def get_endpoint_by_name(session: AsyncSession, name: str) -> IntegrationEndpoint | None:
    result = await session.execute(select(IntegrationEndpoint).where(IntegrationEndpoint.name == name))
    return result.scalar_one_or_none()


async def list_routes(session: AsyncSession) -> list[IntegrationRoute]:
    result = await session.execute(select(IntegrationRoute).order_by(IntegrationRoute.priority, IntegrationRoute.name))
    return list(result.scalars().all())


async def get_route(session: AsyncSession, route_id: UUID) -> IntegrationRoute | None:
    return await session.get(IntegrationRoute, route_id)


async def list_lookup_templates(session: AsyncSession) -> list[ODataLookupTemplate]:
    result = await session.execute(select(ODataLookupTemplate).order_by(ODataLookupTemplate.name))
    return list(result.scalars().all())


async def get_lookup_template(session: AsyncSession, template_id: UUID) -> ODataLookupTemplate | None:
    return await session.get(ODataLookupTemplate, template_id)


async def get_lookup_template_by_name(session: AsyncSession, name: str) -> ODataLookupTemplate | None:
    result = await session.execute(select(ODataLookupTemplate).where(ODataLookupTemplate.name == name))
    return result.scalar_one_or_none()
