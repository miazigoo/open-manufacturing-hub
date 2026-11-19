from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import BusinessRuleStatus, EnterpriseQueueStatus, ODataCacheStatus, ResolverType


class QueueMessageCreate(BaseModel):
    event_id: UUID | None = None
    message_id: UUID | None = None
    run_id: UUID | None = None
    flow_id: UUID | None = None
    endpoint_id: UUID | None = None
    route_id: UUID | None = None
    connector_id: UUID | None = None
    workflow_id: UUID | None = None
    business_object: str = Field(min_length=1)
    business_key: str | None = None
    operation: str = Field(min_length=1)
    source_system: str | None = None
    target_system: str | None = None
    connector_name: str | None = None
    current_step: str | None = None
    max_attempts: int = 10
    priority: int = 100
    worker: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    original_payload_json: dict[str, Any] = Field(default_factory=dict)


class QueueMessagePatch(BaseModel):
    status: EnterpriseQueueStatus | None = None
    current_step: str | None = None
    worker: str | None = None
    last_error: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    last_external_error_message: str | None = None
    next_retry_at: datetime | None = None
    priority: int | None = None


class QueueProcessResponse(BaseModel):
    processed: int
    completed: int = 0
    retry_waiting: int = 0
    dlq: int = 0
    failed: int = 0
    items: list["QueueMessageRead"] = []


class QueueEditRetryRequest(BaseModel):
    payload_json: dict[str, Any] = Field(default_factory=dict)


class QueueMessageSummary(BaseModel):
    id: UUID
    event_id: UUID | None
    message_id: UUID | None
    run_id: UUID | None = None
    flow_id: UUID | None = None
    endpoint_id: UUID | None = None
    route_id: UUID | None = None
    connector_id: UUID | None = None
    workflow_id: UUID | None = None
    business_object: str
    business_key: str | None = None
    operation: str
    source_system: str | None = None
    target_system: str | None = None
    connector_name: str | None = None
    current_step: str | None = None
    status: EnterpriseQueueStatus
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None
    priority: int
    worker: str | None = None
    locked_by: str | None = None
    timeline_link: str | None = None
    last_error: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    last_external_error_message: str | None = None
    locked_at: datetime | None = None
    locked_until: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QueueMessageRead(QueueMessageSummary):
    payload_json: dict[str, Any] = Field(default_factory=dict)
    original_payload_json: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class QueuePageResponse(BaseModel):
    items: list[QueueMessageSummary]
    next_cursor: str | None = None
    has_more: bool = False


class DLQItemSummary(BaseModel):
    id: UUID
    queue_message_id: UUID | None = None
    event_id: UUID | None = None
    message_id: UUID | None = None
    business_object: str
    operation: str
    reason: str
    last_error: str | None = None
    attempts: int = 0
    archived: bool
    restored_at: datetime | None = None
    archived_at: datetime | None = None
    timeline_link: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DLQItemRead(DLQItemSummary):
    payload_json: dict[str, Any] = Field(default_factory=dict)
    current_payload_json: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class DLQPageResponse(BaseModel):
    items: list[DLQItemSummary]
    next_cursor: str | None = None
    has_more: bool = False


class QueueAttemptRead(BaseModel):
    id: UUID
    queue_message_id: UUID
    run_id: UUID | None
    attempt_no: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    external_error_record_id: UUID | None
    duration_ms: int | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MonitorSummary(BaseModel):
    waiting: int = 0
    processing: int = 0
    retry_waiting: int = 0
    dlq: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class CanonicalObjectCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema_json")
    active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class CanonicalObjectRead(CanonicalObjectCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResolverCreate(BaseModel):
    name: str = Field(min_length=1)
    resolver_type: ResolverType
    business_object: str
    connector_id: UUID | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    cache_ttl_seconds: int = 3600
    enabled: bool = True


class ResolverRead(ResolverCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ResolveRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    lookup_key: str | None = None
    use_cache: bool = True


class ResolveResponse(BaseModel):
    resolver: str
    cache_status: ODataCacheStatus
    lookup_key: str
    value: dict[str, Any] | None


class TransformApplyRequest(BaseModel):
    name: str
    value: Any = None
    params: dict[str, Any] = Field(default_factory=dict)


class TransformApplyResponse(BaseModel):
    name: str
    result: Any


class BusinessRuleCreate(BaseModel):
    name: str = Field(min_length=1)
    business_object: str | None = None
    operation: str | None = None
    status: BusinessRuleStatus = BusinessRuleStatus.ENABLED
    rules_json: list[dict[str, Any]] = Field(default_factory=list)


class BusinessRuleRead(BusinessRuleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BusinessRuleRunRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class BusinessRuleRunResponse(BaseModel):
    payload: dict[str, Any]
    variables: dict[str, Any]
    trace: list[dict[str, Any]]
    stopped: bool
    failed: str | None


class ODataCacheRead(BaseModel):
    id: UUID
    resolver_name: str
    lookup_key: str
    status: ODataCacheStatus
    value_json: dict[str, Any] | None
    expires_at: datetime | None
    hit_count: int
    last_hit_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ODataCachePreloadRequest(BaseModel):
    resolver_name: str
    lookup_key: str
    value_json: dict[str, Any]
    ttl_seconds: int = 3600
