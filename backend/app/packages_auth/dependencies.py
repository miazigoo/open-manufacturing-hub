from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.packages_auth import service
from app.packages_auth.models import AuthUser


async def current_user_dep(request: Request, session: AsyncSession = Depends(get_session)) -> AuthUser:
    if not await service.is_auth_package_enabled(session):
        raise HTTPException(status_code=403, detail="Auth package is not enabled")
    user = await service.current_user(session, request)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
