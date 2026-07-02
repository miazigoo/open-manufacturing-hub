from __future__ import annotations

from typing import Any

import httpx


def auth_for(config: dict[str, Any]) -> httpx.BasicAuth | None:
    auth = config.get("auth") or {"type": "none"}
    if auth.get("type", "none") == "basic":
        return httpx.BasicAuth(str(auth.get("username", "")), str(auth.get("password", "")))
    return None


def mask_secrets(value):
    if isinstance(value, dict):
        return {key: ("***" if key.lower() in {"password", "secret", "token"} else mask_secrets(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_secrets(item) for item in value]
    return value
