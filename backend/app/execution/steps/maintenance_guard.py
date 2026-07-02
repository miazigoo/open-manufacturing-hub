from app.connectors.repository import get_by_name
from app.core.enums import ConnectorInstanceStatus
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.maintenance.service import active_target_maintenance


class MaintenanceGuardStep:
    name = "maintenance_guard"
    display_name = "Maintenance Guard"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        if context.dry_run:
            return StepResult.success("Maintenance guard skipped for dry-run")
        maintenance = await active_target_maintenance(context.session, context.target_system)
        if maintenance is not None:
            retry_after = maintenance.ends_at
            content = {
                "reason": maintenance.reason or f"{maintenance.component_name} maintenance",
                "component_name": maintenance.component_name,
                "retry_after": retry_after.isoformat(),
            }
            return StepResult.retry(
                content["reason"],
                retry_after=retry_after,
                artifacts=[ArtifactCreate("maintenance", "maintenance.json", content)],
            )
        if context.target_system:
            connector = await get_by_name(context.session, context.target_system)
            if connector is not None and connector.status == ConnectorInstanceStatus.MAINTENANCE:
                content = {"reason": f"{connector.name} connector maintenance", "component_name": connector.name}
                return StepResult.retry(
                    content["reason"],
                    artifacts=[ArtifactCreate("maintenance", "connector_maintenance.json", content)],
                )
        return StepResult.success("No active maintenance")
