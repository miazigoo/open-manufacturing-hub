from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import repository
from app.audit.diff import json_diff, redact_secrets
from app.audit.models import AuditEvent
from app.core.config import get_settings
from app.core.enums import AuditActorType, AuditSeverity


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def snapshot_model(obj: Any) -> dict[str, Any]:
    mapper = sa_inspect(obj).mapper
    return redact_secrets({column.key: getattr(obj, column.key) for column in mapper.column_attrs})


async def actor_from_request(session: AsyncSession, request: Request | None) -> dict[str, Any]:
    if request is None:
        return {"actor_type": AuditActorType.SYSTEM}
    try:
        from app.packages_auth.service import current_user, is_auth_package_enabled

        if await is_auth_package_enabled(session):
            user = await current_user(session, request)
            if user is not None:
                return {"actor_type": AuditActorType.USER, "actor_user_id": user.id, "actor_username": user.username, "actor_display_name": user.display_name}
    except Exception:
        pass
    return {"actor_type": AuditActorType.UNKNOWN}


async def record_action(
    session: AsyncSession,
    *,
    request: Request | None = None,
    actor: dict[str, Any] | None = None,
    action: str,
    category: str,
    summary: str,
    severity: AuditSeverity | str = AuditSeverity.INFO,
    object_type: str | None = None,
    object_id: str | UUID | None = None,
    object_name: str | None = None,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    event_id: UUID | None = None,
    queue_item_id: UUID | None = None,
    package_id: str | None = None,
) -> AuditEvent:
    actor_data = actor or await actor_from_request(session, request)
    event = AuditEvent(
        actor_user_id=actor_data.get("actor_user_id"),
        actor_username=actor_data.get("actor_username"),
        actor_display_name=actor_data.get("actor_display_name"),
        actor_type=actor_data.get("actor_type") or AuditActorType.UNKNOWN,
        source_ip=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        action=action,
        category=category,
        severity=severity,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        object_name=object_name,
        summary=summary,
        details_json=redact_secrets(details) if details is not None else None,
        request_id=getattr(getattr(request, "state", None), "request_id", None) if request else None,
        correlation_id=correlation_id,
        event_id=event_id,
        queue_item_id=queue_item_id,
        package_id=package_id,
    )
    session.add(event)
    await session.flush()
    return event


async def record_change(
    session: AsyncSession,
    *,
    request: Request | None = None,
    actor: dict[str, Any] | None = None,
    action: str,
    category: str,
    object_type: str,
    object_id: str | UUID | None,
    object_name: str | None,
    before: Any,
    after: Any,
    summary: str,
    severity: AuditSeverity | str = AuditSeverity.INFO,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    event_id: UUID | None = None,
    queue_item_id: UUID | None = None,
    package_id: str | None = None,
) -> AuditEvent:
    before_clean = redact_secrets(before or {})
    after_clean = redact_secrets(after or {})
    event = await record_action(
        session,
        request=request,
        actor=actor,
        action=action,
        category=category,
        object_type=object_type,
        object_id=object_id,
        object_name=object_name,
        summary=summary,
        severity=severity,
        details=details,
        correlation_id=correlation_id,
        event_id=event_id,
        queue_item_id=queue_item_id,
        package_id=package_id,
    )
    event.before_json = before_clean
    event.after_json = after_clean
    event.diff_json = json_diff(before_clean, after_clean)
    await session.flush()
    return event


async def cleanup(session: AsyncSession, *, retention_days: int | None = None, dry_run: bool = False):
    days = retention_days or get_settings().audit_retention_days
    cutoff = utcnow() - timedelta(days=days)
    deleted = await repository.cleanup_before(session, cutoff, dry_run=dry_run)
    return {"retention_days": days, "cutoff": cutoff, "deleted": deleted, "dry_run": dry_run}
