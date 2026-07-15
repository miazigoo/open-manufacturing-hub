from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, is_dataclass
from typing import Any

from app.xml_bridge.parser import reject_unsafe_xml

JSON_MESSAGE_KEYS = ("error_message", "message", "detail", "details", "description", "error", "fault", "faultstring", "ExceptionMessage")
JSON_CODE_KEYS = ("error_code", "code", "errorCode", "faultcode", "type")
XML_MESSAGE_TAGS = {"error", "message", "faultstring", "ОписаниеОшибки", "Сообщение", "ТекстОшибки"}
_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def external_error_payload_from_result(result: Any, *, source_system: str | None = None, target_system: str | None = None, connector_type: str | None = None, connector_name: str | None = None) -> dict[str, Any]:
    response_payload = _to_plain(getattr(result, "response_payload", None))
    request_payload = _to_plain(getattr(result, "request_payload", None))
    raw_json = _to_plain(getattr(result, "raw_response_json", None))
    raw_xml = getattr(result, "raw_response_xml", None)
    raw_text = getattr(result, "raw_response_text", None)
    content_type = getattr(result, "response_content_type", None) or _header_lookup(getattr(result, "response_headers", None), "content-type") or _detect_content_type(raw_json, raw_xml, raw_text, response_payload)

    body_json, body_text, body_xml = _body_parts(raw_json, raw_xml, raw_text, response_payload, content_type)
    preview_source = body_text if body_text is not None else body_xml if body_xml is not None else _json_dumps(body_json) if body_json is not None else None
    preview = _preview(_strip_html(preview_source) if _is_html(content_type) and preview_source else preview_source)
    sha_source = body_text if body_text is not None else body_xml if body_xml is not None else _json_dumps(body_json) if body_json is not None else ""

    extracted_code = getattr(result, "external_error_code", None) or _extract_code(body_json) or _extract_code(response_payload)
    extracted_message = getattr(result, "external_error_message", None) or _extract_message(body_json) or _extract_xml_message(body_xml) or _extract_message(response_payload) or preview
    normalized_code = getattr(result, "error_code", None) or extracted_code or "EXTERNAL_ERROR"
    normalized_message = getattr(result, "error_message", None) or extracted_message or "External system returned an error"
    status_code = getattr(result, "status_code", None) or _int_or_none((response_payload or {}).get("status_code") if isinstance(response_payload, dict) else None)

    operation = getattr(result, "operation", None) or ((request_payload or {}).get("operation") if isinstance(request_payload, dict) else None)
    endpoint_url = getattr(result, "endpoint_url", None) or ((request_payload or {}).get("url") if isinstance(request_payload, dict) else None)
    http_method = (request_payload or {}).get("method") if isinstance(request_payload, dict) else None

    title = getattr(result, "human_title", None) or _human_title(connector_type, connector_name, status_code)
    summary = getattr(result, "human_summary", None) or _human_summary(connector_name or target_system, status_code, extracted_message or normalized_message)
    developer_message = getattr(result, "developer_message", None) or _developer_message(status_code, content_type, preview)
    hint = getattr(result, "hint", None) or _hint(normalized_code, connector_type, connector_name)

    return {
        "normalized_code": str(normalized_code),
        "normalized_message": str(normalized_message),
        "human_title": title,
        "human_summary": summary,
        "developer_message": developer_message,
        "hint": hint,
        "external_error_code": str(extracted_code) if extracted_code is not None else None,
        "external_error_message": str(extracted_message) if extracted_message is not None else None,
        "external_error_type": getattr(result, "external_error_type", None) or _external_type(content_type, status_code, body_json, body_xml, body_text),
        "source_system": source_system,
        "target_system": target_system,
        "connector_type": connector_type,
        "connector_name": connector_name,
        "operation": operation,
        "endpoint_url": endpoint_url,
        "http_method": str(http_method).upper() if http_method else None,
        "http_status": status_code,
        "response_content_type": content_type,
        "response_body_text": body_text,
        "response_body_json": body_json,
        "response_body_xml": body_xml,
        "response_body_preview": preview,
        "response_body_sha256": hashlib.sha256(sha_source.encode("utf-8")).hexdigest() if sha_source else None,
        "response_size_bytes": len(sha_source.encode("utf-8")) if sha_source else None,
        "response_headers": _to_plain(getattr(result, "response_headers", None)) or {},
        "request": request_payload or {},
        "response": response_payload or {},
    }


def external_error_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "normalized_code": payload.get("normalized_code"),
        "normalized_message": payload.get("normalized_message"),
        "human_title": payload.get("human_title"),
        "human_summary": payload.get("human_summary"),
        "developer_message": payload.get("developer_message"),
        "hint": payload.get("hint"),
        "external": {
            "code": payload.get("external_error_code"),
            "message": payload.get("external_error_message"),
            "type": payload.get("external_error_type"),
            "status_code": payload.get("http_status"),
            "content_type": payload.get("response_content_type"),
            "headers": payload.get("response_headers") or {},
            "body": payload.get("response_body_json") if payload.get("response_body_json") is not None else payload.get("response_body_xml") or payload.get("response_body_text"),
            "body_preview": payload.get("response_body_preview"),
            "body_sha256": payload.get("response_body_sha256"),
            "size_bytes": payload.get("response_size_bytes"),
        },
        "request": payload.get("request") or {},
        "response": payload.get("response") or {},
    }


