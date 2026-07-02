from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import HealthComponentType, HealthStatus


class SiteCreate(BaseModel):
    name: str
    code: str
    description: str | None = None


class HealthCheckCreate(BaseModel):
    component_type: HealthComponentType
    component_name: str
    site_code: str | None = None
    status: HealthStatus
    details_json: dict[str, Any] | None = None


class HealthCheckRead(BaseModel):
    id: UUID
    component_type: HealthComponentType
    component_name: str
    site_id: UUID | None
    status: HealthStatus
    details_json: dict[str, Any] | None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentHeartbeatCreate(BaseModel):
    site_name: str
    site_code: str
    agent_name: str
    internet_ok: bool | None = None
    can_reach_hub: bool | None = None
    can_reach_wms: bool | None = None
    can_reach_erp: bool | None = None
    local_ip: str | None = None
    details_json: dict[str, Any] | None = None


class AgentHeartbeatRead(BaseModel):
    id: UUID
    site_id: UUID
    agent_name: str
    internet_ok: bool | None
    can_reach_hub: bool | None
    can_reach_wms: bool | None
    can_reach_erp: bool | None
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)
