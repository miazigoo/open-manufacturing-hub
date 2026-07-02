from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.health.models import HealthCheck, Site


async def get_site_by_code(session: AsyncSession, code: str) -> Site | None:
    result = await session.execute(select(Site).where(Site.code == code))
    return result.scalar_one_or_none()


async def latest_checks(session: AsyncSession) -> list[HealthCheck]:
    result = await session.execute(select(HealthCheck).order_by(HealthCheck.checked_at.desc()))
    checks = list(result.scalars().all())
    seen: set[tuple[str, str, str | None]] = set()
    latest = []
    for check in checks:
        key = (check.component_type.value if hasattr(check.component_type, "value") else check.component_type, check.component_name, str(check.site_id) if check.site_id else None)
        if key not in seen:
            seen.add(key)
            latest.append(check)
    return latest