def _body_parts(raw_json: Any, raw_xml: str | None, raw_text: str | None, response_payload: Any, content_type: str | None) -> tuple[Any | None, str | None, str | None]:
    if raw_json is not None:
        return raw_json, None, None
    if raw_xml:
        return None, raw_xml, raw_xml
    if raw_text is not None:
        if _is_json(content_type):
            parsed = _json_loads(raw_text)
            if parsed is not None:
                return parsed, None, None
        if _is_xml(content_type):
            return None, raw_text, raw_text
        return None, raw_text, None
    if isinstance(response_payload, dict):
        body = response_payload.get("body")
        if isinstance(body, dict) and isinstance(body.get("text"), str) and set(body.keys()) <= {"text"}:
            return _body_parts(None, None, body["text"], None, content_type)
        if isinstance(body, (dict, list)):
            return body, None, None
        if isinstance(body, str):
            return _body_parts(None, None, body, None, content_type)
        if isinstance(response_payload.get("text"), str):
            return None, response_payload["text"], None
        if "body" not in response_payload:
            return response_payload, None, None
    return None, None, None


def _extract_message(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in JSON_MESSAGE_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = _extract_message(value)
                if nested:
                    return nested
        for value in data.values():
            nested = _extract_message(value)
            if nested:
                return nested
    if isinstance(data, list):
        for item in data:
            nested = _extract_message(item)
            if nested:
                return nested
    return None


def _extract_code(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in JSON_CODE_KEYS:
            value = data.get(key)
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value).strip()
        for value in data.values():
            nested = _extract_code(value)
            if nested:
                return nested
    if isinstance(data, list):
        for item in data:
            nested = _extract_code(item)
            if nested:
                return nested
    return None


def _extract_xml_message(xml_text: str | None) -> str | None:
    if not xml_text:
        return None
    try:
        reject_unsafe_xml(xml_text)
        root = ET.fromstring(xml_text.encode("utf-8"))
    except Exception:
        return None
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag in XML_MESSAGE_TAGS and elem.text and elem.text.strip():
            return elem.text.strip()
    text = " ".join(root.itertext())
    return _preview(_WS_RE.sub(" ", text).strip()) if text.strip() else None


def _strip_html(value: str) -> str:
    return html.unescape(_WS_RE.sub(" ", _HTML_RE.sub(" ", value)).strip())


def _preview(value: str | None, limit: int = 4000) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _json_loads(value: str) -> Any | None:
    try:
        return json.loads(value)
    except Exception:
        return None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _to_plain(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    return value


def _header_lookup(headers: Any, name: str) -> str | None:
    if not isinstance(headers, dict):
        return None
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None


def _detect_content_type(raw_json: Any, raw_xml: str | None, raw_text: str | None, response_payload: Any) -> str | None:
    if raw_json is not None:
        return "application/json"
    if raw_xml:
        return "application/xml"
    if isinstance(raw_text, str):
        stripped = raw_text.lstrip().lower()
        if stripped.startswith("<html") or "<body" in stripped[:500]:
            return "text/html"
        if stripped.startswith("<"):
            return "application/xml"
        return "text/plain"
    if isinstance(response_payload, dict):
        return str(response_payload.get("content_type") or response_payload.get("response_content_type") or "application/json")
    return None


def _is_json(content_type: str | None) -> bool:
    return bool(content_type and "json" in content_type.lower())


def _is_xml(content_type: str | None) -> bool:
    return bool(content_type and "xml" in content_type.lower())


def _is_html(content_type: str | None) -> bool:
    return bool(content_type and "html" in content_type.lower())


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _human_title(connector_type: str | None, connector_name: str | None, status_code: int | None) -> str:
    if connector_type == "onec" or (connector_name and "1C" in connector_name):
        return "1C rejected operation" if not status_code or status_code < 500 else "1C HTTP service error"
    if connector_type == "zpl_printer":
        return "Printer rejected job"
    return "External system returned an error"


def _human_summary(system: str | None, status_code: int | None, message: str) -> str:
    prefix = f"{system} says" if system else "External system says"
    if status_code:
        prefix = f"{prefix} HTTP {status_code}"
    return f"{prefix}: {message}"


def _developer_message(status_code: int | None, content_type: str | None, preview: str | None) -> str:
    parts = []
    if status_code:
        parts.append(f"HTTP {status_code}")
    if content_type:
        parts.append(f"Content-Type: {content_type}")
    if preview:
        parts.append(f"Body preview: {preview}")
    return "\n".join(parts) or "External error details are preserved in artifacts."


def _hint(code: str | None, connector_type: str | None, connector_name: str | None) -> str:
    upper = (code or "").upper()
    if "TIMEOUT" in upper or "CONNECTION" in upper:
        return "Check network connectivity, target service availability, DNS and firewall rules."
    if connector_type == "onec" or (connector_name and "1C" in connector_name):
        return "Check the source document, 1C HTTP service log, operation path and mapping before replay."
    if connector_type == "zpl_printer":
        return "Check printer power, TCP port, network route and ZPL payload before replay."
    return "Open request/response artifacts, fix external data or endpoint configuration, then replay from the failed step."


def _external_type(content_type: str | None, status_code: int | None, body_json: Any, body_xml: str | None, body_text: str | None) -> str | None:
    if status_code and status_code >= 500:
        return "http_server_error"
    if status_code and status_code >= 400:
        return "http_client_error"
    if isinstance(body_json, dict) and body_json.get("success") is False:
        return "business_error"
    if body_xml:
        return "xml_error"
    if body_text:
        return "text_error"
    return None
