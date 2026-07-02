import asyncio
from typing import Any

import httpx

from app.core.config import get_settings


async def send_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, dict[str, Any] | None, str | None]:
    settings = get_settings()
    attempts = max(1, settings.notification_webhook_retries + 1)
    last_error: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.notification_webhook_timeout_seconds) as client:
                response = await client.post(url, json=payload)
            if response.status_code < 400:
                return True, {"status_code": response.status_code, "attempts": attempt}, None
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
        if attempt < attempts:
            await asyncio.sleep(0.1 * attempt)
    return False, {"attempts": attempts}, last_error


async def send_email_stub(to: str, payload: dict[str, Any]) -> tuple[bool, dict[str, Any], None]:
    return True, {"stub": True, "to": to, "payload_keys": sorted(payload.keys())}, None
