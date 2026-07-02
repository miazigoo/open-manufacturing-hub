from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.mappings import service
from app.mappings.schemas import (
    MappingCloneRequest,
    MappingCreate,
    MappingDiffRead,
    MappingExecuteRead,
    MappingExecuteRequest,
    MappingPatch,
    MappingRead,
    MappingValidateRequest,
    MappingValidationRead,
    MappingVersionCreate,
    MappingVersionRead,
)

router = APIRouter(tags=["mappings"])


@router.get("/api/mappings", response_model=list[MappingRead])
async def list_mappings(session: AsyncSession = Depends(get_session)):
    return await service.list_mappings(session)


@router.post("/api/mappings", response_model=MappingRead)
async def create_mapping(request: MappingCreate, session: AsyncSession = Depends(get_session)):
    mapping = await service.create_mapping(session, request)
    await session.commit()
    return mapping


@router.get("/api/mappings/{mapping_id}", response_model=MappingRead)
async def get_mapping(mapping_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_mapping_or_404(session, mapping_id)


@router.patch("/api/mappings/{mapping_id}", response_model=MappingRead)
async def patch_mapping(mapping_id: UUID, request: MappingPatch, session: AsyncSession = Depends(get_session)):
    mapping = await service.patch_mapping(session, mapping_id, request)
    await session.commit()
    return mapping


@router.delete("/api/mappings/{mapping_id}", status_code=204)
async def delete_mapping(mapping_id: UUID, session: AsyncSession = Depends(get_session)):
    mapping = await service.get_mapping_or_404(session, mapping_id)
    await session.delete(mapping)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/mappings/validate", response_model=MappingValidationRead)
async def validate_mapping(request: MappingValidateRequest):
    return await service.validate_mapping(request.rules_json, request.sample_payload)


@router.post("/api/mappings/{mapping_id}/versions", response_model=MappingVersionRead)
async def create_mapping_version(mapping_id: UUID, request: MappingVersionCreate, session: AsyncSession = Depends(get_session)):
    version = await service.create_version(session, mapping_id, request)
    await session.commit()
    return version


@router.post("/api/mappings/{mapping_id}/versions/{version}/clone", response_model=MappingVersionRead)
async def clone_mapping_version(mapping_id: UUID, version: int, request: MappingCloneRequest, session: AsyncSession = Depends(get_session)):
    cloned = await service.clone_version(session, mapping_id, version, request)
    await session.commit()
    return cloned


@router.get("/api/mappings/{mapping_id}/compare", response_model=MappingDiffRead)
async def compare_mapping_versions(mapping_id: UUID, left_version: int, right_version: int, session: AsyncSession = Depends(get_session)):
    return await service.diff_versions(session, mapping_id, left_version, right_version)


@router.post("/api/mappings/{mapping_id}/versions/{version}/execute", response_model=MappingExecuteRead)
async def execute_mapping_version(mapping_id: UUID, version: int, request: MappingExecuteRequest, session: AsyncSession = Depends(get_session)):
    output = await service.execute_version(session, mapping_id, version, request.payload)
    return {"output": output}
