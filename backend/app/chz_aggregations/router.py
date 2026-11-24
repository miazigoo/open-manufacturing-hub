from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chz_aggregations import service
from app.chz_aggregations.models import ChzAggregationRegistration
from app.chz_aggregations.schemas import (
    ChzAggregationPreviewResponse,
    ChzAggregationRegistrationRead,
    ChzAggregationRegistrationRequest,
    ChzAggregationRegistrationResponse,
    ChzAggregationSettingsPatch,
    ChzAggregationSettingsRead,
    ChzDnpPullRequest,
    ChzDnpPullResponse,
)
from app.core.database import get_session

router = APIRouter(prefix="/api/chz-aggregations", tags=["chz-aggregations"])


@router.post("/register", response_model=ChzAggregationRegistrationResponse)
async def register_aggregation_json(request: ChzAggregationRegistrationRequest, session: AsyncSession = Depends(get_session)):
    record, onec_response, warnings = await service.register_request(session, request)
    await session.commit()
    return ChzAggregationRegistrationResponse(
        success=record.status == "forwarded",
        status=record.status,
        message=_message(record),
        registration=record,
        onec_response=onec_response,
        warnings=warnings,
    )


@router.post("/register/preview", response_model=ChzAggregationPreviewResponse)
async def preview_aggregation_json(request: ChzAggregationRegistrationRequest):
    return await service.preview_request(request)


@router.post("/register-file", response_model=ChzAggregationRegistrationResponse)
async def register_aggregation_file(
    file: UploadFile = File(...),
    order_number: str | None = Form(default=None),
    source_system: str = Form(default="External aggregation service"),
    source_document_id: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    record, onec_response, warnings = await service.register_file(
        session,
        await file.read(),
        file_name=file.filename,
        order_number=order_number,
        source_system=source_system,
        source_document_id=source_document_id,
    )
    await session.commit()
    return ChzAggregationRegistrationResponse(
        success=record.status == "forwarded",
        status=record.status,
        message=_message(record),
        registration=record,
        onec_response=onec_response,
        warnings=warnings,
    )


@router.post("/register-file/preview", response_model=ChzAggregationPreviewResponse)
async def preview_aggregation_file(
    file: UploadFile = File(...),
    order_number: str | None = Form(default=None),
    source_system: str = Form(default="External aggregation service"),
    source_document_id: str | None = Form(default=None),
):
    return await service.preview_file(
        await file.read(),
        file_name=file.filename,
        order_number=order_number,
        source_system=source_system,
        source_document_id=source_document_id,
    )


@router.post("/pull-from-dnp", response_model=ChzDnpPullResponse)
async def pull_packed_codes_from_dnp(request: ChzDnpPullRequest, session: AsyncSession = Depends(get_session)):
    result = await service.pull_from_dnp(session, request)
    await session.commit()
    return result


@router.get("/registrations", response_model=list[ChzAggregationRegistrationRead])
async def list_registrations(source_document_id: str | None = None, session: AsyncSession = Depends(get_session)):
    query = select(ChzAggregationRegistration)
    if source_document_id is not None:
        query = query.where(ChzAggregationRegistration.source_document_id == source_document_id)
    result = await session.execute(query.order_by(ChzAggregationRegistration.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/settings", response_model=ChzAggregationSettingsRead)
async def get_settings(session: AsyncSession = Depends(get_session)):
    return await service.read_settings(session)


@router.patch("/settings", response_model=ChzAggregationSettingsRead)
async def patch_settings(payload: ChzAggregationSettingsPatch, session: AsyncSession = Depends(get_session)):
    settings = await service.patch_settings(session, payload)
    await session.commit()
    return settings


def _message(record: ChzAggregationRegistration) -> str:
    if record.status == "forwarded":
        return f"Accepted {record.total_codes} codes in {record.total_aggregates} aggregates and forwarded them to 1C."
    if record.status == "skipped":
        return "Отправка отчётов в 1С выключена в настройках OMH."
    return f"Accepted {record.total_codes} codes in {record.total_aggregates} aggregates, but 1C forward failed."
