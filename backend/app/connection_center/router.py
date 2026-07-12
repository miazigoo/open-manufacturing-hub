from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.connection_center import service
from app.connection_center.schemas import ConnectionCenterOptions, ConnectionProfileCreate, ConnectionProfileOption, ConnectionProfilePatch, ConnectionProfileRead, ConnectionProfileTestRequest, ConnectionProfileTestResponse
from app.connection_center.testers import test_profile, update_connector_health
from app.core.database import get_session

router = APIRouter(prefix="/api/connection-center", tags=["connection-center"])


@router.get("/profiles", response_model=list[ConnectionProfileRead])
async def list_profiles(kind: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_profiles(session, kind)  # type: ignore[arg-type]


@router.post("/profiles", response_model=ConnectionProfileRead)
async def create_profile(payload: ConnectionProfileCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    profile = await service.create_profile(session, payload)
    await audit_service.record_action(session, request=http_request, action="connection_profile.created", category="connectors", object_type="connection_profile", object_id=profile.connector_id, object_name=profile.name, summary=f"Connection profile {profile.name} created", details={"profile_id": profile.id, "kind": profile.kind})
    await session.commit()
    return profile


@router.get("/profiles/{profile_id:path}", response_model=ConnectionProfileRead)
async def get_profile(profile_id: str, session: AsyncSession = Depends(get_session)):
    return await service.get_profile(session, profile_id)


@router.patch("/profiles/{profile_id:path}", response_model=ConnectionProfileRead)
async def patch_profile(profile_id: str, payload: ConnectionProfilePatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = await service.get_profile(session, profile_id)
    profile = await service.patch_profile(session, profile_id, payload)
    await audit_service.record_change(session, request=http_request, action="connection_profile.updated", category="connectors", object_type="connection_profile", object_id=profile.connector_id, object_name=profile.name, before=before.model_dump(mode="json"), after=profile.model_dump(mode="json"), summary=f"Connection profile {profile.name} updated")
    await session.commit()
    return profile


@router.delete("/profiles/{profile_id:path}", status_code=204)
async def delete_profile(profile_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = await service.get_profile(session, profile_id)
    await service.delete_profile(session, profile_id)
    await audit_service.record_action(session, request=http_request, action="connection_profile.deleted", category="connectors", object_type="connection_profile", object_id=before.connector_id, object_name=before.name, summary=f"Connection profile {before.name} deleted", details={"profile_id": before.id, "kind": before.kind})
    await session.commit()
    return Response(status_code=204)


@router.post("/profiles/{profile_id:path}/test", response_model=ConnectionProfileTestResponse)
async def test_connection_profile(profile_id: str, payload: ConnectionProfileTestRequest, session: AsyncSession = Depends(get_session)):
    connector, kind, canonical_profile_id = await service.get_connector_for_test(session, profile_id)
    result = await test_profile(session, connector, kind, canonical_profile_id, payload)
    update_connector_health(connector, result)
    await session.commit()
    return result


@router.post("/profiles/{profile_id:path}/enable", response_model=ConnectionProfileRead)
async def enable_profile(profile_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    profile = await service.set_enabled(session, profile_id, True)
    await audit_service.record_action(session, request=http_request, action="connection_profile.enabled", category="connectors", object_type="connection_profile", object_id=profile.connector_id, object_name=profile.name, summary=f"Connection profile {profile.name} enabled", details={"profile_id": profile.id})
    await session.commit()
    return profile


@router.post("/profiles/{profile_id:path}/disable", response_model=ConnectionProfileRead)
async def disable_profile(profile_id: str, http_request: Request, session: AsyncSession = Depends(get_session)):
    profile = await service.set_enabled(session, profile_id, False)
    await audit_service.record_action(session, request=http_request, action="connection_profile.disabled", category="connectors", object_type="connection_profile", object_id=profile.connector_id, object_name=profile.name, summary=f"Connection profile {profile.name} disabled", details={"profile_id": profile.id})
    await session.commit()
    return profile


@router.get("/options", response_model=ConnectionCenterOptions)
async def connection_options(session: AsyncSession = Depends(get_session)):
    return await service.options_bundle(session)


@router.get("/options/odata", response_model=list[ConnectionProfileOption])
async def odata_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, {"onec_odata"})


@router.get("/options/onec-http", response_model=list[ConnectionProfileOption])
async def onec_http_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, {"onec_http_service"})


@router.get("/options/rest", response_model=list[ConnectionProfileOption])
async def rest_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, {"rest_api", "training_mock"})


@router.get("/options/printers", response_model=list[ConnectionProfileOption])
async def printer_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, {"printer"})


@router.get("/options/file-targets", response_model=list[ConnectionProfileOption])
async def file_target_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session, {"smb_share", "local_directory"})
