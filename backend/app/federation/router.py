from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.federation import service
from app.federation.service import FederationAuthError

router = APIRouter(prefix="/api/federation", tags=["federation"])


@router.get("/config-bundle")
async def config_bundle(request: Request, session: AsyncSession = Depends(get_session)):
    token = request.headers.get("x-omh-token")
    try:
        return await service.serve_bundle(session, token)
    except FederationAuthError as exc:
        return JSONResponse(status_code=403, content={"ok": False, "message": str(exc)})


@router.get("/status")
async def status(session: AsyncSession = Depends(get_session)):
    return await service.federation_status(session)


@router.get("/runs")
async def runs(limit: int = Query(default=20, ge=1, le=100), session: AsyncSession = Depends(get_session)):
    return await service.list_runs(session, limit=limit)


@router.post("/sync-now")
async def sync_now(session: AsyncSession = Depends(get_session)):
    result = await service.sync_from_center(session, triggered_by="manual")
    await session.commit()
    return result
