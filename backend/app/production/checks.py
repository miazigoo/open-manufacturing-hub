from __future__ import annotations

import shutil

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.config import get_settings
from app.core.enums import BackupType, EnterpriseQueueStatus, IntegrationPackageStatus
from app.enterprise_runtime.models import DeadLetterQueueItem, IntegrationQueueMessage
from app.integration_bus.models import IntegrationEndpoint
from app.notifications.models import NotificationRule
from app.packages.models import InstalledPackage
from app.packages.registry import package_registry
from app.packages.compatibility import validate_compatibility
from app.production import backups
from app.production.schemas import ProductionCheck
from app.resolvers.models import ResolverDefinitionV2
from app.secrets.models import Secret
from app.secrets.redaction import collect_secret_references, raw_secret_warnings

MIGRATION_HEAD = "0022_secrets_store"


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

    checks.extend(await _secret_checks(session))

    usage = shutil.disk_usage(".")
    free_gb = round(usage.free / 1024 / 1024 / 1024, 2)
    checks.append(ProductionCheck(name="Disk space", status="warning" if free_gb < 1 else "ok", message=f"{free_gb} GB free"))

    if post_update:
        checks.append(ProductionCheck(name="Backend startup", status="ok", message="Backend responded to post-update check."))
        checks.append(ProductionCheck(name="Package registry", status="ok", message=f"{len(package_registry.list_packages())} package manifests loaded."))
    return checks


async def _secret_checks(session: AsyncSession) -> list[ProductionCheck]:
    checks: list[ProductionCheck] = []
    settings = get_settings()
    production_mode = settings.app_env.lower() in {"production", "prod"}
    if production_mode and not settings.secret_key:
        checks.append(ProductionCheck(name="Secrets encryption key", status="error", message="OMH_SECRET_KEY is required in production."))
    elif not settings.secret_key:
        checks.append(ProductionCheck(name="Secrets encryption key", status="warning", message="OMH_SECRET_KEY is not set; development fallback key is active."))
    else:
        checks.append(ProductionCheck(name="Secrets encryption key", status="ok", message="OMH_SECRET_KEY is configured."))

    try:
        secrets = (await session.execute(select(Secret))).scalars().all()
    except Exception as exc:
        checks.append(ProductionCheck(name="Secrets Store schema", status="warning", message=f"Secrets table is not available yet: {exc.__class__.__name__}. Run database migrations."))
        secrets = []
    secrets_by_name = {item.name: item for item in secrets}
    raw_warnings: list[str] = []
    reference_errors: list[str] = []
    for label, config in await _secret_config_sources(session):
        for warning in raw_secret_warnings(config):
            raw_warnings.append(f"{label}: {warning}")
        for name, path in collect_secret_references(config):
            secret = secrets_by_name.get(name)
            if secret is None:
                reference_errors.append(f"{label}:{path} -> missing secret {name}")
            elif not secret.enabled:
                reference_errors.append(f"{label}:{path} -> disabled secret {name}")

    checks.append(
        ProductionCheck(
            name="Raw secret values in config",
            status="warning" if raw_warnings else "ok",
            message=f"{len(raw_warnings)} raw password/token values should be moved to Secrets Store." if raw_warnings else "No raw secret-looking config values found.",
            details={"warnings": raw_warnings[:50]},
        )
    )
    checks.append(
        ProductionCheck(
            name="Secret references",
            status="error" if reference_errors else "ok",
            message=f"{len(reference_errors)} missing or disabled secret references." if reference_errors else "All secret references are available and enabled.",
            details={"errors": reference_errors[:50]},
        )
    )
    return checks


async def _secret_config_sources(session: AsyncSession) -> list[tuple[str, dict | list]]:
    sources: list[tuple[str, dict | list]] = []
    connectors = (await session.execute(select(ConnectorInstance))).scalars().all()
    sources.extend((f"connector:{item.name}", item.config_json or {}) for item in connectors)
    endpoints = (await session.execute(select(IntegrationEndpoint))).scalars().all()
    sources.extend((f"endpoint:{item.slug}", item.auth_config_json or {}) for item in endpoints)
    notifications = (await session.execute(select(NotificationRule))).scalars().all()
    sources.extend((f"notification:{item.name}", item.channels_json or []) for item in notifications)
    resolvers = (await session.execute(select(ResolverDefinitionV2))).scalars().all()
    sources.extend((f"resolver:{item.resolver_code}", item.config_json or {}) for item in resolvers)
    return sources


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
