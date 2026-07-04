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
        package = installed.get(str(item["package_id"]))
        status = package.status.value if package else str(item.get("status") or "available")
        result.append({**item, "status": status, "installable": bool(item.get("installable", True)), "installed": package is not None, "enabled": bool(package and package.enabled)})
    return result


async def categories(session: AsyncSession) -> list[dict[str, Any]]:
    counts = Counter(str(item["category"]) for item in await catalog(session))
    return [{"category": category, "count": count} for category, count in sorted(counts.items())]
