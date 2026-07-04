from __future__ import annotations

from importlib.metadata import version
from typing import Any


def app_version() -> str:
    try:
        return version("open-manufacturing-hub-backend")
    except Exception:
        return "0.1.0"


def frontend_version() -> str:
    return "0.1.0"


def package_row(item: Any) -> dict[str, Any]:
    return {
        "package_id": item.package_id,
        "name": item.name,
        "version": item.version,
        "status": item.status.value if hasattr(item.status, "value") else str(item.status),
        "enabled": item.enabled,
        "official": item.official,
    }
