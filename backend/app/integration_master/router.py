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
