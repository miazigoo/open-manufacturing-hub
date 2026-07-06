from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.core.errors import NotFoundError
from app.integration_flows import repository, service
from app.integration_flows.schemas import FlowExportResponse, FlowTestRequest, FlowTestResponse, IntegrationFlowCreate, IntegrationFlowPatch, IntegrationFlowRead

router = APIRouter(prefix="/api/integration-flows", tags=["integration-flows"])


@router.get("", response_model=list[IntegrationFlowRead])
async def list_flows(session: AsyncSession = Depends(get_session)):
    return await service.list_flows(session)


@router.post("", response_model=IntegrationFlowRead)
async def create_flow(payload: IntegrationFlowCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    flow = await service.create_flow(session, payload)
    await audit_service.record_change(session, request=http_request, action="integration_flow.created", category="integration_flows", object_type="integration_flow", object_id=flow.id, object_name=flow.name, before=None, after=audit_service.snapshot_model(flow), summary=f"Integration flow {flow.name} created")
    await session.commit()
    return await service._read_flow(flow, session)


@router.post("/presets/marking-pool-to-internal-service/install", response_model=IntegrationFlowRead)
async def install_marking_pool_preset(session: AsyncSession = Depends(get_session)):
    flow = await service.install_marking_pool_preset(session)
    await session.commit()
    return await service._read_flow(flow, session)


@router.post("/presets/onec-post-two-odata-to-endpoint/install", response_model=IntegrationFlowRead)
async def install_two_odata_to_endpoint_preset(session: AsyncSession = Depends(get_session)):
    flow = await service.install_two_odata_to_endpoint_preset(session)
    await session.commit()
    return await service._read_flow(flow, session)


@router.post("/presets/operation-key-odata-chain/install", response_model=IntegrationFlowRead)
async def install_operation_key_odata_chain_preset(session: AsyncSession = Depends(get_session)):
    flow = await service.install_operation_key_odata_chain_preset(session)
    await session.commit()
    return await service._read_flow(flow, session)


@router.post("/presets/dnp-pull-codes/install", response_model=IntegrationFlowRead)
async def install_dnp_pull_codes_preset(session: AsyncSession = Depends(get_session)):
    flow = await service.install_dnp_pull_codes_preset(session)
    await session.commit()
    return await service._read_flow(flow, session)


@router.get("/by-slug/{slug}", response_model=IntegrationFlowRead)
async def get_by_slug(slug: str, session: AsyncSession = Depends(get_session)):
    flow = await repository.get_by_slug(session, slug)
    if flow is None:
        raise NotFoundError("Integration flow not found")
    return await service._read_flow(flow, session)


@router.get("/{flow_id}", response_model=IntegrationFlowRead)
async def get_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    flow = await service.get_flow_or_404(session, flow_id)
    return await service._read_flow(flow, session)


@router.patch("/{flow_id}", response_model=IntegrationFlowRead)
async def patch_flow(flow_id: UUID, payload: IntegrationFlowPatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_flow_or_404(session, flow_id)
    before = audit_service.snapshot_model(existing)
    flow = await service.patch_flow(session, flow_id, payload)
    await audit_service.record_change(session, request=http_request, action="integration_flow.updated", category="integration_flows", object_type="integration_flow", object_id=flow.id, object_name=flow.name, before=before, after=audit_service.snapshot_model(flow), summary=f"Integration flow {flow.name} updated")
    await session.commit()
    return await service._read_flow(flow, session)


@router.delete("/{flow_id}", status_code=204)
async def delete_flow(flow_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    flow = await service.get_flow_or_404(session, flow_id)
    before = audit_service.snapshot_model(flow)
    await audit_service.record_change(session, request=http_request, action="integration_flow.deleted", category="integration_flows", object_type="integration_flow", object_id=flow.id, object_name=flow.name, before=before, after=None, summary=f"Integration flow {flow.name} deleted")
    await session.delete(flow)
    await session.commit()
    return Response(status_code=204)


@router.post("/{flow_id}/test", response_model=FlowTestResponse)
async def test_flow(flow_id: UUID, payload: FlowTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.test_flow(session, flow_id, payload)
    flow = await service.get_flow_or_404(session, flow_id)
    await audit_service.record_action(session, request=http_request, action="integration_flow.test_run", category="integration_flows", object_type="integration_flow", object_id=flow.id, object_name=flow.name, summary=f"Integration flow {flow.name} test run completed", details={"dry_run": payload.dry_run, "result": result.model_dump(mode="json") if hasattr(result, "model_dump") else result})
    await session.commit()
    return result


@router.post("/{flow_id}/duplicate", response_model=IntegrationFlowRead)
async def duplicate_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    flow = await service.duplicate_flow(session, flow_id)
    await session.commit()
    return await service._read_flow(flow, session)


@router.get("/{flow_id}/export", response_model=FlowExportResponse)
async def export_flow(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.export_flow(session, flow_id)
