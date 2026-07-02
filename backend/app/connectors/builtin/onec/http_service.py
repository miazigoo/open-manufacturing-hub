from __future__ import annotations

from typing import Any

from app.connectors.builtin.onec import errors
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url, response_json


def resolve_operation(config: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str, str, dict[str, Any] | None]:
    meta = payload.get("_omh") or {}
    operation = str(meta.get("operation") or "")
    configured = (config.get("operations") or {}).get(operation) if operation else None
    method = str(meta.get("method") or (configured or {}).get("method") or "POST").upper()
    path = str(meta.get("path") or (configured or {}).get("path") or "")
    if operation and not path:
        return operation, method, path, {"error_code": errors.ONEC_OPERATION_NOT_CONFIGURED, "error_message": f"1C operation {operation} is not configured"}
    if not path:
        path = "/"
    return operation, method, path, None


async def call_http_service(config: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, int | None, dict[str, Any], dict[str, Any] | None, str | None, str | None]:
    operation, method, path, error = resolve_operation(config, payload)
    body = {key: value for key, value in payload.items() if key != "_omh"}
    base_url = str(config.get("http_service_base_url") or "")
    url = join_url(base_url, path)
    if error:
        return False, None, {"operation": operation, "method": method, "url": url, "body": body}, None, error["error_code"], error["error_message"]
    client = OneCHTTPClient(config)
    response, request_payload, error_code, error_message = await client.request(method, url, json_payload=body)
    request_payload["operation"] = operation
    if error_code:
        return False, None, request_payload, None, error_code, error_message
    assert response is not None
    data, text = response_json(response)
    response_payload = {"status_code": response.status_code, "body": data if data is not None else {"text": text}}
    if response.status_code == 401:
        return False, response.status_code, request_payload, response_payload, errors.ONEC_AUTH_FAILED, "1C authentication failed"
    if response.status_code >= 400:
        return False, response.status_code, request_payload, response_payload, errors.ONEC_HTTP_SERVICE_ERROR, f"1C HTTP service returned {response.status_code}"
    if data is None and text:
        return False, response.status_code, request_payload, response_payload, errors.ONEC_RESPONSE_INVALID, "1C response is not valid JSON"
    return True, response.status_code, request_payload, response_payload, None, None
