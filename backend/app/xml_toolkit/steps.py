from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.connectors import repository as connector_repository
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.external_errors.normalizers import external_error_artifact, external_error_payload_from_result
from app.packages_training.mock_onec_http import accept_raw_xml
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope
from app.xml_toolkit import service


class XmlExtractStep:
    name = "xml_extract"
    display_name = "Extract XML fields"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            raw_xml = _source_xml(context, str(config.get("source") or "request.body_raw"))
        except ValueError as exc:
            return StepResult.failed("XML_SOURCE_EMPTY", str(exc), hint="Use an XML endpoint or select the correct source field.")
        fields = [field for field in config.get("fields") or [] if isinstance(field, dict)]
        parsed = service.parse(raw_xml)
        artifacts = [
            ArtifactCreate(ArtifactType.RAW_PAYLOAD.value, str(config.get("raw_artifact_name") or "xml_parse_input.xml"), {"xml": raw_xml, "size_bytes": len(raw_xml.encode("utf-8")), "sha256": parsed.sha256}),
            ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, str(config.get("parse_tree_artifact_name") or "xml_parse_tree.json"), parsed.model_dump(mode="json")),
        ]
        if not parsed.success:
            return StepResult.failed("XML_PARSE_FAILED", "; ".join(parsed.errors), artifacts=artifacts, hint="Check incoming XML, Content-Type, encoding and namespaces.")
        extraction = service.extract(raw_xml, fields=[_field_model(field) for field in fields])
        values, errors = extraction.values, extraction.errors
        artifacts.append(ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, str(config.get("extracted_fields_artifact_name") or "xml_extracted_fields.json"), {"fields": fields, "values": values, "errors": errors}))
        if errors:
            return StepResult.failed("XML_REQUIRED_FIELD_MISSING", "; ".join(str(item.get("message")) for item in errors), artifacts=artifacts, variables_update={"xml_fields": values}, hint="Open XML path picker and check required field paths.")
        step_id = str(config.get("step_id") or "xml_extract")
        steps = dict(context.variables.get("steps") or {})
        steps[step_id] = values
        return StepResult.success("XML fields extracted", artifacts=artifacts, variables_update={**values, "xml_fields": values, "steps": steps})


class RawXmlForwardStep:
    name = "raw_xml_forward"
    display_name = "Raw XML forward"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            raw_xml = _source_xml(context, str(config.get("source") or "request.body_raw"))
        except ValueError as exc:
            return StepResult.failed("XML_SOURCE_EMPTY", str(exc), hint="Use an XML endpoint or select the correct source field.")

        forwarded_xml = str(config.get("forwarded_xml")) if config.get("forwarded_xml") is not None else raw_xml
        preview = service.raw_forward_preview(raw_xml, forwarded_xml)
        parsed = service.parse(raw_xml)
        step_id = str(config.get("step_id") or "raw_xml_forward")
        method = str(config.get("method") or "POST").upper()
        headers = _headers(config)
        target, target_errors = await _target(config, context)
        hashes = {
            "original_sha256": preview.input_sha256,
            "forwarded_sha256": preview.forwarded_sha256,
            "unchanged": preview.forwarded_unchanged,
            "size_bytes": preview.size_bytes,
            "comparison_scope": "OMH compares the XML text body after reception.",
        }
        target_request = {
            "connector": target.get("connector"),
            "method": method,
            "url": target.get("url"),
            "path": config.get("path"),
            "headers": headers,
            "body_type": "xml",
            "body": forwarded_xml,
            **hashes,
        }
        artifacts = [
            ArtifactCreate(ArtifactType.RAW_PAYLOAD.value, "raw_xml_original.xml", {"xml": raw_xml, "sha256": preview.input_sha256, "size_bytes": preview.size_bytes}),
            ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "raw_xml_forwarded.xml", {"xml": forwarded_xml, "sha256": preview.forwarded_sha256, "size_bytes": len(forwarded_xml.encode("utf-8"))}),
            ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "xml_hashes.json", hashes),
            ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "target_request.json", target_request),
        ]

        if _bool_config(config, "require_valid_xml", _bool_config(config, "validate_xml", True)) and not parsed.success:
            return StepResult.failed(
                "XML_PARSE_FAILED",
                "XML не удалось разобрать. Проверьте структуру документа.",
                artifacts=[*artifacts, ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "xml_parse_errors.json", parsed.model_dump(mode="json"))],
                hint="Disable `require_valid_xml` only when the target must receive non-well-formed XML unchanged.",
            )

        if _bool_config(config, "verify_hash", _bool_config(config, "verify_unchanged_hash", True)) and not preview.forwarded_unchanged:
            return StepResult.failed(
                "XML_HASH_MISMATCH",
                "XML был изменён перед отправкой. Проверьте настройки raw forward.",
                artifacts=artifacts,
                hint="Raw XML bridge must forward the same text body. Remove forwarded_xml overrides and transforms.",
            )

        if target_errors:
            return StepResult.failed("TARGET_ENDPOINT_REQUIRED", "; ".join(target_errors), artifacts=artifacts, hint="Select a 1C HTTP Service connector or enter a full http(s) URL.")

        response = await _send_raw_xml(context, config, target, method, headers, forwarded_xml)
        response_artifact = ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "target_response.json", response)
        artifacts.append(response_artifact)

        response_body = _response_body(response)
        result = {"forwarded": True, "method": method, "path": config.get("path"), "target": target, "hashes": hashes, "target_response": response}
        steps = dict(context.variables.get("steps") or {})
        steps[step_id] = result
        variables = {
            "raw_xml_forward": result,
            "xml_hashes": hashes,
            "target_response": response,
            str(config.get("save_response_as") or "target_response"): response_body,
            "response": response,
            "steps": steps,
        }
        status_code = int(response.get("status_code") or 0)
        if status_code >= 400:
            external_error = _external_error_payload(context, target_request, response, target)
            artifacts.append(ArtifactCreate(ArtifactType.EXTERNAL_ERROR.value, "external_error.json", external_error_artifact(external_error)))
            return StepResult.failed(
                "TARGET_ENDPOINT_ERROR",
                "Принимающая 1С вернула ошибку. Оригинальный ответ показан ниже.",
                artifacts=artifacts,
                variables_update=variables,
                metadata={"external_error": external_error},
                human_title=external_error.get("human_title"),
                human_summary=external_error.get("human_summary"),
                developer_message=external_error.get("developer_message"),
                hint=external_error.get("hint") or "Open target_response.json before changing the XML payload.",
            )
        return StepResult.success("Raw XML forwarded unchanged", artifacts=artifacts, variables_update=variables)


