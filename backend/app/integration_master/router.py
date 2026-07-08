from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.integration_master import service
from app.integration_master.schemas import (
    CompileDraftRequest,
    CompileDraftResponse,
    CompileDraftValidationResponse,
    CompilePreviewResponse,
    CompiledEnableResponse,
    CompiledRunTestRequest,
    CompiledRunTestResponse,
    FinalActionPreviewResponse,
    FinalActionRequest,
    FinalActionSaveRequest,
    FinalActionSaveResponse,
    FinalActionTestRequest,
    FinalActionTestResponse,
    FinalActionValidationResponse,
    ForeachODataStepPreviewResponse,
    ForeachODataStepRequest,
    ForeachODataStepSaveRequest,
    ForeachODataStepSaveResponse,
    ForeachODataStepTestResponse,
    ForeachODataStepValidationResponse,
    InputContractValidationRequest,
    InputContractValidationResponse,
    InputDraftRead,
    InputDraftSaveRequest,
    InputDraftSaveResponse,
    InputParseRequest,
    InputParseResponse,
    IntegrationScenario,
    ODataObjectStepPreviewResponse,
    ODataObjectStepRequest,
    ODataObjectStepSaveRequest,
    ODataObjectStepSaveResponse,
    ODataObjectStepTestResponse,
    ODataObjectStepValidationResponse,
    ODataStepPreviewResponse,
    ODataStepRequest,
    ODataStepSaveRequest,
    ODataStepSaveResponse,
    ODataStepTestResponse,
    ODataStepValidationResponse,
    PayloadStepPreviewResponse,
    PayloadStepRequest,
    PayloadStepSaveRequest,
    PayloadStepSaveResponse,
    PayloadStepValidationResponse,
)

router = APIRouter(prefix="/api/integration-master", tags=["integration-master"])


@router.get("/scenarios", response_model=list[IntegrationScenario])
async def list_scenarios():
    return service.list_scenarios()


@router.post("/input/parse", response_model=InputParseResponse)
async def parse_input(request: InputParseRequest):
    return service.parse_contract_input(request)


@router.post("/input/validate", response_model=InputContractValidationResponse)
async def validate_input(request: InputContractValidationRequest):
    return service.validate_input_contract(request.contract)


@router.post("/input/save-draft", response_model=InputDraftSaveResponse)
async def save_draft(request: InputDraftSaveRequest, session: AsyncSession = Depends(get_session)):
    draft = await service.save_draft(session, request.contract, request.parse_result)
    await session.commit()
    return {"draft": draft, "next_steps": ["Настроить действия интеграции", "Добавить OData/API/XML шаги", "Запустить Dry Run и проверить Timeline"]}


