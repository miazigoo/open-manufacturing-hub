from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import RunMode
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.execution.registry import registry as step_registry
from app.execution.workflow import normalize_step_configs
from app.mappings.service import get_version_by_id_or_404
from app.workflows.models import Workflow
from app.workflows.schemas import DEFAULT_WORKFLOW_STEPS, WorkflowCreate, WorkflowDryRunRequest, WorkflowPatch

CANONICAL_ENTITIES = {
    "Product",
    "Customer",
    "SalesOrder",
    "PurchaseOrder",
    "Shipment",
    "Receipt",
    "StockBalance",
    "Warehouse",
    "WarehouseLocation",
    "InventoryMovement",
}


async def list_workflows(session: AsyncSession) -> list[Workflow]:
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.source_mapping_version), selectinload(Workflow.target_mapping_version))
        .order_by(Workflow.name.asc())
    )
    return list(result.scalars().unique())


async def get_workflow(session: AsyncSession, workflow_id: UUID) -> Workflow | None:
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.source_mapping_version), selectinload(Workflow.target_mapping_version))
        .where(Workflow.id == workflow_id)
    )
    return result.scalar_one_or_none()


async def get_workflow_or_404(session: AsyncSession, workflow_id: UUID) -> Workflow:
    workflow = await get_workflow(session, workflow_id)
    if workflow is None:
        raise NotFoundError("Workflow not found")
    return workflow


async def create_workflow(session: AsyncSession, request: WorkflowCreate) -> Workflow:
    data = request.model_dump()
    await _validate_workflow_payload(session, data)
    workflow = Workflow(**data)
    session.add(workflow)
    await session.flush()
    await session.refresh(workflow, ["source_mapping_version", "target_mapping_version"])
    return workflow


async def patch_workflow(session: AsyncSession, workflow_id: UUID, request: WorkflowPatch) -> Workflow:
    workflow = await get_workflow_or_404(session, workflow_id)
    data = request.model_dump(exclude_unset=True)
    merged = {
        "steps_json": workflow.steps_json,
        "validation_json": workflow.validation_json,
        "source_mapping_version_id": workflow.source_mapping_version_id,
        "target_mapping_version_id": workflow.target_mapping_version_id,
        "entity_type": workflow.entity_type,
        **data,
    }
    await _validate_workflow_payload(session, merged)
    for key, value in data.items():
        setattr(workflow, key, value)
    await session.flush()
    await session.refresh(workflow, ["source_mapping_version", "target_mapping_version"])
    return workflow


async def set_enabled(session: AsyncSession, workflow_id: UUID, enabled: bool) -> Workflow:
    workflow = await get_workflow_or_404(session, workflow_id)
    workflow.enabled = enabled
    await session.flush()
    return workflow


async def select_workflow(
    session: AsyncSession,
    *,
    event_type: str,
    source_system: str | None,
    target_system: str | None,
    entity_type: str | None,
    workflow_id: UUID | None = None,
) -> Workflow | None:
    if workflow_id is not None:
        workflow = await get_workflow_or_404(session, workflow_id)
        if not workflow.enabled:
            raise BadRequestError("Workflow is disabled")
        return workflow
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.source_mapping_version), selectinload(Workflow.target_mapping_version))
        .where(Workflow.enabled.is_(True), or_(Workflow.event_type == event_type, Workflow.event_type.is_(None)))
    )
    candidates = list(result.scalars().unique())
    candidates = [
        workflow
        for workflow in candidates
        if _matches(workflow.source_system, source_system)
        and _matches(workflow.target_system, target_system)
        and _matches(workflow.entity_type, entity_type)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda workflow: _score(workflow, event_type, source_system, target_system, entity_type), reverse=True)
    return candidates[0]


async def dry_run_workflow(session: AsyncSession, workflow_id: UUID, request: WorkflowDryRunRequest) -> tuple[Workflow, EventRun]:
    workflow = await get_workflow_or_404(session, workflow_id)
    if not workflow.enabled:
        raise BadRequestError("Workflow is disabled")
    event = IntegrationEvent(
        correlation_id=None,
        source_system=request.source_system or workflow.source_system or "Workflow Test",
        target_system=request.target_system or workflow.target_system,
        event_type=workflow.event_type or "WorkflowTest",
        entity_type=request.entity_type or workflow.entity_type,
        entity_id=None,
    )
    session.add(event)
    await session.flush()
    from app.execution.engine import ExecutionEngine

    run = await ExecutionEngine(session).execute_event(
        event.id,
        mode=RunMode.DRY_RUN,
        dry_run=True,
        initial_payload=request.payload,
        workflow_id=workflow.id,
    )
    loaded_run = await _load_run(session, run.id)
    return workflow, loaded_run


