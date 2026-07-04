from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.config import get_settings
from app.core.enums import BackupType, EnterpriseQueueStatus
from app.enterprise_runtime.models import DeadLetterQueueItem, IntegrationQueueMessage
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute
from app.integration_flows.models import IntegrationFlow
from app.mappings.models import MappingDefinition
from app.packages.models import InstalledPackage
from app.packages_auth.models import AuthUser
from app.production import backups, checks, export_import, snapshots, update_safety
from app.production.models import BackupRecord
from app.production.schemas import ExportConfigRequest, ImportConfigRequest, ProductionCheck
from app.workflows.models import Workflow


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def status(session: AsyncSession) -> dict[str, Any]:
    settings = get_settings()
    warnings = await production_warnings(session)
    packages = [snapshots.package_row(item) for item in (await session.execute(select(InstalledPackage).order_by(InstalledPackage.package_id))).scalars().all()]
    state = await update_safety.state(session)
    return {
        "app_env": settings.app_env,
        "production_mode": settings.app_env == "production",
        "version": snapshots.app_version(),
        "database_revision": await checks.database_revision(session),
        "packages": packages,
        "warnings": warnings,
        "update_mode_enabled": state.update_mode_enabled,
    }


async def snapshot(session: AsyncSession) -> dict[str, Any]:
    settings = get_settings()
    queue = await queue_counts(session)
    packages = [snapshots.package_row(item) for item in (await session.execute(select(InstalledPackage).order_by(InstalledPackage.package_id))).scalars().all()]
    last = await backups.last_success(session)
    warnings = await production_warnings(session)
    state = await update_safety.state(session)
    return {
        "app_version": snapshots.app_version(),
        "backend_version": snapshots.app_version(),
        "frontend_version": snapshots.frontend_version(),
        "app_env": settings.app_env,
        "production_mode": settings.app_env == "production",
        "database_revision": await checks.database_revision(session),
        "migration_head": checks.MIGRATION_HEAD,
        "packages": packages,
        "counts": {
            "connectors": await _count(session, ConnectorInstance),
            "endpoints": await _count(session, IntegrationEndpoint),
            "routes": await _count(session, IntegrationRoute),
            "workflows": await _count(session, Workflow),
            "integration_flows": await _count(session, IntegrationFlow),
            "mappings": await _count(session, MappingDefinition),
        },
        "queue": queue,
        "dlq_count": queue.get("dlq", 0),
        "auth_users_count": await _count_optional(session, AuthUser),
        "last_backup_at": last.created_at if last else None,
        "health": {"queue": queue, "status": "warning" if warnings else "ok"},
        "warnings": warnings,
        "update_mode": update_safety.as_status(state),
    }


async def production_warnings(session: AsyncSession) -> list[str]:
    warnings: list[str] = []
    settings = get_settings()
    auth_package = (await session.execute(select(InstalledPackage).where(InstalledPackage.package_id == "omh-package-auth"))).scalar_one_or_none()
    if settings.app_env == "production" and not (auth_package and auth_package.enabled):
        warnings.append("Auth package is not enabled")
    if not await backups.recent_success_exists(session, 24):
        warnings.append("No backup created in last 24 hours")
    queue = await queue_counts(session)
    if queue.get("dlq", 0):
        warnings.append("DLQ is not empty")
    state = await update_safety.state(session)
    if state.update_mode_enabled:
        warnings.append("Update mode enabled. New requests are queued but not processed.")
    return warnings


async def export_config(session: AsyncSession, request: ExportConfigRequest) -> tuple[BackupRecord, dict[str, Any]]:
    record = await backups.create_record(session, BackupType.CONFIG_EXPORT, created_by=request.created_by, metadata={"secrets_policy": request.secrets_policy})
    try:
        warnings = [export_import.export_warning()]
        payload = {
            "omh_export_version": 1,
            "created_at": utcnow().isoformat(),
            "app_version": snapshots.app_version(),
            "environment": get_settings().app_env,
            "packages": [snapshots.package_row(item) for item in (await session.execute(select(InstalledPackage).order_by(InstalledPackage.package_id))).scalars().all()],
            "objects": await export_import.export_objects(session, secrets_policy=request.secrets_policy),
            "secrets_policy": request.secrets_policy,
            "warnings": warnings,
        }
        file_name = f"omh-config-export-{utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        path = backups.ensure_export_dir() / file_name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        size = path.stat().st_size
        await backups.mark_success(session, record, file_path=str(path), size_bytes=size, metadata={"file_name": file_name})
        return record, {"export_id": record.id, "file_name": file_name, "size_bytes": size, "warnings": warnings, "download_url": f"/api/production/exports/{record.id}/download"}
    except Exception as exc:
        await backups.mark_failed(session, record, str(exc))
        raise


async def import_preview(session: AsyncSession, request: ImportConfigRequest) -> dict[str, Any]:
    return export_import.preview_import(request.export, request.mode, await export_import.existing_identities(session))


async def import_apply(session: AsyncSession, request: ImportConfigRequest) -> dict[str, Any]:
    return await export_import.apply_import(session, request.export, request.mode)


async def pre_update_check(session: AsyncSession) -> dict[str, Any]:
    return await _check_response(session, post_update=False)


async def post_update_check(session: AsyncSession) -> dict[str, Any]:
    return await _check_response(session, post_update=True)


async def _check_response(session: AsyncSession, *, post_update: bool) -> dict[str, Any]:
    items = await checks.update_checks(session, post_update=post_update)
    actions = checks.required_actions(items)
    return {"safe_to_update": not any(item.status == "error" for item in items), "checks": items, "required_actions": actions}


async def queue_counts(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(select(IntegrationQueueMessage.status, func.count()).group_by(IntegrationQueueMessage.status))
    counts = {status.value if hasattr(status, "value") else str(status): int(count) for status, count in result.all()}
    dlq = await session.scalar(select(func.count()).select_from(DeadLetterQueueItem).where(DeadLetterQueueItem.archived.is_(False)))
    counts["dlq"] = int(dlq or counts.get("dlq", 0))
    for status in EnterpriseQueueStatus:
        counts.setdefault(status.value, 0)
    return counts


async def worker_status(session: AsyncSession) -> dict[str, Any]:
    state = await update_safety.state(session)
    return {"paused": state.update_mode_enabled, "update_mode": update_safety.as_status(state), "queue": await queue_counts(session)}


async def enable_update_mode(session: AsyncSession, *, message: str | None, enabled_by: str | None) -> dict[str, Any]:
    item = await update_safety.enable(session, message=message, enabled_by=enabled_by)
    return update_safety.as_status(item)


async def disable_update_mode(session: AsyncSession) -> dict[str, Any]:
    item = await update_safety.disable(session)
    return update_safety.as_status(item)


async def _count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def _count_optional(session: AsyncSession, model: type) -> int | None:
    try:
        return await _count(session, model)
    except Exception:
        return None


def export_path(record: BackupRecord) -> Path:
    return Path(record.file_path or "")
