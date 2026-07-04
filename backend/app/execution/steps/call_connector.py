from app.connectors.manager import ConnectorManager
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.external_errors.normalizers import external_error_artifact, external_error_payload_from_result
from app.sdk.exceptions import ConnectorNotFoundError
from app.sdk.types import ConnectorContext


class CallConnectorStep:
    name = "call_connector"
    display_name = "Call Connector"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        manager = context.connector_manager or ConnectorManager(context.session)
        payload = dict(context.variables.get("mapped_payload") or {})
        if not payload:
            payload = dict(context.variables.get("canonical_payload") or context.variables.get("payload") or {})
        connector_context = ConnectorContext(
            event_id=context.event.id,
            run_id=context.run.id,
            step_id=context.current_step.id if context.current_step else None,
            correlation_id=context.correlation_id,
            source_system=context.source_system,
            target_system=context.target_system,
            dry_run=context.dry_run,
            metadata={
                "step_name": self.name,
                "event_type": context.event.event_type,
                "entity_type": context.event.entity_type,
                "entity_id": context.event.entity_id,
            },
        )
        try:
            result = await manager.send_to_target(context.target_system, payload, connector_context)
        except ConnectorNotFoundError as exc:
            return StepResult.failed("CONNECTOR_NOT_FOUND", str(exc))
        request_type = ArtifactType.DRY_RUN_REQUEST if context.dry_run else ArtifactType.OUTGOING_REQUEST
        artifacts = [
            ArtifactCreate(
                request_type.value,
                f"{request_type.value}.json",
                result.request_payload or {"payload": payload, "connector": context.target_system},
            )
        ]
        if result.response_payload is not None:
            artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", result.response_payload))
        variables = {"connector_result": result, "response": {"status_code": result.status_code, "body": result.response_payload or {}}}
        if not result.success:
            external_error = external_error_payload_from_result(
                result,
                source_system=context.source_system,
                target_system=context.target_system,
                connector_type=getattr(result, "connector_type", None),
                connector_name=getattr(result, "connector_name", None) or context.target_system,
            )
            artifacts.append(ArtifactCreate(ArtifactType.EXTERNAL_ERROR.value, "external_error.json", external_error_artifact(external_error)))
            return StepResult.failed(
                result.error_code or "CONNECTOR_SEND_FAILED",
                result.error_message or "Connector send failed",
                artifacts=artifacts,
                variables_update=variables,
                metadata={"external_error": external_error},
                human_title=external_error.get("human_title"),
                human_summary=external_error.get("human_summary"),
                developer_message=external_error.get("developer_message"),
                hint=external_error.get("hint"),
            )
        if context.dry_run:
            return StepResult.dry_run("Connector dry-run complete", artifacts=artifacts, variables_update=variables)
        return StepResult.success("Connector call complete", artifacts=artifacts, variables_update=variables)