async def validate_workflow(session: AsyncSession, workflow_id: UUID) -> dict:
    workflow = await get_workflow_or_404(session, workflow_id)
    errors: list[dict] = []
    try:
        steps = normalize_step_configs(workflow.steps_json)
    except ValueError as exc:
        return {"valid": False, "errors": [{"step": None, "message": str(exc)}]}
    from app.connectors.repository import get_by_name
    from app.integration_bus.repository import get_lookup_template_by_name
    from app.operation_templates.repository import get_by_name as get_operation_by_name

    for step in steps:
        name = step["name"]
        handler = step.get("handler") or name
        try:
            step_registry.get(handler)
        except Exception:
            errors.append({"step": name, "message": f"Unknown workflow step: {handler}"})
            continue
        condition = step.get("on", "always")
        if condition not in {"always", "on_success", "failure", "on_failure", "on_dry_run"}:
            errors.append({"step": name, "message": f"Unsupported workflow condition: {condition}"})
        config = step.get("config") or {}
        if name == "odata_lookup":
            if config.get("template") and await get_lookup_template_by_name(session, str(config["template"])) is None:
                errors.append({"step": name, "message": f"Lookup template not found: {config['template']}"})
            if config.get("connector") and await get_by_name(session, str(config["connector"])) is None:
                errors.append({"step": name, "message": f"Connector not found: {config['connector']}"})
            if not config.get("template") and not config.get("resource"):
                errors.append({"step": name, "message": "OData lookup requires template or resource"})
        if name in {"call_connector", "call_print_operation"} and config.get("operation_template"):
            if await get_operation_by_name(session, str(config["operation_template"])) is None:
                errors.append({"step": name, "message": f"Operation template not found: {config['operation_template']}"})
    return {"valid": not errors, "errors": errors}


async def _validate_workflow_payload(session: AsyncSession, data: dict) -> None:
    try:
        steps = normalize_step_configs(data.get("steps_json") or DEFAULT_WORKFLOW_STEPS)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    for step in steps:
        try:
            step_registry.get(step.get("handler") or step["name"])
        except Exception as exc:
            raise BadRequestError(f"Unknown workflow step: {step.get('handler') or step['name']}") from exc
        condition = step.get("on", "always")
        if condition not in {"always", "on_success", "failure", "on_failure", "on_dry_run"}:
            raise BadRequestError(f"Unsupported workflow condition: {condition}")
        if condition == "on_failure":
            step["on"] = "failure"
    entity_type = data.get("entity_type")
    if entity_type is not None and entity_type not in CANONICAL_ENTITIES:
        raise BadRequestError(f"Unsupported canonical entity: {entity_type}")
    if data.get("source_mapping_version_id") is not None:
        await get_version_by_id_or_404(session, data["source_mapping_version_id"])
    if data.get("target_mapping_version_id") is not None:
        await get_version_by_id_or_404(session, data["target_mapping_version_id"])


def _matches(configured: str | None, actual: str | None) -> bool:
    return configured is None or configured == actual


def _score(workflow: Workflow, event_type: str, source_system: str | None, target_system: str | None, entity_type: str | None) -> int:
    return sum(
        [
            8 if workflow.event_type == event_type else 0,
            4 if workflow.source_system == source_system and source_system is not None else 0,
            4 if workflow.target_system == target_system and target_system is not None else 0,
            2 if workflow.entity_type == entity_type and entity_type is not None else 0,
            1 if workflow.source_mapping_version_id is not None else 0,
            1 if workflow.target_mapping_version_id is not None else 0,
        ]
    )


async def _load_run(session: AsyncSession, run_id: UUID) -> EventRun:
    result = await session.execute(
        select(EventRun)
        .options(selectinload(EventRun.steps).selectinload(EventStep.artifacts), selectinload(EventRun.artifacts))
        .where(EventRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise NotFoundError("Run not found")
    run.steps.sort(key=lambda step: step.step_order)
    return run
