from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.mapping_center import service
from app.mapping_center.schemas import (
    InstallMappingPresetsResponse,
    MappingPresetsResponse,
    MappingPreviewRequest,
    MappingProfileCreate,
    MappingProfilePatch,
    MappingProfileRead,
    MappingRenderResponse,
    MappingValidateRequest,
    MappingValidationResponse,
)

router = APIRouter(prefix="/api/mapping-center", tags=["mapping-center"])


@router.get("/mappings", response_model=list[MappingProfileRead])
async def list_mappings(operation_profile_id: UUID | None = None, target_contract_id: UUID | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_mappings(session, operation_profile_id=operation_profile_id, target_contract_id=target_contract_id)


@router.post("/mappings", response_model=MappingProfileRead)
async def create_mapping(payload: MappingProfileCreate, session: AsyncSession = Depends(get_session)):
    mapping = await service.create_mapping(session, payload)
    await session.commit()
    return mapping


@router.get("/mappings/{mapping_id}", response_model=MappingProfileRead)
async def get_mapping(mapping_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_mapping(session, mapping_id)


@router.patch("/mappings/{mapping_id}", response_model=MappingProfileRead)
async def patch_mapping(mapping_id: UUID, payload: MappingProfilePatch, session: AsyncSession = Depends(get_session)):
    mapping = await service.patch_mapping(session, mapping_id, payload)
    await session.commit()
    return mapping


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping(mapping_id: UUID, session: AsyncSession = Depends(get_session)):
    await service.delete_mapping(session, mapping_id)
    await session.commit()
    return Response(status_code=204)


@router.post("/preview", response_model=MappingRenderResponse)
async def preview_mapping(payload: MappingPreviewRequest, session: AsyncSession = Depends(get_session)):
    return await service.preview_mapping(session, payload)


@router.post("/validate", response_model=MappingValidationResponse)
async def validate_mapping(payload: MappingValidateRequest, session: AsyncSession = Depends(get_session)):
    return await service.validate_mapping_request(session, payload)


@router.get("/presets", response_model=MappingPresetsResponse)
async def mapping_presets():
    return await service.presets()


@router.post("/install-presets", response_model=InstallMappingPresetsResponse)
async def install_presets(session: AsyncSession = Depends(get_session)):
    result = await service.install_presets(session)
    await session.commit()
    return result
