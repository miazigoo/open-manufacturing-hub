from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.database import async_session
from app.packages_auth import service as auth_service

PUBLIC_PREFIXES = (
    "/api/auth/state",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/bootstrap",
    "/api/auth/recover-password",
    "/api/bus/in/",
    "/api/webhooks/",
    "/api/mock-onec/",
)
PUBLIC_EXACT = {"/api/health", "/api/health/live", "/api/health/ready", "/live", "/ready", "/docs", "/openapi.json", "/redoc"}


async def optional_auth_guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if _is_public(path) or not path.startswith("/api/"):
        return await call_next(request)

    # Perform auth check in a dedicated short-lived session and close it before call_next
    user = None
    async with async_session() as session:
        try:
            if not await auth_service.is_auth_package_enabled(session):
                pass
            else:
                settings = await auth_service.settings(session)
                if not settings.enabled or not settings.protect_api:
                    pass
                else:
                    state = await auth_service.state(session, request)
                    if state.get("bootstrap_required"):
                        return JSONResponse(status_code=401, content={"detail": "Bootstrap required"})
                    user = await auth_service.current_user(session, request)
                    if user is None:
                        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    if user is not None:
        request.state.current_user = user

    # Hand off to route handler with session completely closed and freed back to the pool
    return await call_next(request)


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
