from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.test_console.models import SavedTestCase


async def list_test_cases(session: AsyncSession) -> list[SavedTestCase]:
    result = await session.execute(select(SavedTestCase).order_by(SavedTestCase.updated_at.desc(), SavedTestCase.name.asc()))
    return list(result.scalars().all())


async def get_test_case(session: AsyncSession, test_case_id: UUID) -> SavedTestCase | None:
    return await session.get(SavedTestCase, test_case_id)
