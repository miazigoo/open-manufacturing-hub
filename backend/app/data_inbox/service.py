from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from xml.etree import ElementTree

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ArtifactType, EventStatus, RunMode, RunStatus, StepStatus
from app.core.errors import BadRequestError, NotFoundError
from app.data_inbox.models import InboxRecord, InboxTemplate
from app.data_inbox.schemas import InboxTemplateCreate, InboxTemplatePatch
from app.artifacts.models import Artifact
from app.artifacts.models import content_hash as artifact_content_hash
from app.artifacts.models import content_size as artifact_content_size
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.json_builder.engine import build_json_from_template

GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_PAYLOAD_ARTIFACT_CHARS = 65536

DEFAULT_RESPONSE = {
    "ok": True,
    "record_id": "{{record.id}}",
    "status": "{{record.status}}",
    "warnings_count": "{{record.warnings_count}}",
}


async def list_templates(session: AsyncSession) -> list[InboxTemplate]:
    result = await session.execute(select(InboxTemplate).order_by(InboxTemplate.created_at.desc()))
    return list(result.scalars().all())


async def get_template_or_404(session: AsyncSession, template_id: UUID) -> InboxTemplate:
    template = await session.get(InboxTemplate, template_id)
    if template is None:
        raise NotFoundError("Inbox template not found")
    return template


async def get_template_by_slug(session: AsyncSession, slug: str) -> InboxTemplate | None:
    result = await session.execute(select(InboxTemplate).where(InboxTemplate.slug == slug).limit(1))
    return result.scalar_one_or_none()


async def create_template(session: AsyncSession, payload: InboxTemplateCreate) -> InboxTemplate:
    _validate_template_schema(payload.schema_json)
    existing = await get_template_by_slug(session, payload.slug)
    if existing is not None:
        raise BadRequestError(f"Шаблон с таким адресом уже существует: {payload.slug}")
    template = InboxTemplate(**payload.model_dump())
    session.add(template)
    await session.flush()
    return template


async def patch_template(session: AsyncSession, template_id: UUID, patch: InboxTemplatePatch) -> InboxTemplate:
    template = await get_template_or_404(session, template_id)
    data = patch.model_dump(exclude_unset=True)
    if "schema_json" in data and data["schema_json"] is not None:
        _validate_template_schema(data["schema_json"])
    if "slug" in data and data["slug"] and data["slug"] != template.slug:
        existing = await get_template_by_slug(session, data["slug"])
        if existing is not None:
            raise BadRequestError(f"Шаблон с таким адресом уже существует: {data['slug']}")
    if "auth_token" in data and data["auth_token"] is None:
        data.pop("auth_token")
    for key, value in data.items():
        setattr(template, key, value)
    await session.flush()
    return template


async def delete_template(session: AsyncSession, template_id: UUID) -> None:
    template = await get_template_or_404(session, template_id)
    await session.delete(template)
    await session.flush()


def _validate_template_schema(schema_json: dict[str, Any]) -> None:
    fields = (schema_json or {}).get("fields")
    if fields is None:
        return
    if not isinstance(fields, list):
        raise BadRequestError("schema_json.fields должен быть массивом полей.")
    seen: set[str] = set()
    for raw in fields:
        if not isinstance(raw, dict) or not str(raw.get("path") or "").strip():
            raise BadRequestError("Каждое поле шаблона должно иметь path.")
        path = str(raw["path"]).strip()
        if path in seen:
            raise BadRequestError(f"Поле шаблона дублируется: {path}")
        seen.add(path)


# --- payload parsing and validation ---


def parse_payload(input_mode: str, payload: Any, text: str | None) -> dict[str, Any]:
    if input_mode == "raw_text":
        return {"text": text if text is not None else (payload if isinstance(payload, str) else "")}
    if input_mode == "xml":
        xml_text = text if text is not None else (payload.get("xml") if isinstance(payload, dict) else payload)
        if not isinstance(xml_text, str) or not xml_text.strip():
            raise BadRequestError("Ожидался XML в теле запроса.")
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            raise BadRequestError(f"XML не парсится: {exc}") from exc
        return {_strip_ns(root.tag): _xml_to_dict(root)}
    if isinstance(payload, dict):
        return payload
    raise BadRequestError("Ожидался JSON object в теле запроса.")


