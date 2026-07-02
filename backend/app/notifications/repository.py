from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import NotificationDelivery, NotificationRule


async def list_rules(session: AsyncSession) -> list[NotificationRule]:
    result = await session.execute(select(NotificationRule).order_by(NotificationRule.created_at.desc()))
    return list(result.scalars().all())


async def get_rule(session: AsyncSession, rule_id: UUID) -> NotificationRule | None:
    return await session.get(NotificationRule, rule_id)


async def list_deliveries(session: AsyncSession) -> list[NotificationDelivery]:
    result = await session.execute(select(NotificationDelivery).order_by(NotificationDelivery.created_at.desc()))
    return list(result.scalars().all())
