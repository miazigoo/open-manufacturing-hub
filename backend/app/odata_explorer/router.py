from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.integration_bus.schemas import ODataLookupTemplateRead
from app.odata_explorer import service
from app.odata_explorer.schemas import ODataLookupCreateRequest, ODataQueryRequest, ODataQueryResponse, ODataResourceList

router = APIRouter(prefix="/api/odata-explorer", tags=["odata-explorer"])

@router.get("/{connector_id}/resources", response_model=ODataResourceList)
async def list_resources(connector_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.resources(session, connector_id)

@router.post("/{connector_id}/query", response_model=ODataQueryResponse)
async def query(connector_id: UUID, request: ODataQueryRequest, session: AsyncSession = Depends(get_session)):
    return await service.query(session, connector_id, request)

@router.post("/{connector_id}/lookups", response_model=ODataLookupTemplateRead)
async def create_lookup(connector_id: UUID, request: ODataLookupCreateRequest, session: AsyncSession = Depends(get_session)):
    template = await service.create_lookup(session, connector_id, request)
    await session.commit()
    return template
