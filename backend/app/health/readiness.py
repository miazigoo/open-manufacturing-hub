from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import HealthComponentType
from app.health.models import HealthCheck
from app.packages.registry import package_registry
from app.production.checks import MIGRATION_HEAD, database_revision

WORKER_HEALTH_NAME = "queue-worker"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def live() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "app_env": settings.app_env,
        "version": settings.app_version,
        "generated_at": utcnow().isoformat(),
    }


async def ready(session: AsyncSession) -> dict[str, Any]:
    settings = get_settings()
    checks: list[dict[str, Any]] = []

    try:
        await session.execute(text("SELECT 1"))
        checks.append({"name": "database", "status": "ok", "message": "connection ok"})
    except Exception as exc:
        checks.append({"name": "database", "status": "error", "message": str(exc)})
        return _payload(checks)

    revision = await database_revision(session)
    production_mode = settings.app_env.lower() in {"production", "prod"}
    migration_ok = (revision == MIGRATION_HEAD)
    migration_status = "ok" if migration_ok else ("error" if production_mode else "warning")
    checks.append(
        {
            "name": "migrations",
            "status": migration_status,
            "message": f"current={revision or 'unknown'} head={MIGRATION_HEAD}",
        }
    )
    checks.append({"name": "package_registry", "status": "ok", "message": f"{len(package_registry.list_packages())} manifests loaded"})

    production_mode = settings.app_env.lower() in {"production", "prod"}
    if production_mode and not settings.secret_key:
        checks.append({"name": "secret_key", "status": "error", "message": "OMH_SECRET_KEY is required in production"})
    elif settings.secret_key:
        checks.append({"name": "secret_key", "status": "ok", "message": "configured"})
    else:
        checks.append({"name": "secret_key", "status": "warning", "message": "development fallback key is active"})

    if settings.require_worker_heartbeat:
        checks.append(await worker_heartbeat_check(session))

    return _payload(checks)


async def worker_heartbeat_check(session: AsyncSession, worker: str | None = None) -> dict[str, Any]:
    stmt = select(HealthCheck).where(
        HealthCheck.component_type == HealthComponentType.AGENT, HealthCheck.component_name == WORKER_HEALTH_NAME
    )
    if worker:
        stmt = stmt.where(HealthCheck.details_json["worker"].as_string() == worker)
    result = await session.execute(stmt.order_by(HealthCheck.checked_at.desc(), HealthCheck.id.desc()).limit(1))
    item = result.scalar_one_or_none()
    if item is None:
        return {"name": "worker_heartbeat", "status": "error", "message": "No queue worker heartbeat found"}
    age = max(0, int((utcnow() - _aware(item.checked_at)).total_seconds()))
    return {
        "name": "worker_heartbeat",
        "status": "ok" if age <= 180 and item.status.value == "ok" else "error",
        "message": f"last heartbeat {age}s ago, status={item.status.value}",
        "details": item.details_json or {},
    }


def _payload(checks: list[dict[str, Any]]) -> dict[str, Any]:
    errors = sum(1 for item in checks if item["status"] == "error")
    warnings = sum(1 for item in checks if item["status"] == "warning")
    return {
        "status": "error" if errors else "warning" if warnings else "ok",
        "generated_at": utcnow().isoformat(),
        "checks": checks,
    }


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
