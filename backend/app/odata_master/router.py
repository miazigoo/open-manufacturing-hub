from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.core.errors import BadRequestError
from app.flow_builder.preview import preview_builder
from app.integration_flows import service as flow_service
from app.integration_flows.schemas import FlowTestRequest, IntegrationFlowCreate
from app.odata_master.compiler import compile_wizard_spec
from app.odata_master.examples import examples
from app.odata_master.preview import preview_wizard
from app.odata_master.schemas import (
    ODataMasterExample,
    ODataMasterPreviewRequest,
    ODataMasterPreviewResponse,
    ODataMasterRunTestRequest,
    ODataMasterRunTestResponse,
    ODataMasterSaveRequest,
    ODataMasterSaveResponse,
)

router = APIRouter(prefix="/api/odata-master", tags=["odata-master"])


@router.get("/examples", response_model=list[ODataMasterExample])
async def list_examples():
    return examples()


@router.post("/preview", response_model=ODataMasterPreviewResponse)
async def preview(request: ODataMasterPreviewRequest, session: AsyncSession = Depends(get_session)):
    return await preview_wizard(session, request.spec, run_real_queries=request.run_real_queries)


@router.post("/save", response_model=ODataMasterSaveResponse)
async def save(request: ODataMasterSaveRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    compiled = compile_wizard_spec(request.spec, enabled=request.enabled)
    flow = await flow_service.create_flow(session, IntegrationFlowCreate(**compiled["flow_payload"]))
    await audit_service.record_change(
        session,
        request=http_request,
        action="odata_master.integration_created",
        category="integration_flows",
        object_type="integration_flow",
        object_id=flow.id,
        object_name=flow.name,
        before=None,
        after=audit_service.snapshot_model(flow),
        summary=f"OData Master integration {flow.name} created",
    )
    await session.commit()
    flow_read = await flow_service._read_flow(flow, session)
    endpoint_url = flow_read["endpoint_url"]
    return {
        "integration_flow": flow_read,
        "endpoint_url": endpoint_url,
        "next_steps": [
            "Отправьте тестовый запрос в endpoint.",
            "Откройте Timeline по event_id из ответа.",
            "Скопируйте endpoint во внешнюю систему.",
        ],
    }


@router.post("/run-test", response_model=ODataMasterRunTestResponse)
async def run_test(request: ODataMasterRunTestRequest, session: AsyncSession = Depends(get_session)):
    if request.flow_id is not None:
        flow = await flow_service.get_flow_or_404(session, request.flow_id)
        result = await flow_service.test_flow(
            session,
            flow.id,
            FlowTestRequest(
                input_mode=(flow.test_payload_text and "xml") or "json",
                payload_json=request.payload_json or flow.test_payload_json,
                payload_text=request.payload_text or flow.test_payload_text,
                headers_json=request.headers_json,
                dry_run=request.dry_run,
            ),
        )
        await session.commit()
        return {"mode": "saved_flow", "result": result}

    if request.spec is None:
        raise BadRequestError("Передайте spec или flow_id.")
    compiled = compile_wizard_spec(request.spec)
    sample = request.payload_json or compiled["flow_payload"].get("test_payload_json") or {}
    result = await preview_builder(session, compiled["builder_json"], sample, run_real_queries=request.run_real_queries)
    return {"mode": "preview", "result": {"compiled": compiled, "preview": result}}
