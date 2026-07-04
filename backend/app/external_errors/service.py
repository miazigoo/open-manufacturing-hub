from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.core.errors import NotFoundError
from app.events.models import EventStep, IntegrationEvent
from app.external_errors.models import ExternalErrorRecord


async def record_external_error(
    session: AsyncSession,
    *,
    event: IntegrationEvent,
    run_id: UUID,
    step: EventStep,
    payload: dict[str, Any],
    request_artifact_id: UUID | None = None,
    response_artifact_id: UUID | None = None,
    error_artifact_id: UUID | None = None,
) -> ExternalErrorRecord:
    record = ExternalErrorRecord(
        event_id=event.id,
        run_id=run_id,
        step_id=step.id,
        source_system=payload.get("source_system") or event.source_system,
        target_system=payload.get("target_system") or event.target_system,
        connector_type=payload.get("connector_type"),
        connector_name=payload.get("connector_name") or event.target_system,
        operation=payload.get("operation"),
        endpoint_url=payload.get("endpoint_url"),
        http_method=payload.get("http_method"),
        http_status=payload.get("http_status"),
        normalized_code=str(payload.get("normalized_code") or step.error_code or "EXTERNAL_ERROR"),
        normalized_message=str(payload.get("normalized_message") or step.error_message or "External system returned an error"),
        human_title=payload.get("human_title"),
        human_summary=payload.get("human_summary"),
        developer_message=payload.get("developer_message"),
        hint=payload.get("hint"),
        external_error_code=payload.get("external_error_code"),
        external_error_message=payload.get("external_error_message"),
        external_error_type=payload.get("external_error_type"),
        response_content_type=payload.get("response_content_type"),
        response_body_text=payload.get("response_body_text"),
        response_body_json=payload.get("response_body_json"),
        response_body_xml=payload.get("response_body_xml"),
        response_body_preview=payload.get("response_body_preview"),
        response_body_sha256=payload.get("response_body_sha256"),
        response_size_bytes=payload.get("response_size_bytes"),
        request_artifact_id=request_artifact_id,
        response_artifact_id=response_artifact_id,
        error_artifact_id=error_artifact_id,
    )
    session.add(record)
    await session.flush()
    return record


async def list_for_event(session: AsyncSession, event_id: UUID) -> list[ExternalErrorRecord]:
    result = await session.execute(select(ExternalErrorRecord).where(ExternalErrorRecord.event_id == event_id).order_by(ExternalErrorRecord.created_at.asc()))
    return list(result.scalars().all())


async def list_for_incident(session: AsyncSession, incident_id: UUID, limit: int = 5) -> list[ExternalErrorRecord]:
    result = await session.execute(
        select(ExternalErrorRecord)
        .where(ExternalErrorRecord.incident_id == incident_id)
        .order_by(ExternalErrorRecord.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_external_error_or_404(session: AsyncSession, error_id: UUID) -> ExternalErrorRecord:
    record = await session.get(ExternalErrorRecord, error_id)
    if record is None:
        raise NotFoundError("External error not found")
    return record


async def link_incident_for_step(session: AsyncSession, *, step_id: UUID, incident_id: UUID) -> None:
    result = await session.execute(select(ExternalErrorRecord).where(ExternalErrorRecord.step_id == step_id))
    for record in result.scalars().all():
        record.incident_id = incident_id
    await session.flush()


def artifact_ids_by_type(artifacts: list[Artifact]) -> tuple[UUID | None, UUID | None, UUID | None]:
    request_id = next((item.id for item in artifacts if item.artifact_type in {"outgoing_request", "dry_run_request"}), None)
    response_id = next((item.id for item in artifacts if item.artifact_type == "incoming_response"), None)
    error_id = next((item.id for item in artifacts if item.artifact_type == "external_error"), None)
    return request_id, response_id, error_id
