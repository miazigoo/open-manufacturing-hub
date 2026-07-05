from __future__ import annotations

import logging
import os

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import EnterpriseQueueStatus
from app.enterprise_runtime.models import IntegrationQueueMessage
from app.packages.models import InstalledPackage
from app.production import backups
from app.packages_auth.models import AuthUser
from app.production.checks import database_revision

logger = logging.getLogger("omh.production.startup")


async def log_startup_banner(session: AsyncSession) -> None:
    settings = get_settings()
    production_mode = settings.app_env.lower() in {"production", "prod"}
    if production_mode and not settings.secret_key:
        raise RuntimeError("OMH_SECRET_KEY is required when APP_ENV=production")

    postgres_password = os.getenv("POSTGRES_PASSWORD", "")
    if production_mode and postgres_password in {"change-me", "change-me-long-random-db-password"}:
        logger.warning("POSTGRES_PASSWORD still uses a placeholder value. Change it before processing factory traffic.")
    if production_mode and settings.allow_demo_seed_in_production:
        logger.warning("Demo seed is explicitly allowed in production. Disable OMH_ALLOW_DEMO_SEED_IN_PRODUCTION before go-live.")

    packages = list((await session.execute(select(InstalledPackage).order_by(InstalledPackage.package_id))).scalars().all())
    auth_package = next((item for item in packages if item.package_id == "omh-package-auth" and item.enabled), None)
    auth_users = int(await session.scalar(select(func.count()).select_from(AuthUser)) or 0)
    processing = int(await session.scalar(select(func.count()).select_from(IntegrationQueueMessage).where(IntegrationQueueMessage.status == EnterpriseQueueStatus.PROCESSING)) or 0)
    if production_mode and not auth_package:
        logger.warning("Auth package is not enabled. UI remains open until the optional auth package is installed and configured.")
    if production_mode and not await backups.recent_success_exists(session, 24):
        logger.warning("No successful backup/export in the last 24 hours. Run make prod-backup before factory traffic or updates.")

    logger.warning(
        "\n".join(
            [
                "OMH Production Startup" if production_mode else "OMH Development Startup",
                f"App version: {settings.app_version}",
                f"DB revision: {await database_revision(session) or 'unknown'}",
                f"Installed packages: {', '.join(item.package_id for item in packages) or 'none'}",
                f"Production mode: {'yes' if production_mode else 'no'}",
                f"Auth enabled: {'yes' if auth_package and auth_users else 'no'}",
                f"Queue worker: {'active items processing' if processing else 'enabled'}",
            ]
        )
    )
