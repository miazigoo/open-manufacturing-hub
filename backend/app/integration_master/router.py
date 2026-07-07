from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.integration_master import service
from app.integration_master.schemas import (
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
