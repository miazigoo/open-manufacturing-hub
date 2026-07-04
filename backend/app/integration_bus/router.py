from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.integration_bus import repository, service
from app.integration_bus.schemas import (
    BusDispatchResponse,
    IntegrationEndpointCreate,
    IntegrationEndpointPatch,
    IntegrationEndpointRead,
    IntegrationRouteCreate,
    IntegrationRoutePatch,
    IntegrationRouteRead,
    ODataLookupTemplateCreate,
    ODataLookupTemplatePatch,
    ODataLookupTemplateRead,
    ODataLookupTemplateTestRequest,
    PresetInstallResponse,
)

router = APIRouter(tags=["integration-bus"])


@router.get("/api/integration-bus/endpoints", response_model=list[IntegrationEndpointRead])
async def list_endpoints(session: AsyncSession = Depends(get_session)):
    return await repository.list_endpoints(session)


@router.post("/api/integration-bus/endpoints", response_model=IntegrationEndpointRead)
async def create_endpoint(request: IntegrationEndpointCreate, session: AsyncSession = Depends(get_session)):
    endpoint = await service.create_endpoint(session, request)
    await session.commit()
    return endpoint


@router.patch("/api/integration-bus/endpoints/{endpoint_id}", response_model=IntegrationEndpointRead)
async def patch_endpoint(endpoint_id: UUID, request: IntegrationEndpointPatch, session: AsyncSession = Depends(get_session)):
    endpoint = await service.patch_endpoint(session, endpoint_id, request)
    await session.commit()
    return endpoint


@router.delete("/api/integration-bus/endpoints/{endpoint_id}", status_code=204)
async def delete_endpoint(endpoint_id: UUID, session: AsyncSession = Depends(get_session)):
    endpoint = await service.get_endpoint_or_404(session, endpoint_id)
    await session.delete(endpoint)
    await session.commit()
    return Response(status_code=204)


@router.get("/api/integration-bus/routes", response_model=list[IntegrationRouteRead])
async def list_routes(session: AsyncSession = Depends(get_session)):
    return await repository.list_routes(session)


@router.post("/api/integration-bus/routes", response_model=IntegrationRouteRead)
async def create_route(request: IntegrationRouteCreate, session: AsyncSession = Depends(get_session)):
    route = await service.create_route(session, request)
    await session.commit()
    return route


@router.patch("/api/integration-bus/routes/{route_id}", response_model=IntegrationRouteRead)
async def patch_route(route_id: UUID, request: IntegrationRoutePatch, session: AsyncSession = Depends(get_session)):
    route = await service.patch_route(session, route_id, request)
    await session.commit()
    return route


@router.delete("/api/integration-bus/routes/{route_id}", status_code=204)
async def delete_route(route_id: UUID, session: AsyncSession = Depends(get_session)):
    route = await service.get_route_or_404(session, route_id)
    await session.delete(route)
    await session.commit()
    return Response(status_code=204)


@router.get("/api/odata-lookups", response_model=list[ODataLookupTemplateRead])
async def list_lookup_templates(session: AsyncSession = Depends(get_session)):
    return await repository.list_lookup_templates(session)


@router.post("/api/odata-lookups", response_model=ODataLookupTemplateRead)
async def create_lookup_template(request: ODataLookupTemplateCreate, session: AsyncSession = Depends(get_session)):
    template = await service.create_lookup_template(session, request)
    await session.commit()
    return template


@router.patch("/api/odata-lookups/{template_id}", response_model=ODataLookupTemplateRead)
async def patch_lookup_template(template_id: UUID, request: ODataLookupTemplatePatch, session: AsyncSession = Depends(get_session)):
    template = await service.patch_lookup_template(session, template_id, request)
    await session.commit()
    return template


@router.post("/api/odata-lookups/{template_id}/test")
async def test_lookup_template(template_id: UUID, request: ODataLookupTemplateTestRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_lookup_template(session, template_id, request.input)


@router.delete("/api/odata-lookups/{template_id}", status_code=204)
async def delete_lookup_template(template_id: UUID, session: AsyncSession = Depends(get_session)):
    template = await service.get_lookup_template_or_404(session, template_id)
    await session.delete(template)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/integration-bus/install-presets", response_model=PresetInstallResponse)
async def install_presets(session: AsyncSession = Depends(get_session)):
    endpoints, routes, lookups = await service.install_presets(session)
    await session.commit()
    return {"endpoints": endpoints, "routes": routes, "lookups": lookups}


@router.post("/api/bus/in/{slug}")
async def dispatch(slug: str, request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.dispatch(session, slug, request)
    await session.commit()
    return result
