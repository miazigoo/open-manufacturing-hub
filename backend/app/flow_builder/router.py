from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.flow_builder.compiler import FlowCompiler
from app.flow_builder.preview import preview_builder
from app.flow_builder.schemas import FlowBuilderPreviewRequest, FlowBuilderPreviewResponse, FlowCompileResponse, FlowValidationResponse
from app.flow_builder.validator import validate_builder
from app.integration_flows import service as flow_service

router = APIRouter(prefix="/api/flow-builder", tags=["flow-builder"])


@router.post("/validate", response_model=FlowValidationResponse)
async def validate(request: FlowBuilderPreviewRequest):
    return validate_builder(request.builder_json)


@router.post("/preview", response_model=FlowBuilderPreviewResponse)
async def preview(request: FlowBuilderPreviewRequest, session: AsyncSession = Depends(get_session)):
    return await preview_builder(session, request.builder_json, request.sample_request, run_real_queries=request.run_real_queries)


@router.post("/compile", response_model=FlowCompileResponse)
async def compile_preview(request: FlowBuilderPreviewRequest):
    compiled = FlowCompiler().compile(request.builder_json)
    return {"valid": compiled["valid"], "workflow_id": None, "steps_json": compiled["steps_json"], "validation": compiled["validation"]}


@router.get("/flows/{flow_id}")
async def get_flow_builder(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    flow = await flow_service.get_flow_or_404(session, flow_id)
    return {"flow_id": flow.id, "builder_json": flow.builder_json or {}, "last_validation_json": flow.last_validation_json or {}}


@router.patch("/flows/{flow_id}")
async def save_flow_builder(flow_id: UUID, request: FlowBuilderPreviewRequest, session: AsyncSession = Depends(get_session)):
    flow = await flow_service.save_builder(session, flow_id, request.builder_json)
    await session.commit()
    return await flow_service._read_flow(flow, session)


@router.post("/flows/{flow_id}/preview", response_model=FlowBuilderPreviewResponse)
async def preview_flow_builder(flow_id: UUID, request: FlowBuilderPreviewRequest, session: AsyncSession = Depends(get_session)):
    flow = await flow_service.get_flow_or_404(session, flow_id)
    return await preview_builder(session, request.builder_json or flow.builder_json or {}, request.sample_request, run_real_queries=request.run_real_queries)


@router.post("/flows/{flow_id}/compile", response_model=FlowCompileResponse)
async def compile_flow_builder(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await flow_service.compile_flow(session, flow_id)
    await session.commit()
    return result