def _field_model(field: dict[str, Any]):
    from app.xml_toolkit.schemas import XmlExtractField

    return XmlExtractField(**field)


def _config(context: PipelineContext) -> dict[str, Any]:
    return dict((context.current_step.step_config_json or {}).get("config") or {})


def _source_xml(context: PipelineContext, source: str) -> str:
    scope = build_runtime_scope(
        request_body=context.variables.get("payload") or {},
        variables=context.variables,
        headers=(context.variables.get("payload") or {}).get("_headers") if isinstance(context.variables.get("payload"), dict) else {},
        query=(context.variables.get("payload") or {}).get("_query") if isinstance(context.variables.get("payload"), dict) else {},
        raw_text=(context.variables.get("payload") or {}).get("text") if isinstance(context.variables.get("payload"), dict) else None,
        xml=(context.variables.get("payload") or {}).get("xml") if isinstance(context.variables.get("payload"), dict) else None,
        context={"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id},
    )
    aliases = {
        "request.body_raw": "request.raw_text",
        "request.xml": "request.xml",
        "payload.xml": "variables.payload.xml",
        "payload.text": "variables.payload.text",
    }
    candidate = aliases.get(source, source)
    try:
        value = resolve_path(scope, candidate)
    except PathResolutionError:
        payload = context.variables.get("payload") or {}
        value = payload.get("xml") or payload.get("text") if isinstance(payload, dict) else None
    if value in (None, ""):
        raise ValueError(f"XML source is empty: {source}")
    return str(value)


def _headers(config: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/xml; charset=utf-8"}
    configured = config.get("headers")
    if isinstance(configured, dict):
        headers.update({str(key): value for key, value in configured.items()})
    return headers


async def _target(config: dict[str, Any], context: PipelineContext) -> tuple[dict[str, Any], list[str]]:
    connector_name = str(config.get("connector") or config.get("connector_name") or "").strip()
    url = _configured_url(config)
    connector_config: dict[str, Any] = {}
    if connector_name:
        connector = await connector_repository.get_by_name(context.session, connector_name)
        if connector is None:
            return {"connector": connector_name, "url": url or None}, [f"Target connector {connector_name} not found"]
        connector_config = connector.config_json or {}
        url = url or _connector_url(connector_config, str(config.get("path") or ""))
    errors: list[str] = []
    if not url and not _has_mock_response(config):
        errors.append("Target URL is required for raw XML forwarding.")
    if url and not _valid_http_url(url):
        errors.append("Target URL must start with http:// or https://.")
    return {"connector": connector_name or None, "url": url or None, "connector_config": connector_config}, errors


def _configured_url(config: dict[str, Any]) -> str:
    direct = str(config.get("url") or "").strip()
    if direct:
        return direct
    base = str(config.get("base_url") or "").strip()
    path = str(config.get("path") or "").strip()
    if base and path:
        return urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    return ""


def _connector_url(connector_config: dict[str, Any], path: str) -> str:
    direct = str(connector_config.get("url") or "").strip()
    if direct:
        return direct
    base = str(connector_config.get("http_service_base_url") or connector_config.get("base_url") or "").strip()
    if not base:
        return ""
    return urljoin(base.rstrip("/") + "/", path.lstrip("/")) if path else base


def _valid_http_url(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _has_mock_response(config: dict[str, Any]) -> bool:
    return any(config.get(key) is not None for key in ("mock_response_json", "mock_response_text", "mock_response_xml")) or bool(config.get("training_mock_onec_xml_receiver"))


async def _send_raw_xml(context: PipelineContext, config: dict[str, Any], target: dict[str, Any], method: str, headers: dict[str, Any], xml: str) -> dict[str, Any]:
    if config.get("training_mock_onec_xml_receiver"):
        status_code, body = accept_raw_xml(xml)
        return {"status_code": status_code, "headers": {"Content-Type": "application/json"}, "content_type": "application/json", "body": body, "mock": True}
    mock_response = _mock_response(config)
    if mock_response is not None:
        status_code = int(config.get("mock_status_code") or 200)
        return {"status_code": status_code, "headers": {"Content-Type": _mock_content_type(mock_response)}, "content_type": _mock_content_type(mock_response), "body": mock_response, "mock": True}
    url = str(target.get("url") or "")
    if context.dry_run:
        return {"status_code": 200, "headers": {}, "content_type": "application/json", "body": {"dry_run": True, "xml_forwarded": True, "target_url": url}, "dry_run": True}
    timeout = float(config.get("timeout_seconds") or 30)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, content=xml.encode("utf-8"), headers=headers)
    except httpx.TimeoutException as exc:
        return {"status_code": 504, "headers": {}, "content_type": "text/plain", "body": str(exc) or "Принимающая система не ответила за заданное время.", "error": "timeout"}
    except Exception as exc:
        return {"status_code": 502, "headers": {}, "content_type": "text/plain", "body": str(exc), "error": "connection_error"}
    content_type = response.headers.get("content-type")
    body: Any
    if content_type and "json" in content_type.lower():
        try:
            body = response.json()
        except Exception:
            body = response.text
    else:
        body = response.text
    return {"status_code": response.status_code, "headers": dict(response.headers), "content_type": content_type, "body": body}


def _mock_response(config: dict[str, Any]) -> Any | None:
    if config.get("mock_response_json") is not None:
        return config.get("mock_response_json")
    if config.get("mock_response_xml") is not None:
        return str(config.get("mock_response_xml"))
    if config.get("mock_response_text") is not None:
        return str(config.get("mock_response_text"))
    return None


def _mock_content_type(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return "application/json"
    text = str(value).lstrip()
    return "application/xml" if text.startswith("<") else "text/plain"


def _response_body(response: dict[str, Any]) -> Any:
    return response.get("body")


def _bool_config(config: dict[str, Any], key: str, default: bool) -> bool:
    value = config.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def _external_error_payload(context: PipelineContext, request_payload: dict[str, Any], response: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body")
    content_type = str(response.get("content_type") or _header_lookup(response.get("headers"), "content-type") or "")
    raw_json = body if isinstance(body, (dict, list)) else None
    raw_text = body if isinstance(body, str) else None
    raw_xml = raw_text if raw_text and _looks_like_xml(content_type, raw_text) else None
    result = SimpleNamespace(
        success=False,
        status_code=response.get("status_code"),
        request_payload=request_payload,
        response_payload=response,
        raw_response_json=raw_json,
        raw_response_text=None if raw_xml else raw_text,
        raw_response_xml=raw_xml,
        response_headers=response.get("headers") or {},
        response_content_type=response.get("content_type") or content_type or None,
        endpoint_url=target.get("url"),
        operation=request_payload.get("method"),
        error_code="TARGET_ENDPOINT_ERROR",
        error_message="Принимающая 1С вернула ошибку.",
        external_error_type="http_error",
        human_title="Принимающая 1С вернула ошибку.",
        human_summary=f"Target HTTP {response.get('status_code')}: {_error_message_from_body(body)}",
        developer_message="Original target response is preserved in target_response.json and external_error.json artifacts.",
        hint="Check the receiving 1C HTTP service, Content-Type and XML contract.",
    )
    return external_error_payload_from_result(result, source_system=context.source_system, target_system=context.target_system, connector_type="raw_xml", connector_name=str(target.get("connector") or target.get("url") or "raw_xml_target"))


def _header_lookup(headers: Any, name: str) -> str | None:
    if not isinstance(headers, dict):
        return None
    lowered = name.lower()
    for key, value in headers.items():
        if str(key).lower() == lowered:
            return str(value)
    return None


def _looks_like_xml(content_type: str, text: str) -> bool:
    return "xml" in content_type.lower() or text.lstrip().startswith("<")


def _error_message_from_body(body: Any) -> str:
    if isinstance(body, dict):
        for key in ("error_message", "message", "detail", "error"):
            value = body.get(key)
            if value:
                return str(value)
    if isinstance(body, str) and body.strip():
        return body.strip()[:240]
    return "request failed"
