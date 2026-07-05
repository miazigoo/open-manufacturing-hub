from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.onboarding.models import OnboardingState


async def get_state(session: AsyncSession, key: str) -> OnboardingState | None:
    result = await session.execute(select(OnboardingState).where(OnboardingState.key == key))
    return result.scalar_one_or_none()


async def list_states(session: AsyncSession) -> list[OnboardingState]:
    result = await session.execute(select(OnboardingState).order_by(OnboardingState.created_at.asc()))
    return list(result.scalars().all())
