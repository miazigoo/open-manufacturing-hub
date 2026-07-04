import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NotificationDeliveryStatus, NotificationTriggerType
from app.core.errors import NotFoundError
from app.notifications import channels
from app.notifications.models import NotificationDelivery, NotificationRule
from app.notifications.repository import get_rule
from app.notifications.schemas import NotificationRuleCreate, NotificationRulePatch
from app.secrets.redaction import is_secret_ref
from app.secrets.service import SecretResolver

logger = logging.getLogger(__name__)


async def create_rule(session: AsyncSession, request: NotificationRuleCreate) -> NotificationRule:
    rule = NotificationRule(name=request.name, enabled=request.enabled, trigger_type=request.trigger_type, filters_json=request.filters, channels_json=request.channels, cooldown_seconds=request.cooldown_seconds)
    session.add(rule)
    await session.flush()
    return rule


async def patch_rule(session: AsyncSession, rule_id: UUID, request: NotificationRulePatch) -> NotificationRule:
    rule = await get_rule(session, rule_id)
    if rule is None:
        raise NotFoundError("Notification rule not found")
    if request.name is not None:
        rule.name = request.name
    if request.enabled is not None:
        rule.enabled = request.enabled
    if request.filters is not None:
        rule.filters_json = request.filters
    if request.channels is not None:
        rule.channels_json = request.channels
    if request.cooldown_seconds is not None:
        rule.cooldown_seconds = request.cooldown_seconds
    await session.flush()
    return rule


def _matches(filters: dict[str, Any], payload: dict[str, Any]) -> bool:
    return all(payload.get(key) == value for key, value in filters.items())


def _channel_address(channel: dict[str, Any]) -> str:
    value = channel.get("url") or channel.get("to") or "unknown"
    if is_secret_ref(value):
        return f"secret:{value['$secret']}"
    return str(value)


async def trigger_notifications(session: AsyncSession, trigger_type: NotificationTriggerType, payload: dict[str, Any]) -> None:
    try:
        result = await session.execute(
            select(NotificationRule).where(
                NotificationRule.enabled.is_(True),
                NotificationRule.trigger_type == trigger_type,
            )
        )
    except Exception:
        logger.exception("Failed to load notification rules for %s", trigger_type)
        return

    for rule in result.scalars().all():
        try:
            if not _matches(rule.filters_json or {}, payload):
                continue
            await deliver_for_rule(session, rule, payload)
        except Exception:
            logger.exception("Notification rule %s failed", rule.id)


async def deliver_for_rule(session: AsyncSession, rule: NotificationRule, payload: dict[str, Any]) -> list[NotificationDelivery]:
    now = datetime.now(timezone.utc)
    last_triggered_at = rule.last_triggered_at
    if last_triggered_at is not None and last_triggered_at.tzinfo is None:
        last_triggered_at = last_triggered_at.replace(tzinfo=timezone.utc)
    in_cooldown = bool(last_triggered_at and (now - last_triggered_at).total_seconds() < rule.cooldown_seconds)
    deliveries: list[NotificationDelivery] = []
    raw_channels = rule.channels_json or []
    resolved_channels = await SecretResolver(session).resolve_value(raw_channels)
    if not isinstance(resolved_channels, list):
        resolved_channels = []
    for index, channel in enumerate(resolved_channels):
        raw_channel = raw_channels[index] if index < len(raw_channels) and isinstance(raw_channels[index], dict) else channel
        channel_type = channel.get("type", "unknown") if isinstance(channel, dict) else "invalid"
        address = _channel_address(raw_channel) if isinstance(raw_channel, dict) else "unknown"
        try:
            if in_cooldown:
                delivery = NotificationDelivery(rule_id=rule.id, trigger_type=rule.trigger_type.value, target_channel=channel_type, target_address=address, status=NotificationDeliveryStatus.SKIPPED_COOLDOWN, request_payload=payload)
            elif channel_type == "webhook":
                url = str(channel.get("url") or "")
                headers = {str(key): str(value) for key, value in (channel.get("headers") or {}).items()} if isinstance(channel.get("headers"), dict) else None
                if headers:
                    ok, response, error = await channels.send_webhook(url, payload, headers=headers)
                else:
                    ok, response, error = await channels.send_webhook(url, payload)
                delivery = NotificationDelivery(rule_id=rule.id, trigger_type=rule.trigger_type.value, target_channel=channel_type, target_address=address, status=NotificationDeliveryStatus.SENT if ok else NotificationDeliveryStatus.FAILED, request_payload=payload, response_payload=response, error_message=error, sent_at=now if ok else None)
            elif channel_type == "email_stub":
                ok, response, error = await channels.send_email_stub(address, payload)
                delivery = NotificationDelivery(rule_id=rule.id, trigger_type=rule.trigger_type.value, target_channel=channel_type, target_address=address, status=NotificationDeliveryStatus.SENT if ok else NotificationDeliveryStatus.FAILED, request_payload=payload, response_payload=response, error_message=error, sent_at=now if ok else None)
            else:
                delivery = NotificationDelivery(rule_id=rule.id, trigger_type=rule.trigger_type.value, target_channel=channel_type, target_address=address, status=NotificationDeliveryStatus.FAILED, request_payload=payload, error_message="Unknown channel")
        except Exception as exc:
            logger.exception("Notification channel %s failed", channel_type)
            delivery = NotificationDelivery(rule_id=rule.id, trigger_type=rule.trigger_type.value, target_channel=channel_type, target_address=address, status=NotificationDeliveryStatus.FAILED, request_payload=payload, error_message=str(exc) or exc.__class__.__name__)
        session.add(delivery)
        deliveries.append(delivery)
    if not in_cooldown:
        rule.last_triggered_at = now
    await session.flush()
    return deliveries


async def test_rule(session: AsyncSession, rule_id: UUID) -> list[NotificationDelivery]:
    rule = await get_rule(session, rule_id)
    if rule is None:
        raise NotFoundError("Notification rule not found")
    return await deliver_for_rule(session, rule, {"test": True, "rule_id": str(rule.id)})
