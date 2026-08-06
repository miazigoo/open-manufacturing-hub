from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import BadRequestError, NotFoundError
from app.data_inbox import service
from app.data_inbox.schemas import (
    InboxRecordPatch,
    InboxRecordRead,
    InboxResendRequest,
    InboxResendResponse,
    InboxTemplateCreate,
    InboxTemplatePatch,
    InboxTemplateRead,
    InboxTemplateTestRequest,
    InboxTemplateTestResponse,
)

router = APIRouter(tags=["data-inbox"])


def _read_template(template) -> InboxTemplateRead:
    return InboxTemplateRead(
        id=template.id,
        slug=template.slug,
        name=template.name,
        description=template.description,
        enabled=template.enabled,
        input_mode=template.input_mode,
        schema_json=template.schema_json,
        missing_policy=template.missing_policy,
        storage_mode=template.storage_mode,
        storage_days=template.storage_days,
        response_json=template.response_json,
        auth_token_set=bool(template.auth_token),
        created_at=template.created_at,
    )


@router.get("/api/inbox-templates", response_model=list[InboxTemplateRead])
async def list_templates(session: AsyncSession = Depends(get_session)):
    return [_read_template(item) for item in await service.list_templates(session)]


@router.post("/api/inbox-templates", response_model=InboxTemplateRead)
async def create_template(payload: InboxTemplateCreate, session: AsyncSession = Depends(get_session)):
    template = await service.create_template(session, payload)
    await session.commit()
    return _read_template(template)


@router.get("/api/inbox-templates/{template_id}", response_model=InboxTemplateRead)
async def get_template(template_id: UUID, session: AsyncSession = Depends(get_session)):
    return _read_template(await service.get_template_or_404(session, template_id))


@router.patch("/api/inbox-templates/{template_id}", response_model=InboxTemplateRead)
async def patch_template(template_id: UUID, payload: InboxTemplatePatch, session: AsyncSession = Depends(get_session)):
    template = await service.patch_template(session, template_id, payload)
    await session.commit()
    return _read_template(template)


@router.delete("/api/inbox-templates/{template_id}", status_code=204)
async def delete_template(template_id: UUID, session: AsyncSession = Depends(get_session)):
    await service.delete_template(session, template_id)
    await session.commit()


@router.post("/api/inbox-templates/{template_id}/test", response_model=InboxTemplateTestResponse)
async def test_template(template_id: UUID, payload: InboxTemplateTestRequest, session: AsyncSession = Depends(get_session)):
    template = await service.get_template_or_404(session, template_id)
    parsed = service.parse_payload(template.input_mode, payload.payload, payload.text)
    return await service.test_template(template, parsed)


@router.get("/api/inbox-records", response_model=dict)
async def list_records(
    template_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    records, total = await service.list_records(
        session,
        template_id=template_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"total": total, "items": [InboxRecordRead.model_validate(record) for record in records]}


@router.get("/api/inbox-records/export.csv")
async def export_records_csv(
    template_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    import csv
    import io

    records, _ = await service.list_records(session, template_id=template_id, status=status, limit=500)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "template_id", "status", "created_at", "fields", "warnings"])
    import json as _json

    for record in records:
        writer.writerow([
            str(record.id),
            str(record.template_id),
            record.status,
            record.created_at.isoformat(),
            _json.dumps(record.fields_json, ensure_ascii=False),
            _json.dumps(record.warnings_json, ensure_ascii=False),
        ])
    return JSONResponse(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inbox-records.csv"'},
    )


@router.get("/api/inbox-records/{record_id}", response_model=InboxRecordRead)
async def get_record(record_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_record_or_404(session, record_id)


@router.patch("/api/inbox-records/{record_id}", response_model=InboxRecordRead)
async def patch_record(record_id: UUID, payload: InboxRecordPatch, session: AsyncSession = Depends(get_session)):
    record = await service.get_record_or_404(session, record_id)
    if payload.payload_json is not None:
        record.payload_json = payload.payload_json
    if payload.fields_json is not None:
        record.fields_json = payload.fields_json
    await session.commit()
    return record


@router.delete("/api/inbox-records/{record_id}", status_code=204)
async def delete_record(record_id: UUID, session: AsyncSession = Depends(get_session)):
    record = await service.get_record_or_404(session, record_id)
    await session.delete(record)
    await session.commit()


@router.post("/api/inbox-records/{record_id}/resend", response_model=InboxResendResponse)
async def resend_record(record_id: UUID, payload: InboxResendRequest, session: AsyncSession = Depends(get_session)):
    record = await service.get_record_or_404(session, record_id)
    if payload.flow_slug:
        raise BadRequestError("Повторная отправка в flow пока доступна через Test Console; укажите url.")
    if not payload.url:
        raise BadRequestError("Укажите url для повторной отправки.")
    return await service.resend_record(record, payload.url, payload.timeout_seconds)


@router.post("/api/inbox/{slug}")
async def receive_inbox(slug: str, request: Request, session: AsyncSession = Depends(get_session)):
    template = await service.get_template_by_slug(session, slug)
    if template is None:
        return JSONResponse(status_code=404, content={"ok": False, "message": f"Приемник '{slug}' не найден. Проверьте адрес или создайте шаблон."})
    if not template.enabled:
        return JSONResponse(status_code=403, content={"ok": False, "message": f"Приемник '{slug}' выключен. Включите шаблон в настройках."})
    if template.auth_token:
        token = request.headers.get("x-omh-token") or ""
        if token != template.auth_token:
            return JSONResponse(status_code=401, content={"ok": False, "message": "Неверный или отсутствующий X-OMH-Token."})

    content_type = request.headers.get("content-type", "")
    if template.input_mode == "json":
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"ok": False, "message": "Тело запроса не является корректным JSON."})
        text = None
    else:
        raw = await request.body()
        text = raw.decode("utf-8", errors="replace")
        body = {"xml": text} if template.input_mode == "xml" else text
        if template.input_mode == "json" and "application/json" not in content_type:
            return JSONResponse(status_code=400, content={"ok": False, "message": "Ожидался JSON (Content-Type: application/json)."})
    try:
        parsed = service.parse_payload(template.input_mode, body, text)
    except BadRequestError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})
    source_ip = request.client.host if request.client else None
    record, response, status_code = await service.receive(session, template, parsed, source_ip=source_ip)
    await session.commit()
    return JSONResponse(status_code=status_code, content=response)
