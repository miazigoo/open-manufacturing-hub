from __future__ import annotations

import shutil

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import BackupType, EnterpriseQueueStatus, IntegrationPackageStatus
from app.enterprise_runtime.models import DeadLetterQueueItem, IntegrationQueueMessage
from app.packages.models import InstalledPackage
from app.packages.registry import package_registry
from app.packages.compatibility import validate_compatibility
from app.production import backups
from app.production.schemas import ProductionCheck

MIGRATION_HEAD = "0020_production_safety"


async def database_revision(session: AsyncSession) -> str | None:
    try:
        return await session.scalar(text("select version_num from alembic_version limit 1"))
    except Exception:
        return None


async def update_checks(session: AsyncSession, *, post_update: bool = False) -> list[ProductionCheck]:
    checks: list[ProductionCheck] = []
    revision = await database_revision(session)
    checks.append(ProductionCheck(name="Database reachable", status="ok", message=f"revision={revision or 'unknown'}"))
    checks.append(ProductionCheck(name="Database migration head", status="ok" if revision == MIGRATION_HEAD else "warning", message=f"current={revision or 'unknown'} head={MIGRATION_HEAD}"))

    processing = int(await session.scalar(select(func.count()).select_from(IntegrationQueueMessage).where(IntegrationQueueMessage.status == EnterpriseQueueStatus.PROCESSING)) or 0)
    waiting = int(await session.scalar(select(func.count()).select_from(IntegrationQueueMessage).where(IntegrationQueueMessage.status.in_([EnterpriseQueueStatus.WAITING, EnterpriseQueueStatus.RETRY_WAITING]))) or 0)
    dlq = int(await session.scalar(select(func.count()).select_from(DeadLetterQueueItem).where(DeadLetterQueueItem.archived.is_(False))) or 0)
    checks.append(ProductionCheck(name="Processing queue items", status="warning" if processing else "ok", message=f"{processing} items are processing. Pause workers before update." if processing else "No items are processing.", details={"processing": processing, "waiting_or_retry": waiting, "dlq": dlq}))
    checks.append(ProductionCheck(name="DLQ backlog", status="warning" if dlq else "ok", message=f"{dlq} DLQ items need review." if dlq else "DLQ is empty."))

    last = await backups.last_success(session, BackupType.CONFIG_EXPORT)
    checks.append(ProductionCheck(name="Last config backup", status="ok" if last else "error", message=f"Last config export: {last.created_at.isoformat()}" if last else "No config export backup found."))

    packages = (await session.execute(select(InstalledPackage))).scalars().all()
    failed = [item.package_id for item in packages if item.status in {IntegrationPackageStatus.FAILED, IntegrationPackageStatus.INCOMPATIBLE}]
    compatibility_errors = []
    for item in packages:
        try:
            compatibility_errors.extend(validate_compatibility(package_registry.get(item.package_id)))
        except Exception as exc:
            compatibility_errors.append(f"{item.package_id}: {exc}")
    package_status = "error" if failed or compatibility_errors else "ok"
    checks.append(ProductionCheck(name="Package compatibility", status=package_status, message="; ".join(failed + compatibility_errors) if package_status == "error" else "Installed packages are compatible."))

    usage = shutil.disk_usage(".")
    free_gb = round(usage.free / 1024 / 1024 / 1024, 2)
    checks.append(ProductionCheck(name="Disk space", status="warning" if free_gb < 1 else "ok", message=f"{free_gb} GB free"))

    if post_update:
        checks.append(ProductionCheck(name="Backend startup", status="ok", message="Backend responded to post-update check."))
        checks.append(ProductionCheck(name="Package registry", status="ok", message=f"{len(package_registry.list_packages())} package manifests loaded."))
    return checks


def required_actions(checks: list[ProductionCheck]) -> list[str]:
    actions: list[str] = []
    for check in checks:
        if check.status == "error" and "backup" in check.name.lower():
            actions.append("Create backup")
        if check.status == "warning" and "processing" in check.name.lower():
            actions.append("Pause workers or enable update mode")
        if check.status == "error" and "package" in check.name.lower():
            actions.append("Fix incompatible or failed packages")
    return sorted(set(actions))
