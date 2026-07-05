from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.change_sets.models import ChangeSet, ChangeSetStatus
from app.core.config import get_settings
from app.core.enums import EnterpriseQueueStatus, IntegrationPackageStatus
from app.enterprise_runtime.models import DeadLetterQueueItem, IntegrationQueueMessage
from app.environments.models import EnvironmentProfile
from app.integration_bus.models import IntegrationEndpoint
from app.integration_flows.models import IntegrationFlow
from app.packages.models import InstalledPackage
from app.packages import service as package_service
from app.packages_auth.models import AuthUser
from app.production import backups, checks, service as production_service
from app.production.schemas import ProductionCheck
from app.secrets.models import Secret
from app.test_console.models import SavedTestCase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def doctor(session: AsyncSession) -> dict[str, Any]:
    items: list[ProductionCheck] = []
    settings = get_settings()

    try:
        await session.execute(text("SELECT 1"))
        database_status = "ok"
        database_message = "connection ok"
    except Exception as exc:
        database_status = "error"
        database_message = str(exc)
    revision = await checks.database_revision(session) if database_status == "ok" else None
    items.append(ProductionCheck(name="Database reachable", status=database_status, message=database_message))
    if database_status != "ok":
        return {
            "generated_at": utcnow().isoformat(),
            "app_env": settings.app_env,
            "status": "error",
            "summary": {"ok": 0, "warning": 0, "error": 1},
            "checks": items,
            "counts": {},
        }
    items.append(ProductionCheck(name="Migration head", status="ok" if revision == checks.MIGRATION_HEAD else "warning", message=f"current={revision or 'unknown'} head={checks.MIGRATION_HEAD}"))

    frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "index.html"
    items.append(ProductionCheck(name="Frontend build", status="ok" if frontend_dist.exists() else "warning", message=str(frontend_dist) if frontend_dist.exists() else "frontend/dist/index.html not found; run npm build or use dev server"))

    installed = {item.package_id: item for item in (await session.execute(select(InstalledPackage))).scalars().all()}
    for package_id, label in (("omh-package-onec", "1C Package"), ("omh-package-printer", "Printer Package")):
        package = installed.get(package_id)
        items.append(ProductionCheck(name=label, status="ok" if package and package.enabled and package.status == IntegrationPackageStatus.ENABLED else "warning", message="enabled" if package and package.enabled else "not enabled"))
    auth_package = installed.get("omh-package-auth")
    users_count = int(await session.scalar(select(func.count()).select_from(AuthUser)) or 0)
    items.append(ProductionCheck(name="Auth state", status="ok" if auth_package and auth_package.enabled and users_count else "warning", message=f"auth_package_enabled={bool(auth_package and auth_package.enabled)} users={users_count}"))

    current_environment = (await session.execute(select(EnvironmentProfile).where(EnvironmentProfile.is_current.is_(True)).limit(1))).scalar_one_or_none()
    pending_change_sets = int(await session.scalar(select(func.count()).select_from(ChangeSet).where(ChangeSet.status.in_([ChangeSetStatus.DRAFT, ChangeSetStatus.EXPORTED, ChangeSetStatus.IMPORT_PREVIEWED, ChangeSetStatus.FAILED]))) or 0)
    items.append(ProductionCheck(name="Current environment", status="ok" if current_environment else "warning", message=f"{current_environment.name} ({current_environment.code})" if current_environment else "No current environment selected"))
    items.append(ProductionCheck(name="Pending change sets", status="warning" if pending_change_sets else "ok", message=f"{pending_change_sets} pending/failed" if pending_change_sets else "No pending change sets"))

    package_report = await package_service.compatibility_report(session)
    package_errors = [f"{item['package_id']}: {', '.join(item['errors'])}" for item in package_report["packages"] if item.get("errors")]
    items.append(ProductionCheck(name="Package compatibility", status="error" if package_errors else "ok", message="; ".join(package_errors) if package_errors else "registered packages compatible"))

    items.extend(await checks._secret_checks(session))

    queue = await production_service.queue_counts(session)
    backlog = int(queue.get(EnterpriseQueueStatus.WAITING.value, 0) + queue.get(EnterpriseQueueStatus.RETRY_WAITING.value, 0))
    dlq_count = int(queue.get("dlq", 0))
    items.append(ProductionCheck(name="Queue backlog", status="warning" if backlog else "ok", message=f"waiting_or_retry={backlog}", details=queue))
    items.append(ProductionCheck(name="DLQ count", status="warning" if dlq_count else "ok", message=f"dlq={dlq_count}"))

    last_backup = await backups.last_success(session)
    items.append(ProductionCheck(name="Last backup", status="ok" if last_backup else "warning", message=last_backup.created_at.isoformat() if last_backup else "No successful backup/export recorded"))

    production_checks = await checks.update_checks(session, post_update=True)
    disk = next((item for item in production_checks if item.name == "Disk space"), None)
    if disk:
        items.append(disk)

    counts = {
        "connectors": await _count(session, ConnectorInstance),
        "endpoints": await _count(session, IntegrationEndpoint),
        "flows": await _count(session, IntegrationFlow),
        "saved_test_cases": await _count(session, SavedTestCase),
        "environments": await _count(session, EnvironmentProfile),
        "change_sets": await _count(session, ChangeSet),
        "secrets": await _count(session, Secret),
        "queue_messages": await _count(session, IntegrationQueueMessage),
        "dlq_items": await _count(session, DeadLetterQueueItem),
    }
    errors = sum(1 for item in items if item.status == "error")
    warnings = sum(1 for item in items if item.status == "warning")
    return {"generated_at": utcnow().isoformat(), "app_env": settings.app_env, "status": "error" if errors else "warning" if warnings else "ok", "summary": {"ok": sum(1 for item in items if item.status == "ok"), "warning": warnings, "error": errors}, "checks": items, "counts": counts}


