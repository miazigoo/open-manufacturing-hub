from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.operation_catalog.models import OperationProfile
from app.operation_catalog.schemas import OperationSuccessConditionResult, OperationTestRequest, OperationTestResponse
from app.operation_catalog import service


async def test_operation(session: AsyncSession, operation: OperationProfile, request: OperationTestRequest) -> OperationTestResponse:
    connection = await service.connection_for_operation(session, operation)
    final_url = service.final_url(operation, connection)
    method = (operation.method or "POST").upper()
    headers = _headers(operation, connection)
    request_body = _request_body(operation, request)
    preview = {
        "connection": {
            "id": str(operation.connection_profile_id) if operation.connection_profile_id else None,
            "name": connection.name if connection else None,
            "kind": connection.kind if connection else None,
            "base_url": _connection_base_url(connection),
        },
        "method": method,
        "final_url": final_url,
        "headers": headers,
        "body_type": operation.body_type or "json",
        "body_preview": request_body,
        "success_condition": operation.success_condition_json or _default_success_condition(),
        "response_extractors": operation.response_extractors_json or [],
        "timeout_seconds": operation.timeout_seconds or 20,
    }
    if request.dry_run:
        result = OperationTestResponse(
            success=True,
            status="dry_run",
            message="Dry run: сеть не вызывалась. Проверьте final URL, headers, body preview, success condition и extractors.",
            operation_id=operation.id,
            dry_run=True,
            final_url=final_url,
            method=method,
            request=preview,
            response={"mode": "dry_run"},
            warnings=_preview_warnings(operation, final_url),
        )
        _store_last_test(operation, result.success)
        await session.flush()
        return result

    if not request.confirm_real_request:
        raise BadRequestError("Реальный тест операции требует confirm_real_request=true. Для безопасной проверки используйте dry_run=true.")
    if not final_url:
        raise BadRequestError("Невозможно выполнить тест: у операции нет final URL.")

    if request.mock_response:
        http_status = request.http_status
        response_body = request.response_body if request.response_body is not None else operation.sample_response_json if operation.sample_response_json is not None else {"success": True}
        response_headers = {"Content-Type": _content_type(operation.response_body_type or operation.body_type or "json")}
        network = {"mode": "mocked_real_request", "note": "HTTP-клиент не вызывался, использован sample/mock response."}
    else:
        http_status, response_body, response_headers, network = await _send_http(method, final_url, headers, request_body, operation.body_type or "json", operation.timeout_seconds or 20)

    condition_result = evaluate_success_condition(operation.success_condition_json, http_status, response_body)
    extracted, extractor_errors = extract_response(operation.response_extractors_json or [], response_body)
    success = condition_result.success and not extractor_errors
    errors = [*condition_result.errors, *extractor_errors]
    result = OperationTestResponse(
        success=success,
        status="success" if success else "failed",
        message="Операция прошла проверку." if success else "Операция выполнена, но условия успеха или обязательные extractors не прошли.",
        operation_id=operation.id,
        dry_run=False,
        final_url=final_url,
        method=method,
        request=preview,
        response={"headers": response_headers, **network},
        http_status=http_status,
        response_body=response_body,
        success_condition_result=condition_result,
        extracted=extracted,
        errors=errors,
    )
    _store_last_test(operation, result.success)
    await session.flush()
    return result


def evaluate_success_condition(config: dict[str, Any] | None, http_status: int | None, response_body: Any) -> OperationSuccessConditionResult:
    condition_group = config if isinstance(config, dict) else _default_success_condition()
    mode = condition_group.get("mode") if condition_group.get("mode") in {"all", "any"} else "all"
    raw_conditions = condition_group.get("conditions") if isinstance(condition_group.get("conditions"), list) else []
    conditions = raw_conditions or [{"type": "http_status_2xx"}]
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for condition in conditions:
        result = _evaluate_condition(condition, http_status, response_body)
        results.append(result)
        if not result["success"]:
            errors.append(str(result.get("message") or "Success condition failed"))
    success = all(item["success"] for item in results) if mode == "all" else any(item["success"] for item in results)
    if mode == "any" and success:
        errors = []
    return OperationSuccessConditionResult(success=success, mode=mode, conditions=results, errors=errors)


def extract_response(extractors: list[dict[str, Any]], response_body: Any) -> tuple[dict[str, Any], list[str]]:
    extracted: dict[str, Any] = {}
    errors: list[str] = []
    for extractor in extractors:
        name = str(extractor.get("name") or "").strip()
        path = str(extractor.get("path") or "").strip()
        required = bool(extractor.get("required"))
        if not name or not path:
            continue
        found, value = _json_path(response_body, path)
        if found:
            extracted[name] = value
        elif required:
            errors.append(f"В ответе нет обязательного поля {name}.")
    return extracted, errors


