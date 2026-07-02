from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class StepResultStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"
    WAIT = "wait"
    DRY_RUN = "dry_run"


@dataclass(slots=True)
class ArtifactCreate:
    artifact_type: str
    name: str
    content: dict[str, Any]


@dataclass(slots=True)
class StepResult:
    status: StepResultStatus
    message: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    artifacts: list[ArtifactCreate] = field(default_factory=list)
    variables_update: dict[str, Any] = field(default_factory=dict)
    next_step: str | None = None
    retry_after: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        message: str | None = None,
        *,
        artifacts: list[ArtifactCreate] | None = None,
        variables_update: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StepResult:
        return cls(
            status=StepResultStatus.SUCCESS,
            message=message,
            artifacts=artifacts or [],
            variables_update=variables_update or {},
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        error_code: str,
        error_message: str,
        *,
        artifacts: list[ArtifactCreate] | None = None,
        variables_update: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StepResult:
        return cls(
            status=StepResultStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
            artifacts=artifacts or [],
            variables_update=variables_update or {},
            metadata=metadata or {},
        )

    @classmethod
    def skipped(cls, message: str | None = None, *, artifacts: list[ArtifactCreate] | None = None) -> StepResult:
        return cls(status=StepResultStatus.SKIPPED, message=message, artifacts=artifacts or [])

    @classmethod
    def retry(
        cls,
        message: str,
        *,
        retry_after: datetime | None = None,
        artifacts: list[ArtifactCreate] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StepResult:
        return cls(status=StepResultStatus.RETRY, message=message, retry_after=retry_after, artifacts=artifacts or [], metadata=metadata or {})

    @classmethod
    def wait(
        cls,
        message: str,
        *,
        retry_after: datetime | None = None,
        artifacts: list[ArtifactCreate] | None = None,
    ) -> StepResult:
        return cls(status=StepResultStatus.WAIT, message=message, retry_after=retry_after, artifacts=artifacts or [])

    @classmethod
    def dry_run(
        cls,
        message: str | None = None,
        *,
        artifacts: list[ArtifactCreate] | None = None,
        variables_update: dict[str, Any] | None = None,
    ) -> StepResult:
        return cls(
            status=StepResultStatus.DRY_RUN,
            message=message,
            artifacts=artifacts or [],
            variables_update=variables_update or {},
        )
