from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
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
async def create_endpoint(payload: IntegrationEndpointCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    endpoint = await service.create_endpoint(session, payload)
    await audit_service.record_change(session, request=http_request, action="endpoint.created", category="endpoints", object_type="integration_endpoint", object_id=endpoint.id, object_name=endpoint.name, before=None, after=audit_service.snapshot_model(endpoint), summary=f"Integration endpoint {endpoint.name} created")
    await session.commit()
    return endpoint


@router.patch("/api/integration-bus/endpoints/{endpoint_id}", response_model=IntegrationEndpointRead)
async def patch_endpoint(endpoint_id: UUID, payload: IntegrationEndpointPatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_endpoint_or_404(session, endpoint_id)
    before = audit_service.snapshot_model(existing)
    endpoint = await service.patch_endpoint(session, endpoint_id, payload)
    await audit_service.record_change(session, request=http_request, action="endpoint.updated", category="endpoints", object_type="integration_endpoint", object_id=endpoint.id, object_name=endpoint.name, before=before, after=audit_service.snapshot_model(endpoint), summary=f"Integration endpoint {endpoint.name} updated")
    await session.commit()
    return endpoint


@router.delete("/api/integration-bus/endpoints/{endpoint_id}", status_code=204)
async def delete_endpoint(endpoint_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    endpoint = await service.get_endpoint_or_404(session, endpoint_id)
    before = audit_service.snapshot_model(endpoint)
    await audit_service.record_change(session, request=http_request, action="endpoint.deleted", category="endpoints", object_type="integration_endpoint", object_id=endpoint.id, object_name=endpoint.name, before=before, after=None, summary=f"Integration endpoint {endpoint.name} deleted")
    await session.delete(endpoint)
    await session.commit()
    return Response(status_code=204)


@router.get("/api/integration-bus/routes", response_model=list[IntegrationRouteRead])
async def list_routes(session: AsyncSession = Depends(get_session)):
    return await repository.list_routes(session)


@router.post("/api/integration-bus/routes", response_model=IntegrationRouteRead)
async def create_route(payload: IntegrationRouteCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    route = await service.create_route(session, payload)
    await audit_service.record_change(session, request=http_request, action="route.created", category="routes", object_type="integration_route", object_id=route.id, object_name=route.name, before=None, after=audit_service.snapshot_model(route), summary=f"Integration route {route.name} created")
    await session.commit()
    return route


@router.patch("/api/integration-bus/routes/{route_id}", response_model=IntegrationRouteRead)
async def patch_route(route_id: UUID, payload: IntegrationRoutePatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_route_or_404(session, route_id)
    before = audit_service.snapshot_model(existing)
    route = await service.patch_route(session, route_id, payload)
    await audit_service.record_change(session, request=http_request, action="route.updated", category="routes", object_type="integration_route", object_id=route.id, object_name=route.name, before=before, after=audit_service.snapshot_model(route), summary=f"Integration route {route.name} updated")
    await session.commit()
    return route


@router.delete("/api/integration-bus/routes/{route_id}", status_code=204)
async def delete_route(route_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    route = await service.get_route_or_404(session, route_id)
    before = audit_service.snapshot_model(route)
    await audit_service.record_change(session, request=http_request, action="route.deleted", category="routes", object_type="integration_route", object_id=route.id, object_name=route.name, before=before, after=None, summary=f"Integration route {route.name} deleted")
    await session.delete(route)
    await session.commit()
    return Response(status_code=204)


@router.get("/api/odata-lookups", response_model=list[ODataLookupTemplateRead])
async def list_lookup_templates(session: AsyncSession = Depends(get_session)):
    return await repository.list_lookup_templates(session)


@router.post("/api/odata-lookups", response_model=ODataLookupTemplateRead)
async def create_lookup_template(payload: ODataLookupTemplateCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    template = await service.create_lookup_template(session, payload)
    await audit_service.record_change(session, request=http_request, action="resolver.created", category="resolvers", object_type="odata_lookup_template", object_id=template.id, object_name=template.name, before=None, after=audit_service.snapshot_model(template), summary=f"OData lookup template {template.name} created")
    await session.commit()
    return template


@router.patch("/api/odata-lookups/{template_id}", response_model=ODataLookupTemplateRead)
async def patch_lookup_template(template_id: UUID, payload: ODataLookupTemplatePatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_lookup_template_or_404(session, template_id)
    before = audit_service.snapshot_model(existing)
    template = await service.patch_lookup_template(session, template_id, payload)
    await audit_service.record_change(session, request=http_request, action="resolver.updated", category="resolvers", object_type="odata_lookup_template", object_id=template.id, object_name=template.name, before=before, after=audit_service.snapshot_model(template), summary=f"OData lookup template {template.name} updated")
    await session.commit()
    return template


@router.post("/api/odata-lookups/{template_id}/test")
async def test_lookup_template(template_id: UUID, payload: ODataLookupTemplateTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.test_lookup_template(session, template_id, payload.input)
    template = await service.get_lookup_template_or_404(session, template_id)
    await audit_service.record_action(session, request=http_request, action="resolver.tested", category="resolvers", object_type="odata_lookup_template", object_id=template.id, object_name=template.name, summary=f"OData lookup template {template.name} tested", details={"input": payload.input, "result": result})
    await session.commit()
    return result


@router.delete("/api/odata-lookups/{template_id}", status_code=204)
async def delete_lookup_template(template_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    template = await service.get_lookup_template_or_404(session, template_id)
    before = audit_service.snapshot_model(template)
    await audit_service.record_change(session, request=http_request, action="resolver.deleted", category="resolvers", object_type="odata_lookup_template", object_id=template.id, object_name=template.name, before=before, after=None, summary=f"OData lookup template {template.name} deleted")
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
