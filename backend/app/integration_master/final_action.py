from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.integration_master.payload_renderer import (
    PayloadRenderError,
    render_json_template,
    render_text_template,
    render_xml_template,
    resolve_template_path,
)
from app.integration_master.schemas import FinalActionConfig

PRIVATE_HOST_HINTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
MAX_PREVIEW_ARRAY_ITEMS = 3
HTTP_CLIENT_CLS = httpx.AsyncClient


@dataclass(slots=True)
class FinalActionError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class FinalActionPreview:
    success: bool
    action_type: str
    send_preview: dict[str, Any] | None
    caller_response_preview: Any
    human_preview: str
    warnings: list[str]
    errors: list[str]
    error_code: str | None = None


@dataclass(slots=True)
class FinalActionTestResult:
    success: bool
    dry_run: bool
    error_code: str | None = None
    message: str | None = None
    would_send: dict[str, Any] | None = None
    would_return_to_caller: Any = None
    target_status: int | None = None
    target_response: Any = None
    caller_response: Any = None


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    error_code: str | None = None


def preview_final_action(final_action: FinalActionConfig, variables: dict[str, Any]) -> FinalActionPreview:
    validation = validate_final_action(final_action, variables)
    if not validation.valid:
        return FinalActionPreview(
            success=False,
            action_type=final_action.type,
            send_preview=None,
            caller_response_preview=None,
            human_preview="\n".join(validation.errors),
            warnings=validation.warnings,
            errors=validation.errors,
            error_code=validation.error_code,
        )
    try:
        send_preview = _send_preview(final_action, variables) if _needs_endpoint(final_action) else None
        caller_response = _caller_response_preview(final_action, variables)
        return FinalActionPreview(
            success=True,
            action_type=final_action.type,
            send_preview=send_preview,
            caller_response_preview=caller_response,
            human_preview=_human_preview(final_action, send_preview, caller_response),
            warnings=validation.warnings,
            errors=[],
        )
    except (FinalActionError, PayloadRenderError) as exc:
        code = exc.code if isinstance(exc, (FinalActionError, PayloadRenderError)) else "FINAL_ACTION_RENDER_FAILED"
        return FinalActionPreview(
            success=False,
            action_type=final_action.type,
            send_preview=None,
            caller_response_preview=None,
            human_preview=str(exc),
            warnings=validation.warnings,
            errors=[str(exc)],
            error_code=code,
        )


async def test_final_action(final_action: FinalActionConfig, variables: dict[str, Any], *, dry_run: bool = True) -> FinalActionTestResult:
    preview = preview_final_action(final_action, variables)
    if not preview.success:
        return FinalActionTestResult(success=False, dry_run=dry_run, error_code=preview.error_code or "FINAL_ACTION_INVALID", message="; ".join(preview.errors))
    if dry_run or not _needs_endpoint(final_action):
        return FinalActionTestResult(
            success=True,
            dry_run=True,
            would_send=preview.send_preview,
            would_return_to_caller=preview.caller_response_preview,
            caller_response=preview.caller_response_preview if not _needs_endpoint(final_action) else None,
        )

    assert preview.send_preview is not None
    request_body = _request_body_for_http(final_action, variables)
    headers = _string_headers(_render_headers(final_action.headers, variables))
    try:
        async with HTTP_CLIENT_CLS(timeout=final_action.timeout_seconds) as client:
            response = await client.request(
                final_action.method,
                preview.send_preview["url"],
                headers=headers,
                **request_body,
            )
    except httpx.TimeoutException:
        return FinalActionTestResult(success=False, dry_run=False, error_code="TARGET_ENDPOINT_TIMEOUT", message="Endpoint не ответил за заданное время.", would_send=preview.send_preview)
    except httpx.HTTPError as exc:
        return FinalActionTestResult(success=False, dry_run=False, error_code="TARGET_ENDPOINT_REQUEST_FAILED", message=f"Не удалось выполнить HTTP-запрос: {exc}", would_send=preview.send_preview)

    target_response = _response_body(response)
    if response.status_code >= 400:
        return FinalActionTestResult(
            success=False,
            dry_run=False,
            error_code="TARGET_ENDPOINT_ERROR",
            message="Endpoint вернул ошибку. Оригинальный ответ сохранён и показан ниже.",
            would_send=preview.send_preview,
            target_status=response.status_code,
            target_response=target_response,
        )

    caller_response = target_response if _return_type(final_action) == "proxy_response" else preview.caller_response_preview
    return FinalActionTestResult(
        success=True,
        dry_run=False,
        would_send=preview.send_preview,
        target_status=response.status_code,
        target_response=target_response,
        caller_response=caller_response,
    )


