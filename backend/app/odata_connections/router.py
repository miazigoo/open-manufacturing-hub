from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.odata_connections import service
from app.odata_connections.schemas import ODataConnectionCreate, ODataConnectionOption, ODataConnectionPatch, ODataConnectionRead, ODataConnectionTestRequest, ODataConnectionTestResponse

router = APIRouter(prefix="/api/odata-connections", tags=["odata-connections"])


@router.get("", response_model=list[ODataConnectionRead])
async def list_odata_connections(session: AsyncSession = Depends(get_session)):
    return await service.list_connections(session)


@router.get("/options", response_model=list[ODataConnectionOption])
async def odata_connection_options(session: AsyncSession = Depends(get_session)):
    return await service.options(session)


@router.post("", response_model=ODataConnectionRead)
async def create_odata_connection(payload: ODataConnectionCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    connection = await service.create_connection(session, payload)
    await audit_service.record_action(session, request=http_request, action="odata_connection.created", category="connectors", object_type="odata_connection", object_id=connection.id, object_name=connection.name, summary=f"OData connection {connection.name} created")
    await session.commit()
    return connection


@router.get("/{connection_id}", response_model=ODataConnectionRead)
async def get_odata_connection(connection_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_connection(session, connection_id)


@router.patch("/{connection_id}", response_model=ODataConnectionRead)
async def patch_odata_connection(connection_id: UUID, payload: ODataConnectionPatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = await service.get_connection(session, connection_id)
    connection = await service.patch_connection(session, connection_id, payload)
    await audit_service.record_change(session, request=http_request, action="odata_connection.updated", category="connectors", object_type="odata_connection", object_id=connection.id, object_name=connection.name, before=before.model_dump(mode="json"), after=connection.model_dump(mode="json"), summary=f"OData connection {connection.name} updated")
    await session.commit()
    return connection


@router.delete("/{connection_id}", status_code=204)
async def delete_odata_connection(connection_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = await service.get_connection(session, connection_id)
    await service.delete_connection(session, connection_id)
    await audit_service.record_action(session, request=http_request, action="odata_connection.deleted", category="connectors", object_type="odata_connection", object_id=connection_id, object_name=before.name, summary=f"OData connection {before.name} deleted")
    await session.commit()
    return Response(status_code=204)


@router.post("/{connection_id}/test", response_model=ODataConnectionTestResponse)
async def test_odata_connection(connection_id: UUID, payload: ODataConnectionTestRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_connection(session, connection_id, payload)
