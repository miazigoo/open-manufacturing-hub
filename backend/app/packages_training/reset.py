from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.connectors.models import ConnectorInstance
from app.events.models import IntegrationEvent
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute
from app.integration_flows.models import IntegrationFlow
from app.operation_templates.models import OperationTemplate
from app.polling.models import PollingJob
from app.test_console.models import SavedTestCase
from app.workflows.models import Workflow


async def reset_training_data(session: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    counts["test_cases"] = await _delete_by_name_prefix(session, SavedTestCase, "Training ")
    counts["flow_test_cases"] = await _delete_by_name_prefix(session, SavedTestCase, "Flow Training ")
    counts["flows"] = await _delete_by_name_prefix(session, IntegrationFlow, "Training ")
    counts["polling_jobs"] = await _delete_by_name_prefix(session, PollingJob, "Training ")
    counts["endpoints"] = await _delete_by_slug_prefix(session, IntegrationEndpoint, "training-")
    counts["routes"] = await _delete_by_name_prefix(session, IntegrationRoute, "Flow Training ")
    counts["workflows"] = await _delete_by_name_prefix(session, Workflow, "Flow Training ")
    counts["operations"] = await _delete_by_name_prefix(session, OperationTemplate, "Flow Training ")
    counts["connectors"] = await _delete_by_name_prefix(session, ConnectorInstance, "Training ")
    events_result = await session.execute(select(IntegrationEvent).where(IntegrationEvent.event_type.like("Flow.training-%")))
    events = events_result.scalars().all()
    counts["events"] = len(events)
    event_ids = [event.id for event in events]
    if event_ids:
        await session.execute(delete(Artifact).where(Artifact.event_id.in_(event_ids)))
    for event in events:
        await session.delete(event)
    await session.flush()
    return counts


async def _delete_by_name_prefix(session: AsyncSession, model, prefix: str) -> int:
    result = await session.execute(select(model).where(model.name.like(f"{prefix}%")))
    rows = result.scalars().all()
    for row in rows:
        await session.delete(row)
    await session.flush()
    return len(rows)


async def _delete_by_slug_prefix(session: AsyncSession, model, prefix: str) -> int:
    result = await session.execute(select(model).where(model.slug.like(f"{prefix}%")))
    rows = result.scalars().all()
    for row in rows:
        await session.delete(row)
    await session.flush()
    return len(rows)