def _xml_to_dict(node: ElementTree.Element) -> Any:
    children = list(node)
    if not children:
        return (node.text or "").strip()
    result: dict[str, Any] = {}
    for child in children:
        key = _strip_ns(child.tag)
        value = _xml_to_dict(child)
        if key in result:
            existing = result[key]
            if not isinstance(existing, list):
                result[key] = [existing]
            result[key].append(value)
        else:
            result[key] = value
    return result


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _get_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split(".") if path else []:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def validate_fields(template: InboxTemplate, payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Extract fields, collect warnings and the list of missing required paths."""
    fields = (template.schema_json or {}).get("fields") or []
    extracted: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []
    missing_required: list[str] = []
    for raw in fields:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path") or "").strip()
        if not path:
            continue
        field_type = str(raw.get("type") or "string")
        value = _get_path(payload, path)
        if value is None:
            if raw.get("required"):
                missing_required.append(path)
            continue
        coerced, warning = _coerce_type(value, field_type)
        if warning is not None:
            warnings.append({"path": path, "message": warning})
        extracted[path] = coerced
    return extracted, warnings, missing_required


def _coerce_type(value: Any, field_type: str) -> tuple[Any, str | None]:
    if field_type == "raw":
        return value, None
    if field_type == "string":
        if isinstance(value, str):
            return value, None
        return str(value), f"значение приведено к строке (было {type(value).__name__})"
    if field_type == "number":
        if isinstance(value, bool):
            return None, "ожидалось число, получено булево"
        if isinstance(value, (int, float)):
            return value, None
        if isinstance(value, str):
            try:
                return float(value.replace(",", ".")), "число получено строкой и приведено к number"
            except ValueError:
                return None, f"ожидалось число, получено '{value}'"
        return None, f"ожидалось число, получено {type(value).__name__}"
    if field_type == "boolean":
        if isinstance(value, bool):
            return value, None
        if isinstance(value, str) and value.strip().lower() in {"true", "1", "да", "yes"}:
            return True, "булево получено строкой"
        if isinstance(value, str) and value.strip().lower() in {"false", "0", "нет", "no"}:
            return False, "булево получено строкой"
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value), "булево получено числом"
        return None, "ожидалось булево (true/false)"
    if field_type == "guid":
        if isinstance(value, str) and GUID_RE.match(value.strip()):
            return value.strip(), None
        return None, "ожидался GUID вида xxxxxxxx-xxxx-..."
    if field_type == "date":
        if isinstance(value, str) and DATE_RE.match(value.strip()):
            return value.strip(), None
        return None, "ожидалась дата вида ГГГГ-ММ-ДД"
    if field_type == "datetime":
        if isinstance(value, str) and value.strip():
            return value.strip(), None
        return None, "ожидалась дата-время строкой"
    if field_type == "array":
        if isinstance(value, list):
            return value, None
        return None, "ожидался массив"
    if field_type == "object":
        if isinstance(value, dict):
            return value, None
        return None, "ожидался объект"
    return value, None


def apply_missing_policy(template: InboxTemplate, extracted: dict[str, Any], missing_required: list[str]) -> tuple[str, list[dict[str, Any]]]:
    """Apply the missing policy. Returns (status, extra_warnings)."""
    if not missing_required:
        return "stored", []
    policy = template.missing_policy
    if policy == "reject":
        return "rejected", []
    warnings = []
    for path in missing_required:
        raw_field = next((item for item in (template.schema_json or {}).get("fields") or [] if str(item.get("path") or "") == path), {})
        if policy == "fill_defaults":
            default = raw_field.get("default")
            extracted[path] = default
            warnings.append({"path": path, "message": f"обязательное поле отсутствовало, подставлено значение по умолчанию: {default!r}"})
        else:
            warnings.append({"path": path, "message": "обязательное поле отсутствует (принято с предупреждением)"})
    return "accepted_with_warnings", warnings


def render_response(template: InboxTemplate, *, record_id: str | None, status: str, fields: dict[str, Any], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    response_template = template.response_json or DEFAULT_RESPONSE
    scope = {
        "record": {
            "id": record_id or "",
            "status": status,
            "warnings_count": len(warnings),
        },
        "fields": fields,
        "warnings": warnings,
        "status": status,
    }
    try:
        rendered = build_json_from_template(response_template, scope)
    except Exception:
        return {"ok": status != "rejected", "record_id": record_id, "status": status, "warnings_count": len(warnings)}
    if isinstance(rendered, dict):
        return rendered
    return {"ok": status != "rejected", "result": rendered}


async def test_template(template: InboxTemplate, payload: dict[str, Any]) -> dict[str, Any]:
    extracted, warnings, missing_required = validate_fields(template, payload)
    status, policy_warnings = apply_missing_policy(template, extracted, missing_required)
    warnings = warnings + policy_warnings
    if status == "stored" and warnings:
        status = "accepted_with_warnings"
    response = render_response(template, record_id="(новая запись)", status=status, fields=extracted, warnings=warnings)
    return {"status": status, "fields": extracted, "warnings": warnings, "response": response}


async def receive(
    session: AsyncSession,
    template: InboxTemplate,
    payload: dict[str, Any],
    *,
    source_ip: str | None,
) -> tuple[InboxRecord | None, dict[str, Any], int]:
    extracted, warnings, missing_required = validate_fields(template, payload)
    status, policy_warnings = apply_missing_policy(template, extracted, missing_required)
    warnings = warnings + policy_warnings
    if status == "stored" and warnings:
        status = "accepted_with_warnings"

    record: InboxRecord | None = None
    if template.storage_mode != "none":
        record = InboxRecord(
            template_id=template.id,
            status=status,
            payload_json=_trim_payload(payload),
            fields_json=extracted,
            warnings_json=warnings,
            source_ip=source_ip,
        )
        session.add(record)
        await session.flush()
    await _log_inbox_event(session, template, status, extracted, warnings, record)
    response = render_response(template, record_id=str(record.id) if record else None, status=status, fields=extracted, warnings=warnings)
    if status == "rejected":
        response["ok"] = False
        response["missing_required"] = missing_required
        response["message"] = "В данных не хватает обязательных полей: " + ", ".join(missing_required)
        return record, response, 400
    return record, response, 200


def _trim_payload(payload: dict[str, Any]) -> dict[str, Any]:
    import json as _json

    text = _json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= MAX_PAYLOAD_ARTIFACT_CHARS:
        return payload
    return {"_truncated": True, "preview": text[:MAX_PAYLOAD_ARTIFACT_CHARS]}


async def _log_inbox_event(
    session: AsyncSession,
    template: InboxTemplate,
    status: str,
    fields: dict[str, Any],
    warnings: list[dict[str, Any]],
    record: InboxRecord | None,
) -> None:
    from uuid import uuid4

    now = datetime.now(UTC)
    event = IntegrationEvent(
        correlation_id=f"inbox:{template.slug}:{uuid4()}",
        source_system=f"Inbox {template.slug}",
        target_system="OMH Data Inbox",
        event_type="inbox.received",
        entity_type="InboxRecord",
        entity_id=str(record.id) if record else None,
        status=EventStatus.SUCCESS if status != "rejected" else EventStatus.FAILED,
    )
    session.add(event)
    await session.flush()
    run = EventRun(event_id=event.id, run_number=1, mode=RunMode.NORMAL, status=RunStatus.SUCCESS if status != "rejected" else RunStatus.FAILED, started_at=now, finished_at=now)
    session.add(run)
    await session.flush()
    step = EventStep(
        run_id=run.id,
        step_order=1,
        step_name="inbox_receive",
        status=StepStatus.SUCCESS if status != "rejected" else StepStatus.FAILED,
        started_at=now,
        finished_at=now,
        error_code="INBOX_VALIDATION_FAILED" if status == "rejected" else None,
        error_message=("; ".join(item["message"] for item in warnings)) if status == "rejected" else None,
    )
    session.add(step)
    await session.flush()
    content = {
        "template": template.slug,
        "status": status,
        "fields": fields,
        "warnings": warnings,
        "record_id": str(record.id) if record else None,
    }
    session.add(
        Artifact(
            event_id=event.id,
            run_id=run.id,
            step_id=step.id,
            artifact_type=ArtifactType.INCOMING_RESPONSE.value if status != "rejected" else ArtifactType.ERROR_DETAILS.value,
            name="inbox_receive.json",
            content_json=content,
            content_hash=artifact_content_hash(content),
            size_bytes=artifact_content_size(content),
        )
    )
    await session.flush()


# --- records management ---


async def list_records(
    session: AsyncSession,
    *,
    template_id: UUID | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[InboxRecord], int]:
    query = select(InboxRecord)
    count_query = select(func.count()).select_from(InboxRecord)
    filters = []
    if template_id is not None:
        filters.append(InboxRecord.template_id == template_id)
    if status:
        filters.append(InboxRecord.status == status)
    if date_from is not None:
        filters.append(InboxRecord.created_at >= date_from)
    if date_to is not None:
        filters.append(InboxRecord.created_at <= date_to)
    if search:
        filters.append(func.cast(InboxRecord.fields_json, db_string()).ilike(f"%{search}%"))
    for condition in filters:
        query = query.where(condition)
        count_query = count_query.where(condition)
    total = (await session.execute(count_query)).scalar_one()
    result = await session.execute(query.order_by(InboxRecord.created_at.desc()).limit(min(limit, 500)).offset(offset))
    return list(result.scalars().all()), total


def db_string():
    from sqlalchemy import String

    return String


async def get_record_or_404(session: AsyncSession, record_id: UUID) -> InboxRecord:
    record = await session.get(InboxRecord, record_id)
    if record is None:
        raise NotFoundError("Inbox record not found")
    return record


async def resend_record(record: InboxRecord, url: str, timeout_seconds: float) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=record.payload_json)
    except httpx.HTTPError as exc:
        return {"success": False, "status": "failed", "message": f"Отправка не удалась: {exc}", "details": {"url": url}}
    body: Any
    try:
        body = response.json()
    except ValueError:
        body = response.text[:1000]
    return {
        "success": response.status_code < 400,
        "status": "success" if response.status_code < 400 else "failed",
        "message": f"HTTP {response.status_code}",
        "details": {"url": url, "http_status": response.status_code, "response": body},
    }