def validate_final_action(final_action: FinalActionConfig, variables: dict[str, Any] | None = None) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    error_code: str | None = None
    variables = variables or {}

    if final_action.type in {"send_endpoint", "send_and_return_response"}:
        url = (final_action.url or "").strip()
        if not url:
            errors.append("Укажите URL endpoint'а.")
            error_code = error_code or "FINAL_ACTION_URL_REQUIRED"
        elif not _valid_http_url(url):
            errors.append("URL должен начинаться с http:// или https://.")
            error_code = error_code or "FINAL_ACTION_URL_INVALID"
        else:
            warnings.extend(_url_warnings(url))
        if final_action.body_source == "custom" and (final_action.custom_body is None or final_action.custom_body == ""):
            errors.append("Укажите custom body или выберите target_payload.")
            error_code = error_code or "FINAL_ACTION_BODY_REQUIRED"
        if final_action.body_source == "target_payload" and variables and "target_payload" not in variables:
            errors.append("Выберите, что отправлять в body. Обычно это target_payload.")
            error_code = error_code or "FINAL_ACTION_BODY_SOURCE_MISSING"
        if final_action.body_type == "form":
            errors.append("Form body появится позже. Сейчас доступны JSON, XML и raw text.")
            error_code = error_code or "FINAL_ACTION_BODY_TYPE_UNSUPPORTED"
    elif final_action.type == "return_response":
        if final_action.body_source == "target_payload" and variables and "target_payload" not in variables:
            errors.append("Переменная target_payload не найдена для ответа вызывающей системе.")
            error_code = error_code or "FINAL_ACTION_BODY_SOURCE_MISSING"
    elif final_action.type == "accepted_event":
        pass
    else:
        errors.append("Выберите тип финального действия.")
        error_code = error_code or "FINAL_ACTION_TYPE_INVALID"

    if final_action.timeout_seconds < 1 or final_action.timeout_seconds > 300:
        errors.append("Timeout должен быть от 1 до 300 секунд.")
        error_code = error_code or "FINAL_ACTION_TIMEOUT_INVALID"
    if final_action.return_to_caller.status_code < 100 or final_action.return_to_caller.status_code > 599:
        errors.append("HTTP status должен быть от 100 до 599.")
        error_code = error_code or "FINAL_ACTION_STATUS_INVALID"
    return ValidationResult(valid=not errors, errors=_dedupe(errors), warnings=_dedupe(warnings), error_code=error_code)


def _needs_endpoint(final_action: FinalActionConfig) -> bool:
    return final_action.type in {"send_endpoint", "send_and_return_response"}


def _send_preview(final_action: FinalActionConfig, variables: dict[str, Any]) -> dict[str, Any]:
    url = render_text_template((final_action.url or "").strip(), variables)
    body = _body_preview(final_action, variables)
    return {
        "method": final_action.method,
        "url": url,
        "headers": _render_headers(final_action.headers, variables),
        "body_type": final_action.body_type,
        "body_source": final_action.body_source,
        "body_preview": _truncate_preview(body),
        "timeout_seconds": final_action.timeout_seconds,
    }


def _caller_response_preview(final_action: FinalActionConfig, variables: dict[str, Any]) -> Any:
    if final_action.type == "accepted_event" or _return_type(final_action) == "accepted_event":
        return _accepted_response(variables)
    if final_action.type == "return_response":
        return _body_preview(final_action, variables)
    return_type = _return_type(final_action)
    if final_action.type == "send_and_return_response" or return_type == "proxy_response":
        return {"proxy_response": True, "message": "OMH вернёт вызывающей системе ответ endpoint'а."}
    if return_type == "fixed_success":
        return {"ok": True}
    if return_type in {"custom_json", "custom_xml", "custom_raw"}:
        return _render_return_body(final_action, variables)
    return {"ok": True}