async def first_run_checklist(session: AsyncSession) -> dict[str, Any]:
    installed = {item.package_id: item for item in (await session.execute(select(InstalledPackage))).scalars().all()}
    onec = installed.get("omh-package-onec")
    printer = installed.get("omh-package-printer")
    auth = installed.get("omh-package-auth")
    secret_key_configured = bool(get_settings().secret_key)
    items = [
        _item("auth", "Create first user or intentionally leave Auth Package disabled", "ok" if (auth and auth.enabled and await _count(session, AuthUser)) or not (auth and auth.enabled) else "action_required", {"auth_package_enabled": bool(auth and auth.enabled), "users": await _count(session, AuthUser)}),
        _item("secret_key", "Configure OMH_SECRET_KEY", "ok" if secret_key_configured else "warning", {"configured": secret_key_configured}),
        _item("onec_package", "Install and enable 1C Package", "ok" if onec and onec.enabled else "action_required"),
        _item("onec_connector", "Configure 1C connector", "ok" if await _connector_count(session, "onec") else "action_required"),
        _item("odata", "Test OData lookup", "ok" if await _endpoint_slug_exists(session, "site-contractor-lookup") else "warning"),
        _item("flows", "Configure at least one integration flow", "ok" if await _count(session, IntegrationFlow) else "action_required"),
        _item("test_case", "Run or create a saved test case", "ok" if await _count(session, SavedTestCase) else "action_required"),
        _item("backup", "Configure backup / create config export", "ok" if await backups.last_success(session) else "action_required"),
        _item("release_check", "Run make release-check", "manual", {"command": "make release-check"}),
        _item("production_mode", "Enable production mode only after checklist is complete", "manual", {"app_env": get_settings().app_env}),
        _item("printer_package", "Install and enable Printer Package if printing is used", "ok" if printer and printer.enabled else "warning"),
    ]
    return {"generated_at": utcnow().isoformat(), "items": items, "complete": not any(item["status"] == "action_required" for item in items)}


async def route_inventory_gate(routes: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_core = {"/api/bus/in/{slug}", "/api/events/*", "/api/queue/*", "/api/packages/*"}
    paths = {item["path"] for item in routes}
    missing_core = sorted(required_core - paths)
    if missing_core:
        errors.append(f"Missing core route inventory entries: {missing_core}")
    for item in routes:
        path = str(item.get("path") or "")
        if any(marker in path for marker in ("/api/onec", "/api/odata-explorer", "/api/printing")) and not item.get("guarded"):
            warnings.append(f"Package-looking route is not marked guarded: {path}")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "checked": len(routes)}


async def _count(session: AsyncSession, model: type) -> int:
    try:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)
    except Exception:
        return 0


async def _connector_count(session: AsyncSession, connector_type: str) -> int:
    return int(await session.scalar(select(func.count()).select_from(ConnectorInstance).where(ConnectorInstance.connector_type == connector_type)) or 0)


async def _endpoint_slug_exists(session: AsyncSession, slug: str) -> bool:
    return bool(await session.scalar(select(IntegrationEndpoint.id).where(IntegrationEndpoint.slug == slug).limit(1)))


def _item(code: str, title: str, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "title": title, "status": status, "details": details or {}}
