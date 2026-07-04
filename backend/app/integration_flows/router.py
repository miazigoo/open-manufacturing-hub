from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.integration_flows import repository, service
from app.integration_flows.schemas import FlowExportResponse, FlowTestRequest, FlowTestResponse, IntegrationFlowCreate, IntegrationFlowPatch, IntegrationFlowRead

router = APIRouter(prefix="/api/integration-flows", tags=["integration-flows"])


@router.get("", response_model=list[IntegrationFlowRead])
async def list_flows(session: AsyncSession = Depends(get_session)):
    return await service.list_flows(session)


@router.post("", response_model=IntegrationFlowRead)
async def create_flow(request: IntegrationFlowCreate, session: AsyncSession = Depends(get_session)):
    flow = await service.create_flow(session, request)
    await session.commit()
    return await service._read_flow(flow)


@router.post("/presets/marking-pool-to-internal-service/install", response_model=IntegrationFlowRead)
async def install_marking_pool_preset(session: AsyncSession = Depends(get_session)):
    flow = await service.install_marking_pool_preset(session)
    await session.commit()
    return await service._read_flow(flow)


@router.get("/by-slug/{slug}", response_model=IntegrationFlowRead)
async def get_by_slug(slug: str, session: AsyncSession = Depends(get_session)):
    flow = await repository.get_by_slug(session, slug)
    if flow is None:
        raise NotFoundError("Integration flow not found")
    return await service._read_flow(flow)


@router.get("/{flow_id}", response_model=IntegrationFlowRead)
async def get_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    flow = await service.get_flow_or_404(session, flow_id)
    return await service._read_flow(flow)


@router.patch("/{flow_id}", response_model=IntegrationFlowRead)
async def patch_flow(flow_id: UUID, request: IntegrationFlowPatch, session: AsyncSession = Depends(get_session)):
    flow = await service.patch_flow(session, flow_id, request)
    await session.commit()
    return await service._read_flow(flow)


@router.delete("/{flow_id}", status_code=204)
async def delete_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    flow = await service.get_flow_or_404(session, flow_id)
    await session.delete(flow)
    await session.commit()
    return Response(status_code=204)


@router.post("/{flow_id}/test", response_model=FlowTestResponse)
async def test_flow(flow_id: UUID, request: FlowTestRequest, session: AsyncSession = Depends(get_session)):
    result = await service.test_flow(session, flow_id, request)
    await session.commit()
    return result


@router.post("/{flow_id}/duplicate", response_model=IntegrationFlowRead)
async def duplicate_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    flow = await service.duplicate_flow(session, flow_id)
    await session.commit()
    return await service._read_flow(flow)


@router.get("/{flow_id}/export", response_model=FlowExportResponse)
async def export_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.export_flow(session, flow_id)