def _body_preview(final_action: FinalActionConfig, variables: dict[str, Any]) -> Any:
    if final_action.body_source == "none":
        return None
    if final_action.body_source == "target_payload":
        return resolve_template_path("target_payload", variables)
    if final_action.body_type == "json":
        return render_json_template(_json_template(final_action.custom_body), variables)
    if final_action.body_type == "xml":
        return render_xml_template(_text_template(final_action.custom_body), variables)
    if final_action.body_type == "raw_text":
        return render_text_template(_text_template(final_action.custom_body), variables)
    raise FinalActionError("FINAL_ACTION_BODY_TYPE_UNSUPPORTED", "Form body появится позже. Сейчас доступны JSON, XML и raw text.")


def _render_return_body(final_action: FinalActionConfig, variables: dict[str, Any]) -> Any:
    return_type = _return_type(final_action)
    body = final_action.return_to_caller.body
    if return_type == "custom_json":
        return render_json_template(_json_template(body), variables)
    if return_type == "custom_xml":
        return render_xml_template(_text_template(body), variables)
    if return_type == "custom_raw":
        return render_text_template(_text_template(body), variables)
    return body


def _request_body_for_http(final_action: FinalActionConfig, variables: dict[str, Any]) -> dict[str, Any]:
    if final_action.body_source == "none" or final_action.method == "GET":
        return {}
    body = _body_preview(final_action, variables)
    if final_action.body_type == "json":
        return {"json": body}
    if body is None:
        return {}
    return {"content": body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)}


def _render_headers(headers: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    rendered = render_json_template(headers or {}, variables)
    return rendered if isinstance(rendered, dict) else {}


def _string_headers(headers: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        if isinstance(value, dict) and "$secret" in value:
            result[key] = f"<secret:{value.get('$secret')}>"
        elif value is not None:
            result[key] = str(value)
    return result


def _accepted_response(variables: dict[str, Any]) -> dict[str, Any]:
    context = variables.get("context") if isinstance(variables.get("context"), dict) else {}
    event_id = context.get("event_id") or "preview-event-id"
    queue_item_id = context.get("queue_item_id") or "preview-queue-item-id"
    return {
        "accepted": True,
        "event_id": event_id,
        "queue_item_id": queue_item_id,
        "timeline_url": f"/events/{event_id}",
    }


def _human_preview(final_action: FinalActionConfig, send_preview: dict[str, Any] | None, caller_response: Any) -> str:
    if final_action.type == "return_response":
        return "OMH вернёт вызывающей системе configured response."
    if final_action.type == "accepted_event":
        return "OMH не будет ждать завершения. Он вернёт event_id и поставит запрос в очередь."
    if final_action.type == "send_and_return_response" or _return_type(final_action) == "proxy_response":
        return "OMH отправит запрос на endpoint и вернёт вызывающей системе ответ endpoint'а."
    method = send_preview.get("method") if send_preview else final_action.method
    url = send_preview.get("url") if send_preview else final_action.url
    return f"OMH отправит {method} {url} и вернёт вызывающей системе {json.dumps(caller_response, ensure_ascii=False)}."


def _return_type(final_action: FinalActionConfig) -> str:
    if final_action.type == "send_and_return_response":
        return "proxy_response"
    return final_action.return_to_caller.type


def _json_template(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if value is None:
        return {}
    return value


def _text_template(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _response_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "json" in content_type.lower():
        try:
            return response.json()
        except ValueError:
            return response.text
    try:
        return response.json()
    except ValueError:
        return response.text


def _valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _url_warnings(url: str) -> list[str]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host in PRIVATE_HOST_HINTS:
        return ["URL указывает на localhost/private адрес. Для production проверьте сетевую доступность из backend-контейнера."]
    try:
        ip = socket.inet_aton(host)
    except OSError:
        return []
    first = ip[0]
    second = ip[1]
    if first == 10 or first == 127 or (first == 172 and 16 <= second <= 31) or (first == 192 and second == 168):
        return ["URL указывает на private IP. Это разрешено, но проверьте сетевую доступность из backend-контейнера."]
    return []


def _truncate_preview(value: Any) -> Any:
    if isinstance(value, list):
        if len(value) > MAX_PREVIEW_ARRAY_ITEMS:
            return value[:MAX_PREVIEW_ARRAY_ITEMS] + [{"_preview_truncated": len(value) - MAX_PREVIEW_ARRAY_ITEMS}]
        return [_truncate_preview(item) for item in value]
    if isinstance(value, dict):
        return {key: _truncate_preview(item) for key, item in value.items()}
    return value


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
