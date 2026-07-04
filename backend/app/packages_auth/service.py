from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.core.enums import IntegrationPackageStatus
from app.packages.models import InstalledPackage
from app.packages_auth import repository
from app.packages_auth.models import AuthRecoveryKey, AuthSession, AuthSettings, AuthUser
from app.packages_auth.schemas import AuthSettingsPatch, UserCreate, UserPatch
from app.packages_auth.recovery import generate_recovery_keys
from app.packages_auth.security import hash_password, hash_token, new_session_token, verify_password

AUTH_PACKAGE_ID = "omh-package-auth"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def is_auth_package_enabled(session: AsyncSession) -> bool:
    package = (await session.execute(select(InstalledPackage).where(InstalledPackage.package_id == AUTH_PACKAGE_ID))).scalar_one_or_none()
    return bool(package and package.enabled and package.status == IntegrationPackageStatus.ENABLED)


async def settings(session: AsyncSession) -> AuthSettings:
    return await repository.get_settings(session)


async def state(session: AsyncSession, request: Request | None = None):
    package_enabled = await is_auth_package_enabled(session)
    if not package_enabled:
        return {"auth_available": False, "auth_enabled": False, "requires_login": False, "bootstrap_required": False, "user": None}
    auth_settings = await settings(session)
    users = await repository.user_count(session)
    user = await current_user(session, request) if request is not None else None
    return {"auth_available": True, "auth_enabled": auth_settings.enabled, "requires_login": auth_settings.enabled and auth_settings.protect_ui, "bootstrap_required": users == 0, "user": user}


async def create_user(session: AsyncSession, request: UserCreate) -> tuple[AuthUser, list[str]]:
    username = request.username.strip()
    if not username:
        raise BadRequestError("Username is required")
    if await repository.get_user_by_username(session, username):
        raise BadRequestError("Username already exists")
    user = AuthUser(username=username, display_name=request.display_name, password_hash=hash_password(request.password), enabled=True, password_changed_at=now_utc())
    session.add(user)
    await session.flush()
    keys = await reset_recovery_keys(session, user.id)
    return user, keys


async def bootstrap(session: AsyncSession, request: UserCreate) -> tuple[AuthUser, list[str]]:
    if not await is_auth_package_enabled(session):
        raise BadRequestError("Auth package is not enabled")
    if await repository.user_count(session) != 0:
        raise BadRequestError("Bootstrap is already completed")
    return await create_user(session, request)


async def login(session: AsyncSession, request, http_request: Request, response: Response) -> AuthUser:
    if not await is_auth_package_enabled(session):
        raise BadRequestError("Auth package is not enabled")
    user = await repository.get_user_by_username(session, request.username.strip())
    if user is None or not user.enabled or not verify_password(request.password, user.password_hash):
        raise BadRequestError("Invalid username or password")
    auth_settings = await settings(session)
    token = new_session_token()
    session_row = AuthSession(
        user_id=user.id,
        session_token_hash=hash_token(token),
        expires_at=now_utc() + timedelta(days=max(1, auth_settings.session_ttl_days)),
        user_agent=http_request.headers.get("user-agent"),
        ip_address=http_request.client.host if http_request.client else None,
    )
    user.last_login_at = now_utc()
    session.add(session_row)
    secure = http_request.url.scheme == "https"
    response.set_cookie(auth_settings.cookie_name, token, httponly=True, samesite="lax", secure=secure, max_age=max(1, auth_settings.session_ttl_days) * 86400, path="/")
    await session.flush()
    return user


async def current_session(session: AsyncSession, request: Request | None) -> AuthSession | None:
    if request is None:
        return None
    auth_settings = await settings(session)
    token = request.cookies.get(auth_settings.cookie_name)
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        return None
    item = await repository.get_session_by_hash(session, hash_token(token))
    if item is None or item.revoked_at is not None or as_utc(item.expires_at) <= now_utc():
        return None
    item.last_seen_at = now_utc()
    await session.flush()
    return item


async def current_user(session: AsyncSession, request: Request | None) -> AuthUser | None:
    item = await current_session(session, request)
    if item is None:
        return None
    user = await repository.get_user(session, item.user_id)
    return user if user and user.enabled else None


async def require_user(session: AsyncSession, request: Request) -> AuthUser:
    user = await current_user(session, request)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def logout(session: AsyncSession, request: Request, response: Response) -> None:
    auth_settings = await settings(session)
    item = await current_session(session, request)
    if item is not None:
        item.revoked_at = now_utc()
    response.delete_cookie(auth_settings.cookie_name, path="/")
    await session.flush()


async def change_password(session: AsyncSession, user: AuthUser, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise BadRequestError("Current password is invalid")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now_utc()
    await revoke_user_sessions(session, user.id)
    await session.flush()


async def patch_user(session: AsyncSession, user_id: UUID, request: UserPatch) -> AuthUser:
    user = await repository.get_user(session, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if request.username is not None and request.username.strip() and request.username.strip() != user.username:
        existing = await repository.get_user_by_username(session, request.username.strip())
        if existing and existing.id != user.id:
            raise BadRequestError("Username already exists")
        user.username = request.username.strip()
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.enabled is not None:
        user.enabled = request.enabled
    await session.flush()
    return user


async def set_user_enabled(session: AsyncSession, user_id: UUID, enabled: bool) -> AuthUser:
    user = await repository.get_user(session, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.enabled = enabled
    if not enabled:
        await revoke_user_sessions(session, user.id)
    await session.flush()
    return user


async def reset_recovery_keys(session: AsyncSession, user_id: UUID) -> list[str]:
    user = await repository.get_user(session, user_id)
    if user is None:
        raise NotFoundError("User not found")
    existing = (await session.execute(select(AuthRecoveryKey).where(AuthRecoveryKey.user_id == user_id, AuthRecoveryKey.used_at.is_(None)))).scalars().all()
    for item in existing:
        item.used_at = now_utc()
    keys = generate_recovery_keys()
    for index, key in enumerate(keys, start=1):
        session.add(AuthRecoveryKey(user_id=user_id, key_hash=hash_token(key), label=f"key-{index}"))
    await session.flush()
    return keys


async def recover_password(session: AsyncSession, username: str, recovery_key: str, new_password: str) -> None:
    if not await is_auth_package_enabled(session):
        raise BadRequestError("Auth package is not enabled")
    user = await repository.get_user_by_username(session, username.strip())
    key = await repository.recovery_key_by_hash(session, hash_token(recovery_key.strip()))
    if user is None or key is None or key.user_id != user.id or key.used_at is not None:
        raise BadRequestError("Invalid recovery key")
    key.used_at = now_utc()
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now_utc()
    user.enabled = True
    await revoke_user_sessions(session, user.id)
    await session.flush()


async def revoke_user_sessions(session: AsyncSession, user_id: UUID) -> None:
    rows = (await session.execute(select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)))).scalars().all()
    for row in rows:
        row.revoked_at = now_utc()


async def update_settings(session: AsyncSession, patch: AuthSettingsPatch) -> AuthSettings:
    item = await settings(session)
    if patch.enabled is not None:
        item.enabled = patch.enabled
    if patch.protect_api is not None:
        item.protect_api = patch.protect_api
    if patch.protect_ui is not None:
        item.protect_ui = patch.protect_ui
    if patch.session_ttl_days is not None:
        item.session_ttl_days = max(1, patch.session_ttl_days)
    if patch.cookie_name is not None and patch.cookie_name.strip():
        item.cookie_name = patch.cookie_name.strip()
    await session.flush()
    return item
