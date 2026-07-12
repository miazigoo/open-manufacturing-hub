from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.operation_catalog import service
from app.operation_catalog.schemas import InstallPresetsResponse, OperationCatalogOptions, OperationProfileCreate, OperationProfileOption, OperationProfilePatch, OperationProfileRead, OperationTestRequest, OperationTestResponse
from app.operation_catalog.testers import test_operation

router = APIRouter(prefix="/api/operation-catalog", tags=["operation-catalog"])


@router.get("/operations", response_model=list[OperationProfileRead])
async def list_operations(kind: str | None = None, connection_profile_id: UUID | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_operations(session, kind=kind, connection_profile_id=connection_profile_id)  # type: ignore[arg-type]


@router.post("/operations", response_model=OperationProfileRead)
async def create_operation(payload: OperationProfileCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    operation = await service.create_operation(session, payload)
    await audit_service.record_action(session, request=http_request, action="operation_profile.created", category="connectors", object_type="operation_profile", object_id=operation.id, object_name=operation.name, summary=f"Operation profile {operation.name} created", details={"code": operation.code, "kind": operation.kind, "connection_profile_id": str(operation.connection_profile_id) if operation.connection_profile_id else None})
    await session.commit()
    return operation


@router.get("/operations/{operation_id}", response_model=OperationProfileRead)
async def get_operation(operation_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_operation(session, operation_id)


@router.patch("/operations/{operation_id}", response_model=OperationProfileRead)
async def patch_operation(operation_id: UUID, payload: OperationProfilePatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = await service.get_operation(session, operation_id)
    operation = await service.patch_operation(session, operation_id, payload)
    await audit_service.record_change(session, request=http_request, action="operation_profile.updated", category="connectors", object_type="operation_profile", object_id=operation.id, object_name=operation.name, before=before.model_dump(mode="json"), after=operation.model_dump(mode="json"), summary=f"Operation profile {operation.name} updated")
    await session.commit()
    return operation


@router.delete("/operations/{operation_id}", status_code=204)
async def delete_operation(operation_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = await service.get_operation(session, operation_id)
    await service.delete_operation(session, operation_id)
    await audit_service.record_action(session, request=http_request, action="operation_profile.deleted", category="connectors", object_type="operation_profile", object_id=before.id, object_name=before.name, summary=f"Operation profile {before.name} deleted")
    await session.commit()
    return Response(status_code=204)


@router.post("/operations/{operation_id}/test", response_model=OperationTestResponse)
async def test_operation_profile(operation_id: UUID, payload: OperationTestRequest, session: AsyncSession = Depends(get_session)):
    operation = await service.get_operation_or_404(session, operation_id)
    result = await test_operation(session, operation, payload)
    await session.commit()
    return result


@router.post("/operations/{operation_id}/enable", response_model=OperationProfileRead)
async def enable_operation(operation_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    operation = await service.set_enabled(session, operation_id, True)
    await audit_service.record_action(session, request=http_request, action="operation_profile.enabled", category="connectors", object_type="operation_profile", object_id=operation.id, object_name=operation.name, summary=f"Operation profile {operation.name} enabled")
    await session.commit()
    return operation


@router.post("/operations/{operation_id}/disable", response_model=OperationProfileRead)
async def disable_operation(operation_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    operation = await service.set_enabled(session, operation_id, False)
    await audit_service.record_action(session, request=http_request, action="operation_profile.disabled", category="connectors", object_type="operation_profile", object_id=operation.id, object_name=operation.name, summary=f"Operation profile {operation.name} disabled")
    await session.commit()
    return operation


@router.get("/options", response_model=OperationCatalogOptions)
async def operation_options(session: AsyncSession = Depends(get_session)):
    return await service.options_bundle(session)


@router.get("/options/rest", response_model=list[OperationProfileOption])
async def rest_operation_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, kinds={"rest_api_operation", "training_operation"})


@router.get("/options/onec-http", response_model=list[OperationProfileOption])
async def onec_http_operation_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, kinds={"onec_http_operation", "training_operation"})


@router.post("/install-presets", response_model=InstallPresetsResponse)
async def install_presets(session: AsyncSession = Depends(get_session)):
    result = await service.install_presets(session)
    await session.commit()
    return result
