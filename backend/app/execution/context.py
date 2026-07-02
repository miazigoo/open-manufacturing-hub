from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.manager import ConnectorManager
from app.core.enums import RunMode
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.workflows.models import Workflow


@dataclass(slots=True)
class PipelineContext:
    session: AsyncSession
    event: IntegrationEvent
    run: EventRun
    current_step: EventStep | None
    workflow: Workflow | None
    mode: RunMode
    dry_run: bool
    source_system: str | None
    target_system: str | None
    correlation_id: str | None
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    artifact_service: Any | None = None
    connector_manager: ConnectorManager | None = None
    incident_service: Any | None = None
    notification_service: Any | None = None
    maintenance_service: Any | None = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("app.execution"))

    def debug_snapshot(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event.id),
            "run_id": str(self.run.id),
            "current_step": self.current_step.step_name if self.current_step else None,
            "workflow": self.workflow.name if self.workflow else None,
            "mode": self.mode.value,
            "dry_run": self.dry_run,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "correlation_id": self.correlation_id,
            "variables": sorted(self.variables.keys()),
            "metadata": self.metadata,
        }
