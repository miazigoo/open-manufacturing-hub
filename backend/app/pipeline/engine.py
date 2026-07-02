import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.service import create_artifact
from app.connectors.manager import ConnectorManager
from app.core.enums import ArtifactType, ConnectorInstanceStatus, EventStatus, RunMode, RunStatus, StepStatus
from app.core.errors import BadRequestError, PipelineError
from app.sdk.exceptions import ConnectorNotFoundError
from app.sdk.types import ConnectorContext
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.maintenance.service import active_target_maintenance
from app.mappings.engine import MappingEngine, get_path
from app.pipeline.context import PipelineContext
from app.pipeline import steps
from app.workflows import service as workflow_service
from app.workflows.models import Workflow

logger = logging.getLogger(__name__)


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)


class PipelineEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, event: IntegrationEvent, run: EventRun, context: PipelineContext) -> EventRun:
        original_event_status = event.status
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        workflow = await workflow_service.select_workflow(
            self.session,
            event_type=event.event_type,
            source_system=event.source_system,
            target_system=event.target_system,
            entity_type=event.entity_type,
            workflow_id=context.workflow_id,
        )
        if workflow is not None:
            run.workflow_id = workflow.id
            run.workflow_name = workflow.name
            run.workflow_version = workflow.version
            run.mapping_versions_json = self._mapping_versions(workflow)
        if context.mode != RunMode.DRY_RUN:
            event.status = EventStatus.PROCESSING
        await self.session.flush()

        step_names = self._selected_steps(context.start_from_step, workflow.steps_json if workflow else steps.STEP_NAMES)
        current_payload = dict(context.payload)
        mapped_payload: dict[str, Any] | None = None
        response: dict[str, Any] | None = None
        mapping_engine = MappingEngine()

        step: EventStep | None = None
        try:
            for index, step_name in enumerate(step_names, start=1):
                step = EventStep(run_id=run.id, step_order=index, step_name=step_name, status=StepStatus.RUNNING)
                step.started_at = datetime.now(timezone.utc)
                self.session.add(step)
                await self.session.flush()

                if step_name == "receive":
                    current_payload = steps.receive(current_payload)
                    await create_artifact(
                        self.session,
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        artifact_type=ArtifactType.RAW_PAYLOAD.value,
                        name="raw_payload.json",
                        content=current_payload,
                    )
                elif step_name in {"normalize", "map_to_canonical"}:
                    try:
                        if workflow and workflow.source_mapping_version is not None:
                            current_payload = mapping_engine.apply(current_payload, workflow.source_mapping_version.rules_json)
                        else:
                            current_payload = steps.normalize(current_payload)
                    except BadRequestError as exc:
                        raise PipelineError("MAPPING_FAILED", str(exc)) from exc
                    await create_artifact(
                        self.session,
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        artifact_type=ArtifactType.CANONICAL_PAYLOAD.value,
                        name="canonical_payload.json",
                        content=current_payload,
                    )
                elif step_name == "validate":
                    result = self._validate_payload(current_payload, workflow)
                    await create_artifact(
                        self.session,
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        artifact_type=ArtifactType.VALIDATION_RESULT.value,
                        name="validation_result.json",
                        content=result,
                    )
                    if not result["valid"]:
                        raise PipelineError("VALIDATION_FAILED", f"Missing fields: {', '.join(result['missing'])}")
                elif step_name == "map_to_target":
                    try:
                        if workflow and workflow.target_mapping_version is not None:
                            mapped_payload = mapping_engine.apply(current_payload, workflow.target_mapping_version.rules_json)
                        else:
                            mapped_payload = steps.map_to_target(current_payload)
                    except BadRequestError as exc:
                        raise PipelineError("MAPPING_FAILED", str(exc)) from exc
                    await create_artifact(
                        self.session,
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        artifact_type=ArtifactType.MAPPED_PAYLOAD.value,
                        name="mapped_payload.json",
                        content=mapped_payload,
                    )
                elif step_name == "send_to_target":
                    maintenance = await active_target_maintenance(self.session, event.target_system)
                    if maintenance and context.mode != RunMode.DRY_RUN:
                        await create_artifact(
                            self.session,
                            event_id=event.id,
                            run_id=run.id,
                            step_id=step.id,
                            artifact_type="maintenance",
                            name="maintenance.json",
                            content={
                                "reason": maintenance.reason or f"{maintenance.component_name} maintenance",
                                "component_name": maintenance.component_name,
                                "retry_after": maintenance.ends_at.isoformat(),
                            },
                        )
                        step.status = StepStatus.SKIPPED
                        step.finished_at = datetime.now(timezone.utc)
                        step.duration_ms = _duration_ms(step.started_at, step.finished_at)
                        run.status = RunStatus.CANCELLED
                        event.status = EventStatus.RETRY_WAITING
                        break
                    manager = ConnectorManager(self.session)
                    try:
                        connector_instance = await manager.get_target_instance(event.target_system)
                    except ConnectorNotFoundError as exc:
                        raise PipelineError("CONNECTOR_NOT_FOUND", str(exc)) from exc
                    if connector_instance.status == ConnectorInstanceStatus.MAINTENANCE:
                        await create_artifact(
                            self.session,
                            event_id=event.id,
                            run_id=run.id,
                            step_id=step.id,
                            artifact_type="maintenance",
                            name="connector_maintenance.json",
                            content={"reason": f"{connector_instance.name} connector maintenance", "component_name": connector_instance.name},
                        )
                        step.status = StepStatus.SKIPPED
                        step.finished_at = datetime.now(timezone.utc)
                        step.duration_ms = _duration_ms(step.started_at, step.finished_at)
                        run.status = RunStatus.CANCELLED
                        event.status = EventStatus.RETRY_WAITING
                        break
                    try:
                        outgoing_payload = mapped_payload or self._map_to_target(current_payload, workflow, mapping_engine)
                    except BadRequestError as exc:
                        raise PipelineError("MAPPING_FAILED", str(exc)) from exc
                    connector_context = ConnectorContext(
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        correlation_id=event.correlation_id,
                        source_system=event.source_system,
                        target_system=event.target_system,
                        dry_run=context.mode == RunMode.DRY_RUN,
                        metadata={"step_name": step.step_name},
                    )
                    try:
                        result = await manager.send_to_target(event.target_system, outgoing_payload, connector_context)
                    except ConnectorNotFoundError as exc:
                        raise PipelineError("CONNECTOR_NOT_FOUND", str(exc)) from exc

                    artifact_type = ArtifactType.DRY_RUN_REQUEST if context.mode == RunMode.DRY_RUN else ArtifactType.OUTGOING_REQUEST
                    await create_artifact(
                        self.session,
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        artifact_type=artifact_type.value,
                        name=f"{artifact_type.value}.json",
                        content=result.request_payload or {"payload": outgoing_payload, "connector": event.target_system},
                    )
                    if result.response_payload is not None:
                        await create_artifact(
                            self.session,
                            event_id=event.id,
                            run_id=run.id,
                            step_id=step.id,
                            artifact_type=ArtifactType.INCOMING_RESPONSE.value,
                            name="incoming_response.json",
                            content=result.response_payload,
                        )
                    if not result.success:
                        raise PipelineError(result.error_code or "CONNECTOR_SEND_FAILED", result.error_message or "Connector send failed")
                    if context.mode == RunMode.DRY_RUN:
                        step.status = StepStatus.DRY_RUN
                        step.finished_at = datetime.now(timezone.utc)
                        step.duration_ms = _duration_ms(step.started_at, step.finished_at)
                        continue
                    response = {"status_code": result.status_code, "body": result.response_payload or {}}
                elif step_name == "handle_response":
                    handled = steps.handle_response(response or {"status_code": 204})
                    await create_artifact(
                        self.session,
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        artifact_type=ArtifactType.INCOMING_RESPONSE.value,
                        name="handled_response.json",
                        content=handled,
                    )

                if step.status == StepStatus.RUNNING:
                    step.status = StepStatus.SUCCESS
                step.finished_at = datetime.now(timezone.utc)
                step.duration_ms = _duration_ms(step.started_at, step.finished_at)
                await self.session.flush()

            if event.status != EventStatus.RETRY_WAITING:
                run.status = RunStatus.DRY_RUN_SUCCESS if context.mode == RunMode.DRY_RUN else RunStatus.SUCCESS
                event.status = original_event_status if context.mode == RunMode.DRY_RUN else EventStatus.SUCCESS
        except PipelineError as exc:
            step.status = StepStatus.FAILED
            step.error_code = exc.code
            step.error_message = exc.message
            step.finished_at = datetime.now(timezone.utc)
            step.duration_ms = _duration_ms(step.started_at, step.finished_at)
            await create_artifact(
                self.session,
                event_id=event.id,
                run_id=run.id,
                step_id=step.id,
                artifact_type=ArtifactType.ERROR_DETAILS.value,
                name="error_details.json",
                content={"error_code": exc.code, "error_message": exc.message, "step_name": step.step_name},
            )
            run.status = RunStatus.DRY_RUN_FAILED if context.mode == RunMode.DRY_RUN else RunStatus.FAILED
            event.status = original_event_status if context.mode == RunMode.DRY_RUN else EventStatus.FAILED
            if context.mode != RunMode.DRY_RUN:
                from app.incidents.service import safe_record_failure

                await safe_record_failure(self.session, event, run, step)
        except Exception as exc:
            logger.exception("Unexpected pipeline failure")
            if step is not None:
                step.status = StepStatus.FAILED
                step.error_code = "UNEXPECTED_PIPELINE_ERROR"
                step.error_message = str(exc) or exc.__class__.__name__
                step.finished_at = datetime.now(timezone.utc)
                step.duration_ms = _duration_ms(step.started_at, step.finished_at)
                await create_artifact(
                    self.session,
                    event_id=event.id,
                    run_id=run.id,
                    step_id=step.id,
                    artifact_type=ArtifactType.ERROR_DETAILS.value,
                    name="unexpected_error_details.json",
                    content={
                        "error_code": "UNEXPECTED_PIPELINE_ERROR",
                        "error_message": step.error_message,
                        "step_name": step.step_name,
                    },
                )
                if context.mode != RunMode.DRY_RUN:
                    from app.incidents.service import safe_record_failure

                    await safe_record_failure(self.session, event, run, step)
            run.status = RunStatus.DRY_RUN_FAILED if context.mode == RunMode.DRY_RUN else RunStatus.FAILED
            event.status = original_event_status if context.mode == RunMode.DRY_RUN else EventStatus.FAILED
        finally:
            run.finished_at = datetime.now(timezone.utc)
            await self.session.flush()

        return run

    @staticmethod
    def _selected_steps(start_from_step: str | None, configured_steps: list[str]) -> list[str]:
        if start_from_step is None:
            return configured_steps
        if start_from_step not in configured_steps:
            raise PipelineError("UNKNOWN_STEP", f"Unknown step: {start_from_step}")
        return configured_steps[configured_steps.index(start_from_step) :]

    @staticmethod
    def _mapping_versions(workflow: Workflow) -> dict[str, Any]:
        versions: dict[str, Any] = {}
        if workflow.source_mapping_version is not None:
            versions["source"] = {
                "mapping_id": str(workflow.source_mapping_version.mapping_id),
                "version_id": str(workflow.source_mapping_version.id),
                "version": workflow.source_mapping_version.version,
            }
        if workflow.target_mapping_version is not None:
            versions["target"] = {
                "mapping_id": str(workflow.target_mapping_version.mapping_id),
                "version_id": str(workflow.target_mapping_version.id),
                "version": workflow.target_mapping_version.version,
            }
        return versions

    @staticmethod
    def _validate_payload(payload: dict[str, Any], workflow: Workflow | None) -> dict[str, Any]:
        if workflow is None:
            return steps.validate(payload)
        required = workflow.validation_json.get("required_fields", [])
        missing = [path for path in required if get_path(payload, path) in (None, "")]
        return {"valid": not missing, "missing": missing}

    @staticmethod
    def _map_to_target(payload: dict[str, Any], workflow: Workflow | None, mapping_engine: MappingEngine) -> dict[str, Any]:
        if workflow and workflow.target_mapping_version is not None:
            return mapping_engine.apply(payload, workflow.target_mapping_version.rules_json)
        return steps.map_to_target(payload)
