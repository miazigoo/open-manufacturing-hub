from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.packages.models import InstalledPackage


async def list_installed(session: AsyncSession) -> list[InstalledPackage]:
    result = await session.execute(select(InstalledPackage).order_by(InstalledPackage.name.asc()))
    return list(result.scalars().all())


async def get_installed(session: AsyncSession, package_id: str) -> InstalledPackage | None:
    result = await session.execute(select(InstalledPackage).where(InstalledPackage.package_id == package_id))
    return result.scalar_one_or_none()
