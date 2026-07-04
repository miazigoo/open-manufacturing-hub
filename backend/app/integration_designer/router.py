from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.integration_designer import service
from app.integration_designer.schemas import DesignerBuildRequest, DesignerBuildResponse

router = APIRouter(prefix="/api/integration-designer", tags=["integration-designer"])

@router.post("/build", response_model=DesignerBuildResponse)
async def build(request: DesignerBuildRequest, session: AsyncSession = Depends(get_session)):
    result = await service.build(session, request)
    await session.commit()
    return result
