from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.artifacts.service import create_artifact
from app.connectors.manager import ConnectorManager
from app.core.enums import ArtifactType, EventStatus, RunMode, RunStatus, StepStatus
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.events.repository import latest_run, next_run_number
from app.execution.context import PipelineContext
from app.execution.exceptions import StepNotFoundError
from app.execution.registry import StepRegistry, registry as default_registry
from app.execution.result import ArtifactCreate, StepResult, StepResultStatus
from app.execution.workflow import DEFAULT_EXECUTION_STEPS, DEFAULT_VALIDATION, normalize_step_configs, step_condition
from app.external_errors import service as external_error_service
from app.workflows import service as workflow_service
from app.workflows.models import Workflow

logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self, session: AsyncSession, step_registry: StepRegistry | None = None) -> None:
        self.session = session
        self.registry = step_registry or default_registry

    async def execute_event(
        self,
        event_id: UUID,
        mode: RunMode = RunMode.NORMAL,
        start_from_step: str | None = None,
        edited_artifact: dict | None = None,
        dry_run: bool = False,
        created_by: str | None = None,
        initial_payload: dict | None = None,
        workflow_id: UUID | None = None,
    ) -> EventRun:
        event = await self.session.get(IntegrationEvent, event_id)
        if event is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("Event not found")
        original_event_status = event.status
        workflow = await workflow_service.select_workflow(
            self.session,
            event_type=event.event_type,
            source_system=event.source_system,
            target_system=event.target_system,
            entity_type=event.entity_type,
            workflow_id=workflow_id,
        )
        parent = await latest_run(self.session, event.id)
        run = EventRun(
            event_id=event.id,
            run_number=await next_run_number(self.session, event.id),
            mode=mode,
            status=RunStatus.CREATED,
            parent_run_id=parent.id if parent else None,
            created_by=created_by,
            workflow_id=workflow.id if workflow else None,
            workflow_name=workflow.name if workflow else "Default execution workflow",
            workflow_version=workflow.version if workflow else 1,
            mapping_versions_json=self._mapping_versions(workflow),
        )
        self.session.add(run)
        await self.session.flush()
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        is_dry_run = dry_run or mode == RunMode.DRY_RUN
        if not is_dry_run:
            event.status = EventStatus.PROCESSING
        await self.session.flush()

        variables = await self._bootstrap_variables(event.id, initial_payload or edited_artifact)
        context = PipelineContext(
            session=self.session,
            event=event,
            run=run,
            current_step=None,
            workflow=workflow,
            mode=mode,
            dry_run=is_dry_run,
            source_system=event.source_system,
            target_system=event.target_system,
            correlation_id=event.correlation_id,
            variables=variables,
            metadata={},
            connector_manager=ConnectorManager(self.session),
            logger=logger,
        )
        if edited_artifact is not None:
            await create_artifact(
                self.session,
                event_id=event.id,
                run_id=run.id,
                step_id=None,
                artifact_type=ArtifactType.RAW_PAYLOAD.value,
                name="edited_raw_payload.json",
                content=edited_artifact,
            )

        configs = self._selected_configs(workflow, start_from_step)
        failed = False
        retry_waiting = False
        failed_step: EventStep | None = None
        failed_result: StepResult | None = None
        executed_failure_steps = False

        try:
            for config in configs:
                condition = step_condition(config)
                if condition == "failure" or (condition == "on_dry_run" and not is_dry_run):
                    continue
                if condition not in {"always", "on_success", "on_dry_run"}:
                    continue
                result, event_step = await self._execute_config(context, config)
                if result.status == StepResultStatus.FAILED:
                    failed = True
                    failed_step = event_step
                    failed_result = result
                    context.metadata["failure_step"] = event_step
                    break
                if result.status in {StepResultStatus.RETRY, StepResultStatus.WAIT}:
                    retry_waiting = True
                    break

            if failed and failed_step is not None and not is_dry_run:
                executed_failure_steps = True
                for config in configs:
                    if step_condition(config) == "failure":
                        await self._execute_config(context, config)

            if retry_waiting:
                run.status = RunStatus.CANCELLED
                event.status = EventStatus.RETRY_WAITING
            elif failed:
                run.status = RunStatus.DRY_RUN_FAILED if is_dry_run else RunStatus.FAILED
                event.status = original_event_status if is_dry_run else EventStatus.FAILED
                if failed_result and failed_step and not executed_failure_steps and not is_dry_run:
                    context.metadata["failure_step"] = failed_step
            else:
                run.status = RunStatus.DRY_RUN_SUCCESS if is_dry_run else RunStatus.SUCCESS
                event.status = original_event_status if is_dry_run else EventStatus.SUCCESS
        finally:
            run.finished_at = datetime.now(timezone.utc)
            await self.session.flush()
        return run

    async def _execute_config(self, context: PipelineContext, config: dict[str, Any]) -> tuple[StepResult, EventStep]:
        step_name = config["name"]
        handler_name = config.get("handler") or step_name
        step = self.registry.get(handler_name)
        step_order = await self._next_step_order(context.run.id)
        event_step = EventStep(
            run_id=context.run.id,
            step_order=step_order,
            step_name=step_name,
            status=StepStatus.RUNNING,
            step_config_json=config,
            condition=step_condition(config),
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(event_step)
        await self.session.flush()
        context.current_step = event_step
        try:
            can_execute = await step.can_execute(context) if hasattr(step, "can_execute") else True
            result = await step.execute(context) if can_execute else StepResult.skipped("Step can_execute returned false")
        except StepNotFoundError:
            raise
        except Exception as exc:
            logger.exception("Execution step %s failed unexpectedly", step_name)
            result = StepResult.failed(
                "UNEXPECTED_PIPELINE_ERROR",
                str(exc) or exc.__class__.__name__,
                artifacts=[
                    ArtifactCreate(
                        ArtifactType.ERROR_DETAILS.value,
                        "unexpected_error_details.json",
                        {
                            "error_code": "UNEXPECTED_PIPELINE_ERROR",
                            "error_message": str(exc) or exc.__class__.__name__,
                            "step_name": step_name,
                        },
                    )
                ],
            )

        if result.status == StepResultStatus.FAILED and not any(a.artifact_type == ArtifactType.ERROR_DETAILS.value for a in result.artifacts):
            result.artifacts.append(
                ArtifactCreate(
                    ArtifactType.ERROR_DETAILS.value,
                    "error_details.json",
                    {
                        "error_code": result.error_code,
                        "error_message": result.error_message,
                        "step_name": step_name,
                    },
                )
            )
        created_artifacts: list[Artifact] = []
        for artifact in result.artifacts:
            created_artifact = await create_artifact(
                self.session,
                event_id=context.event.id,
                run_id=context.run.id,
                step_id=event_step.id,
                artifact_type=artifact.artifact_type,
                name=artifact.name,
                content=artifact.content,
            )
            created_artifacts.append(created_artifact)
        context.variables.update(result.variables_update)
        event_step.status = self._step_status(result.status)
        event_step.error_code = result.error_code
        event_step.error_message = result.error_message
        event_step.finished_at = datetime.now(timezone.utc)
        event_step.duration_ms = _duration_ms(event_step.started_at, event_step.finished_at)
        if result.status == StepResultStatus.FAILED and isinstance(result.metadata.get("external_error"), dict):
            request_id, response_id, error_id = external_error_service.artifact_ids_by_type(created_artifacts)
            external_error = await external_error_service.record_external_error(
                self.session,
                event=context.event,
                run_id=context.run.id,
                step=event_step,
                payload=result.metadata["external_error"],
                request_artifact_id=request_id,
                response_artifact_id=response_id,
                error_artifact_id=error_id,
            )
            result.external_error_record_id = str(external_error.id)
        await self.session.flush()
        return result, event_step

    async def _next_step_order(self, run_id: UUID) -> int:
        result = await self.session.execute(select(EventStep).where(EventStep.run_id == run_id).order_by(EventStep.step_order.desc()).limit(1))
        latest_step = result.scalar_one_or_none()
        return (latest_step.step_order if latest_step else 0) + 1

    async def _bootstrap_variables(self, event_id: UUID, override_payload: dict | None) -> dict[str, Any]:
        variables: dict[str, Any] = {}
        if override_payload is not None:
            variables["raw_payload"] = dict(override_payload)
            variables["payload"] = dict(override_payload)
            return variables
        result = await self.session.execute(
            select(Artifact)
            .where(Artifact.event_id == event_id)
            .where(Artifact.artifact_type.in_([ArtifactType.RAW_PAYLOAD.value, ArtifactType.CANONICAL_PAYLOAD.value, ArtifactType.MAPPED_PAYLOAD.value, ArtifactType.INCOMING_RESPONSE.value]))
            .order_by(Artifact.created_at.asc())
        )
        for artifact in result.scalars().all():
            if artifact.artifact_type == ArtifactType.RAW_PAYLOAD.value:
                variables["raw_payload"] = artifact.content_json
                variables.setdefault("payload", artifact.content_json)
            elif artifact.artifact_type == ArtifactType.CANONICAL_PAYLOAD.value:
                variables["canonical_payload"] = artifact.content_json
                variables["payload"] = artifact.content_json
            elif artifact.artifact_type == ArtifactType.MAPPED_PAYLOAD.value:
                variables["mapped_payload"] = artifact.content_json
            elif artifact.artifact_type == ArtifactType.INCOMING_RESPONSE.value:
                variables["response"] = artifact.content_json
        return variables

    def _selected_configs(self, workflow: Workflow | None, start_from_step: str | None) -> list[dict[str, Any]]:
        configs = normalize_step_configs(workflow.steps_json if workflow else DEFAULT_EXECUTION_STEPS)
        if workflow is None:
            # Keep legacy validation behavior in the default workflow.
            pass
        if start_from_step is None:
            return configs
        names = [config["name"] for config in configs]
        if start_from_step not in names:
            requested_step = self.registry.get(start_from_step)
            for index, config in enumerate(configs):
                if self.registry.get(config["name"]) is requested_step:
                    return configs[index:]
            raise StepNotFoundError(f"Unknown step: {start_from_step}")
        return configs[names.index(start_from_step) :]

    @staticmethod
    def _mapping_versions(workflow: Workflow | None) -> dict[str, Any]:
        if workflow is None:
            return {}
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
    def _step_status(status: StepResultStatus) -> StepStatus:
        if status == StepResultStatus.SUCCESS:
            return StepStatus.SUCCESS
        if status == StepResultStatus.FAILED:
            return StepStatus.FAILED
        if status in {StepResultStatus.RETRY, StepResultStatus.WAIT, StepResultStatus.SKIPPED}:
            return StepStatus.SKIPPED
        if status == StepResultStatus.DRY_RUN:
            return StepStatus.DRY_RUN
        return StepStatus.FAILED


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)
