from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.connectors.builtin.onec import errors
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url, response_json
from app.sdk.types import ConnectorContext

OPERATION_PRESETS: dict[str, dict[str, str]] = {
    "update_shipment_status": {"method": "POST", "path": "/shipment-facts"},
    "update_stock_balance": {"method": "POST", "path": "/stock-balances"},
    "send_inventory_result": {"method": "POST", "path": "/inventory-results"},
}


def resolve_operation(config: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str, str, dict[str, Any] | None]:
    meta = payload.get("_omh") or {}
    operation = str(meta.get("operation") or "")
    configured = (config.get("operations") or {}).get(operation) if operation else None
    preset = OPERATION_PRESETS.get(operation) if operation else None
    fallback_path = (config.get("http_services") or {}).get("default_path") or config.get("default_http_service_path")
    method = str(meta.get("method") or (configured or {}).get("method") or (preset or {}).get("method") or "POST").upper()
    path = str(meta.get("path") or (configured or {}).get("path") or (preset or {}).get("path") or fallback_path or "")
    if operation and not path:
        return operation, method, path, {"error_code": errors.ONEC_OPERATION_NOT_CONFIGURED, "error_message": f"1C operation {operation} is not configured"}
    if not path:
        path = "/"
    return operation, method, path, None


async def call_http_service(config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext | None = None) -> tuple[bool, int | None, dict[str, Any], dict[str, Any] | None, str | None, str | None]:
    operation, method, path, error = resolve_operation(config, payload)
    body = standard_envelope(payload, context)
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
    if isinstance(data, dict) and data.get("success") is False:
        return (
            False,
            response.status_code,
            request_payload,
            response_payload,
            str(data.get("error_code") or errors.ONEC_BUSINESS_ERROR),
            str(data.get("error_message") or "1C business operation failed"),
        )
    return True, response.status_code, request_payload, response_payload, None, None


def standard_envelope(payload: dict[str, Any], context: ConnectorContext | None) -> dict[str, Any]:
    body = {key: value for key, value in payload.items() if key != "_omh"}
    envelope = body if isinstance(body.get("payload"), dict) else {"payload": body}
    omh = dict(envelope.get("omh") or {})
    if context is not None:
        if context.event_id is not None:
            omh.setdefault("event_id", str(context.event_id))
        if context.run_id is not None:
            omh.setdefault("run_id", str(context.run_id))
        if context.step_id is not None:
            omh.setdefault("step_id", str(context.step_id))
        if context.correlation_id is not None:
            omh.setdefault("correlation_id", context.correlation_id)
        if context.source_system is not None:
            omh.setdefault("source_system", context.source_system)
        if context.target_system is not None:
            omh.setdefault("target_system", context.target_system)
        for key in ("event_type", "entity_type", "entity_id"):
            if context.metadata.get(key) is not None:
                omh.setdefault(key, context.metadata[key])
    omh.setdefault("sent_at", datetime.now(timezone.utc).isoformat())
    envelope["omh"] = omh
    return envelope