async def _send_http(method: str, url: str, headers: dict[str, Any], body: Any, body_type: str, timeout: int) -> tuple[int, Any, dict[str, str], dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            kwargs: dict[str, Any] = {"headers": _http_headers(headers)}
            if method not in {"GET", "DELETE"} and body_type != "none":
                if body_type == "json":
                    kwargs["json"] = body
                else:
                    kwargs["content"] = body if isinstance(body, (str, bytes)) else _json_dumps(body)
            response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise BadRequestError("HTTP test timed out. Увеличьте timeout_seconds или проверьте endpoint.") from exc
    except httpx.HTTPError as exc:
        raise BadRequestError(f"HTTP test failed: {exc}") from exc
    return response.status_code, _response_body(response), dict(response.headers), {"mode": "real_request"}


def _evaluate_condition(condition: dict[str, Any], http_status: int | None, response_body: Any) -> dict[str, Any]:
    condition_type = condition.get("type")
    if condition_type == "always_success":
        return {"type": condition_type, "success": True, "message": "always_success"}
    if condition_type == "http_status_2xx":
        success = http_status is not None and 200 <= http_status <= 299
        return {"type": condition_type, "success": success, "actual": http_status, "message": f"HTTP status {http_status} is not 2xx" if not success else "HTTP status is 2xx"}
    if condition_type == "http_status_equals":
        expected = condition.get("status")
        success = http_status == expected
        return {"type": condition_type, "success": success, "expected": expected, "actual": http_status, "message": f"HTTP status {http_status} != {expected}" if not success else "HTTP status matches"}
    if condition_type == "json_path_exists":
        found, value = _json_path(response_body, str(condition.get("path") or ""))
        return {"type": condition_type, "success": found, "path": condition.get("path"), "actual": value, "message": "JSON path exists" if found else f"JSON path {condition.get('path')} not found"}
    if condition_type == "json_path_equals":
        found, value = _json_path(response_body, str(condition.get("path") or ""))
        expected = condition.get("value")
        success = found and value == expected
        return {"type": condition_type, "success": success, "path": condition.get("path"), "expected": expected, "actual": value, "message": "JSON path equals expected" if success else f"JSON path {condition.get('path')} != {expected}"}
    if condition_type == "response_contains_text":
        expected = str(condition.get("text") or "")
        text = response_body if isinstance(response_body, str) else _json_dumps(response_body)
        success = expected in text
        return {"type": condition_type, "success": success, "expected": expected, "message": "response contains text" if success else "response does not contain expected text"}
    return {"type": condition_type, "success": False, "message": "Unsupported success condition"}


def _json_path(value: Any, path: str) -> tuple[bool, Any]:
    normalized = path.strip()
    if not normalized:
        return False, None
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized == "$":
        return True, value
    current = value
    for part in normalized.split("."):
        if not part:
            continue
        key, indexes = _split_indexes(part)
        if key:
            if not isinstance(current, dict) or key not in current:
                return False, None
            current = current[key]
        for index in indexes:
            if not isinstance(current, list) or index >= len(current):
                return False, None
            current = current[index]
    return True, current


def _split_indexes(part: str) -> tuple[str, list[int]]:
    key = part.split("[", 1)[0]
    indexes: list[int] = []
    rest = part[len(key):]
    while rest.startswith("[") and "]" in rest:
        raw, rest = rest[1:].split("]", 1)
        try:
            indexes.append(int(raw))
        except ValueError:
            return key, indexes
    return key, indexes


def _headers(operation: OperationProfile, connection: Any) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    config = getattr(connection, "config_json", {}) or {}
    if isinstance(config.get("headers"), dict):
        headers.update(config["headers"])
    if isinstance(operation.headers_json, dict):
        headers.update(operation.headers_json)
    return headers


def _request_body(operation: OperationProfile, request: OperationTestRequest) -> Any:
    if request.request_body is not None:
        return request.request_body
    if operation.sample_request_json is not None:
        return operation.sample_request_json
    if operation.request_template_json is not None:
        return operation.request_template_json
    if operation.request_template_text is not None:
        return operation.request_template_text
    if (operation.body_type or "json") == "none":
        return None
    return {}


def _connection_base_url(connection: Any) -> str | None:
    if connection is None:
        return None
    config = getattr(connection, "config_json", {}) or {}
    return config.get("http_service_base_url") or config.get("base_url") or config.get("url")


def _preview_warnings(operation: OperationProfile, final_url: str | None) -> list[str]:
    warnings: list[str] = []
    if not final_url:
        warnings.append("У операции нет final URL: выберите Connection Profile + path или задайте full_url.")
    if operation.kind in {"printer_operation", "file_operation"}:
        warnings.append("Этот тип операции пока частично реализован: доступен каталог и dry-run, production runner будет добавлен отдельно.")
    return warnings


def _http_headers(headers: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        if isinstance(value, dict):
            continue
        result[str(key)] = str(value)
    return result


def _response_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        try:
            return response.json()
        except ValueError:
            return response.text
    try:
        return response.json()
    except ValueError:
        return response.text


def _default_success_condition() -> dict[str, Any]:
    return {"mode": "all", "conditions": [{"type": "http_status_2xx"}]}


def _content_type(body_type: str) -> str:
    if body_type == "xml":
        return "application/xml"
    if body_type == "raw_text":
        return "text/plain"
    if body_type == "form":
        return "application/x-www-form-urlencoded"
    return "application/json"


def _json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def _store_last_test(operation: OperationProfile, success: bool) -> None:
    operation.last_test_at = datetime.now(timezone.utc)
    operation.last_test_success = success
