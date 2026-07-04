from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.ui import service
from app.ui.schemas import UICockpitOptions, UICockpitSummary, UIFlowBuilderOptions, UIFlowBuilderState, UINavigationItem

router = APIRouter(prefix="/api/ui", tags=["ui"])


@router.get("/navigation", response_model=list[UINavigationItem])
async def navigation(session: AsyncSession = Depends(get_session)):
    return await service.navigation(session)


@router.get("/cockpit/summary", response_model=UICockpitSummary)
async def cockpit_summary(session: AsyncSession = Depends(get_session)):
    return await service.cockpit_summary(session)


@router.get("/cockpit/options", response_model=UICockpitOptions)
async def cockpit_options(session: AsyncSession = Depends(get_session)):
    return await service.cockpit_options(session)


@router.get("/flow-builder/options", response_model=UIFlowBuilderOptions)
async def flow_builder_options(session: AsyncSession = Depends(get_session)):
    return await service.flow_builder_options(session)


@router.get("/flow-builder/{flow_id}/state", response_model=UIFlowBuilderState)
async def flow_builder_state(flow_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.flow_builder_state(session, flow_id)
