from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.connectors.builtin.onec import errors
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url, response_json
from app.sdk.types import ConnectorContext

OPERATION_PRESETS: dict[str, dict[str, str]] = {
    "update_shipment_status": {"method": "POST", "path": "/shipment-facts", "body_mode": "json_envelope", "content_type": "application/json"},
    "update_stock_balance": {"method": "POST", "path": "/stock-balances", "body_mode": "json_envelope", "content_type": "application/json"},
    "send_inventory_result": {"method": "POST", "path": "/inventory-results", "body_mode": "json_envelope", "content_type": "application/json"},
}


def resolve_operation(config: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str, str, dict[str, Any], dict[str, Any] | None]:
    meta = payload.get("_omh") or {}
    operation = str(meta.get("operation") or "")
    configured = (config.get("operations") or {}).get(operation) if operation else None
    preset = OPERATION_PRESETS.get(operation) if operation else None
    fallback_path = (config.get("http_services") or {}).get("default_path") or config.get("default_http_service_path")
    method = str(meta.get("method") or (configured or {}).get("method") or (preset or {}).get("method") or "POST").upper()
    path = str(meta.get("path") or (configured or {}).get("path") or (preset or {}).get("path") or fallback_path or "")
    options = {
        "content_type": meta.get("content_type") or (configured or {}).get("content_type") or (preset or {}).get("content_type") or "application/json",
        "body_mode": meta.get("body_mode") or (configured or {}).get("body_mode") or (preset or {}).get("body_mode") or "json_envelope",
    }
    if operation and not path:
        return operation, method, path, options, {"error_code": errors.ONEC_OPERATION_NOT_CONFIGURED, "error_message": f"1C operation {operation} is not configured"}
    if not path:
        path = "/"
    return operation, method, path, options, None


async def call_http_service(config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext | None = None) -> tuple[bool, int | None, dict[str, Any], dict[str, Any] | None, str | None, str | None]:
    operation, method, path, options, error = resolve_operation(config, payload)
    body, raw_content = request_body(payload, context, options)
    base_url = str(config.get("http_service_base_url") or "")
    url = join_url(base_url, path)
    if error:
        return False, None, {"operation": operation, "method": method, "url": url, "body": body}, None, error["error_code"], error["error_message"]
    client = OneCHTTPClient(config)
    if raw_content is None:
        response, request_payload, error_code, error_message = await client.request(method, url, json_payload=body)
    else:
        headers = {"Content-Type": str(options["content_type"])}
        response, request_payload, error_code, error_message = await client.request(method, url, content=raw_content, headers=headers)
    request_payload["operation"] = operation
    request_payload["body_mode"] = options["body_mode"]
    if error_code:
        return False, None, request_payload, None, error_code, error_message
    assert response is not None
    data, text = response_json(response)
    content_type = response.headers.get("content-type")
    response_payload = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "content_type": content_type,
        "body": data if data is not None else {"text": text},
    }
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


def request_body(payload: dict[str, Any], context: ConnectorContext | None, options: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    mode = str(options.get("body_mode") or "json_envelope")
    if mode == "json_envelope":
        return standard_envelope(payload, context), None
    if mode == "raw_xml":
        nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        xml = payload.get("xml") or payload.get("xml_payload") or nested.get("xml")
        if not isinstance(xml, str) or not xml.strip():
            return {"error": "xml payload is required for raw_xml"}, ""
        return None, xml
    if mode == "plain_text":
        text = payload.get("text") or payload.get("body") or payload.get("payload")
        return None, text if isinstance(text, str) else str(text or "")
    return standard_envelope(payload, context), None


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
