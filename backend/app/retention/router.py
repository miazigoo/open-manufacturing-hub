from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.retention import service

router = APIRouter(prefix="/api/retention", tags=["retention"])


@router.get("/preview")
async def preview(session: AsyncSession = Depends(get_session)):
    return await service.preview(session)


@router.post("/cleanup")
async def cleanup(session: AsyncSession = Depends(get_session)):
    result = await service.cleanup_expired(session)
    await session.commit()
    return result
