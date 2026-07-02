from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MaintenanceWindowCreate(BaseModel):
    component_type: str
    component_name: str
    reason: str | None = None
    starts_at: datetime
    ends_at: datetime
    enabled: bool = True


class MaintenanceWindowPatch(BaseModel):
    reason: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    enabled: bool | None = None


class MaintenanceWindowRead(BaseModel):
    id: UUID
    component_type: str
    component_name: str
    reason: str | None
    starts_at: datetime
    ends_at: datetime
    enabled: bool

    model_config = ConfigDict(from_attributes=True)
