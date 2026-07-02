from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from app.connectors.builtin.onec.auth import auth_for, mask_secrets
from app.connectors.builtin.onec import errors


def join_url(base: str, path: str = "") -> str:
    if not path:
        return base.rstrip("/")
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


class OneCHTTPClient:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.timeout = float(config.get("timeout_seconds", 20))
        self.verify = bool(config.get("verify_ssl", True))
        self.auth = auth_for(config)

    async def request(self, method: str, url: str, *, params: dict | None = None, json_payload: dict | None = None) -> tuple[httpx.Response | None, dict[str, Any], str | None, str | None]:
        request_payload = {"method": method.upper(), "url": url, "params": params or {}, "body": json_payload, "auth": mask_secrets(self.config.get("auth") or {"type": "none"})}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify, auth=self.auth) as client:
                response = await client.request(method.upper(), url, params=params, json=json_payload)
            return response, request_payload, None, None
        except httpx.TimeoutException:
            return None, request_payload, errors.ONEC_TIMEOUT, f"1C request timed out after {self.timeout:g} seconds"
        except httpx.ConnectError as exc:
            return None, request_payload, errors.ONEC_CONNECTION_ERROR, str(exc) or "1C connection error"
        except httpx.HTTPError as exc:
            return None, request_payload, errors.ONEC_CONNECTION_ERROR, str(exc) or "1C connection error"


def response_json(response: httpx.Response) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    try:
        data = response.json()
    except Exception:
        return None, response.text
    return data, None
