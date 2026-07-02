from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.notifications import repository, service
from app.notifications.schemas import NotificationDeliveryRead, NotificationRuleCreate, NotificationRulePatch, NotificationRuleRead

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/rules", response_model=list[NotificationRuleRead])
async def rules(session: AsyncSession = Depends(get_session)):
    return await repository.list_rules(session)


@router.post("/rules", response_model=NotificationRuleRead)
async def create_rule(request: NotificationRuleCreate, session: AsyncSession = Depends(get_session)):
    rule = await service.create_rule(session, request)
    await session.commit()
    return rule


@router.get("/rules/{rule_id}", response_model=NotificationRuleRead)
async def get_rule(rule_id: UUID, session: AsyncSession = Depends(get_session)):
    rule = await repository.get_rule(session, rule_id)
    if rule is None:
        raise NotFoundError("Notification rule not found")
    return rule


@router.patch("/rules/{rule_id}", response_model=NotificationRuleRead)
async def patch_rule(rule_id: UUID, request: NotificationRulePatch, session: AsyncSession = Depends(get_session)):
    rule = await service.patch_rule(session, rule_id, request)
    await session.commit()
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: UUID, session: AsyncSession = Depends(get_session)):
    rule = await repository.get_rule(session, rule_id)
    if rule is None:
        raise NotFoundError("Notification rule not found")
    await session.delete(rule)
    await session.commit()
    return Response(status_code=204)


@router.post("/rules/{rule_id}/test", response_model=list[NotificationDeliveryRead])
async def test_rule(rule_id: UUID, session: AsyncSession = Depends(get_session)):
    deliveries = await service.test_rule(session, rule_id)
    await session.commit()
    return deliveries


@router.get("/deliveries", response_model=list[NotificationDeliveryRead])
async def deliveries(session: AsyncSession = Depends(get_session)):
    return await repository.list_deliveries(session)
