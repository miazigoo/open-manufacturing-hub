from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.plugin_store import service
from app.plugin_store.schemas import PluginStoreCategory, PluginStoreItem

router = APIRouter(prefix="/api/plugin-store", tags=["plugin-store"])


@router.get("/catalog", response_model=list[PluginStoreItem])
async def catalog(session: AsyncSession = Depends(get_session)):
    return await service.catalog(session)


@router.get("/categories", response_model=list[PluginStoreCategory])
async def categories(session: AsyncSession = Depends(get_session)):
    return await service.categories(session)
