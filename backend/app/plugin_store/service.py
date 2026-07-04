from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.packages import repository
from app.plugin_store.catalog import load_catalog


async def catalog(session: AsyncSession) -> list[dict[str, Any]]:
    installed = {item.package_id: item for item in await repository.list_installed(session)}
    result: list[dict[str, Any]] = []
    for item in load_catalog():
        package_id = str(item["package_id"])
        package = installed.get(package_id)
        manifest_status = str(item.get("status") or "available")
        installable = bool(item.get("installable", True))
        status = "installed" if package and package.enabled else "disabled" if package else manifest_status
        result.append({**item, "registered": True, "available": installable and manifest_status == "available", "status": status, "installable": installable, "installed": package is not None, "enabled": bool(package and package.enabled)})
    return result


async def categories(session: AsyncSession) -> list[dict[str, Any]]:
    counts = Counter(str(item["category"]) for item in await catalog(session))
    return [{"category": category, "count": count} for category, count in sorted(counts.items())]
