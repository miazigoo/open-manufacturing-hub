from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.packages_auth.models import AuthRecoveryKey, AuthSession, AuthSettings, AuthUser


async def user_count(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count(AuthUser.id)))).scalar_one())


async def get_user_by_username(session: AsyncSession, username: str) -> AuthUser | None:
    return (await session.execute(select(AuthUser).where(func.lower(AuthUser.username) == username.lower()))).scalar_one_or_none()


async def get_user(session: AsyncSession, user_id: UUID) -> AuthUser | None:
    return await session.get(AuthUser, user_id)


async def list_users(session: AsyncSession) -> list[AuthUser]:
    return list((await session.execute(select(AuthUser).order_by(AuthUser.username))).scalars().all())


async def get_settings(session: AsyncSession) -> AuthSettings:
    settings = await session.get(AuthSettings, "default")
    if settings is None:
        settings = AuthSettings(id="default")
        session.add(settings)
        await session.flush()
    return settings


async def get_session_by_hash(session: AsyncSession, token_hash: str) -> AuthSession | None:
    return (await session.execute(select(AuthSession).where(AuthSession.session_token_hash == token_hash))).scalar_one_or_none()


async def list_sessions(session: AsyncSession) -> list[AuthSession]:
    return list((await session.execute(select(AuthSession).order_by(AuthSession.created_at.desc()))).scalars().all())


async def get_session(session: AsyncSession, session_id: UUID) -> AuthSession | None:
    return await session.get(AuthSession, session_id)


async def recovery_key_by_hash(session: AsyncSession, key_hash: str) -> AuthRecoveryKey | None:
    return (await session.execute(select(AuthRecoveryKey).where(AuthRecoveryKey.key_hash == key_hash))).scalar_one_or_none()