@router.get("/drafts/{draft_id}", response_model=InputDraftRead)
async def get_draft(draft_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_draft(session, draft_id)


@router.post("/drafts/{draft_id}/validate-for-compile", response_model=CompileDraftValidationResponse)
async def validate_for_compile(draft_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.validate_draft_for_compile(session, draft_id)


@router.post("/drafts/{draft_id}/compile-preview", response_model=CompilePreviewResponse)
async def compile_preview(draft_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.preview_compile_draft(session, draft_id)


@router.post("/drafts/{draft_id}/compile", response_model=CompileDraftResponse)
async def compile_draft(draft_id: UUID, payload: CompileDraftRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.compile_draft(session, draft_id, payload)
    details = {
        "draft_id": str(draft_id),
        "flow_id": str(result.integration_flow_id),
        "endpoint_id": str(result.endpoint_id),
        "route_id": str(result.route_id),
        "saved_test_case_id": str(result.saved_test_case_id) if result.saved_test_case_id else None,
        "enabled": result.enabled,
        "endpoint_url": result.endpoint.url,
        "comment": payload.comment,
    }
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_master.compiled",
        category="integration_master",
        object_type="integration_master_draft",
        object_id=draft_id,
        object_name=result.endpoint.url,
        summary=f"Integration Master draft compiled into {result.endpoint.url}",
        details=details,
    )
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_flow.created_from_master",
        category="integration_flows",
        object_type="integration_flow",
        object_id=result.integration_flow_id,
        object_name=result.endpoint.url,
        summary=f"Integration flow created from Integration Master draft {draft_id}",
        details=details,
    )
    if result.saved_test_case_id:
        await audit_service.record_action(
            session,
            request=http_request,
            action="saved_test_case.created_from_master",
            category="test_console",
            object_type="saved_test_case",
            object_id=result.saved_test_case_id,
            object_name=result.endpoint.url,
            summary=f"Saved test case created from Integration Master draft {draft_id}",
            details=details,
        )
    await session.commit()
    return result


@router.post("/compiled/{integration_flow_id}/run-test", response_model=CompiledRunTestResponse)
async def run_compiled_test(integration_flow_id: UUID, payload: CompiledRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.run_compiled_test(session, integration_flow_id, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_master.compiled_test_run",
        category="integration_master",
        object_type="integration_flow",
        object_id=integration_flow_id,
        summary=f"Compiled integration {integration_flow_id} test run completed",
        details={"dry_run": payload.dry_run, "saved_test_case_id": str(result.saved_test_case_id), "success": result.success, "event_id": str(result.event_id) if result.event_id else None},
    )
    await session.commit()
    return result


@router.post("/compiled/{integration_flow_id}/enable", response_model=CompiledEnableResponse)
async def enable_compiled(integration_flow_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.enable_compiled_integration(session, integration_flow_id)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_master.compiled_enabled",
        category="integration_master",
        object_type="integration_flow",
        object_id=integration_flow_id,
        summary=f"Compiled integration {integration_flow_id} enabled",
        details=result.model_dump(mode="json"),
    )
    await session.commit()
    return result


@router.post("/odata-step/validate", response_model=ODataStepValidationResponse)
async def validate_odata_step(request: ODataStepRequest):
    return service.validate_odata_step(request)


@router.post("/odata-step/preview", response_model=ODataStepPreviewResponse)
async def preview_odata_step(request: ODataStepRequest):
    return service.preview_odata_step(request)


@router.post("/odata-step/test", response_model=ODataStepTestResponse)
async def test_odata_step(request: ODataStepRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_odata_step(session, request)


@router.post("/drafts/{draft_id}/odata-steps", response_model=ODataStepSaveResponse)
async def append_odata_step(draft_id: UUID, request: ODataStepSaveRequest, session: AsyncSession = Depends(get_session)):
    draft, saved_step = await service.append_odata_step(session, draft_id, request.odata_step)
    await session.commit()
    return {
        "draft": draft,
        "saved_step": saved_step,
        "next_steps": [
            "Добавить второй шаг позже через foreach/tabular helper",
            "Настроить JSON/XML builder и endpoint отправки",
            "Запустить Dry Run и проверить Timeline/DLQ",
        ],
    }


@router.post("/odata-object-step/validate", response_model=ODataObjectStepValidationResponse)
async def validate_odata_object_step(request: ODataObjectStepRequest):
    return service.validate_odata_object_step(request)


@router.post("/odata-object-step/preview", response_model=ODataObjectStepPreviewResponse)
async def preview_odata_object_step(request: ODataObjectStepRequest):
    return service.preview_odata_object_step(request)


@router.post("/odata-object-step/test", response_model=ODataObjectStepTestResponse)
async def test_odata_object_step(request: ODataObjectStepRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_odata_object_step(session, request)


@router.post("/drafts/{draft_id}/odata-object-steps", response_model=ODataObjectStepSaveResponse)
async def append_odata_object_step(draft_id: UUID, request: ODataObjectStepSaveRequest, session: AsyncSession = Depends(get_session)):
    draft, saved_step = await service.append_odata_object_step(session, draft_id, request.odata_object_step, request.previous_variables)
    await session.commit()
    return {
        "draft": draft,
        "saved_step": saved_step,
        "next_steps": [
            "Повторить OData по массиву products будет следующим этапом",
            "Настроить JSON/XML builder позже",
            "Запустить Dry Run и проверить Timeline/DLQ позже",
        ],
    }


@router.post("/foreach-odata-step/validate", response_model=ForeachODataStepValidationResponse)
async def validate_foreach_odata_step(request: ForeachODataStepRequest):
    return service.validate_foreach_odata_step(request)


@router.post("/foreach-odata-step/preview", response_model=ForeachODataStepPreviewResponse)
async def preview_foreach_odata_step(request: ForeachODataStepRequest):
    return service.preview_foreach_odata_step(request)


@router.post("/foreach-odata-step/test", response_model=ForeachODataStepTestResponse)
async def test_foreach_odata_step(request: ForeachODataStepRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_foreach_odata_step(session, request)


@router.post("/drafts/{draft_id}/foreach-odata-steps", response_model=ForeachODataStepSaveResponse)
async def append_foreach_odata_step(draft_id: UUID, request: ForeachODataStepSaveRequest, session: AsyncSession = Depends(get_session)):
    draft, saved_step = await service.append_foreach_odata_step(session, draft_id, request.foreach_step, request.previous_variables)
    await session.commit()
    return {
        "draft": draft,
        "saved_step": saved_step,
        "next_steps": [
            "JSON/XML builder будет следующим этапом",
            "Endpoint send и full integration compile позже",
            "Запустить Dry Run и проверить Timeline/DLQ позже",
        ],
    }


@router.post("/payload/validate", response_model=PayloadStepValidationResponse)
async def validate_payload_step(request: PayloadStepRequest):
    return service.validate_payload_step(request)


@router.post("/payload/preview", response_model=PayloadStepPreviewResponse)
async def preview_payload_step(request: PayloadStepRequest):
    return service.preview_payload_step(request)


@router.post("/drafts/{draft_id}/payload-steps", response_model=PayloadStepSaveResponse)
async def append_payload_step(draft_id: UUID, request: PayloadStepSaveRequest, session: AsyncSession = Depends(get_session)):
    draft, saved_step = await service.append_payload_step(session, draft_id, request.payload_step, request.previous_variables)
    await session.commit()
    return {
        "draft": draft,
        "saved_step": saved_step,
        "next_steps": [
            "Endpoint send и caller response будут следующими этапами",
            "Full integration compile пока не выполняется",
            "Запустить Dry Run и проверить Timeline/DLQ позже",
        ],
    }


@router.post("/final-action/validate", response_model=FinalActionValidationResponse)
async def validate_final_action(request: FinalActionRequest):
    return service.validate_final_action_step(request)


@router.post("/final-action/preview", response_model=FinalActionPreviewResponse)
async def preview_final_action(request: FinalActionRequest):
    return service.preview_final_action_step(request)


@router.post("/final-action/test", response_model=FinalActionTestResponse)
async def test_final_action(request: FinalActionTestRequest):
    return await service.test_final_action_step(request)


@router.post("/drafts/{draft_id}/final-action", response_model=FinalActionSaveResponse)
async def save_final_action(draft_id: UUID, request: FinalActionSaveRequest, session: AsyncSession = Depends(get_session)):
    draft, saved_action = await service.save_final_action(session, draft_id, request.final_action, request.previous_variables)
    await session.commit()
    return {
        "draft": draft,
        "final_action": saved_action,
        "next_steps": [
            "Step 4A сохранён в draft. Full publish/compile будет отдельным этапом.",
            "Проверьте dry-run перед real test, чтобы не отправить случайный запрос во внешний сервис.",
            "Production retry/DLQ и Timeline появятся в следующих этапах.",
        ],
    }
