from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OneCScenarioPresetRead(BaseModel):
    key: str
    name: str
    description: str
    source_resource: str
    event_type: str
    entity_type: str
    mappings: list[str]


class OneCScenarioInstallRead(BaseModel):
    scenario: str
    source_connector_id: UUID
    target_connector_id: UUID
    workflow_id: UUID
    polling_job_id: UUID | None
    mappings: list[str]
    notes: list[str]

    model_config = ConfigDict(from_attributes=True)


class ShipmentFactTestRequest(BaseModel):
    order_id: str = "1532"
    shipment_id: str = "WMS-SHIP-1532"
    status: str = "shipped"
    warehouse_id: str = "MAIN"
    items: list[dict[str, Any]] = Field(default_factory=lambda: [{"sku": "ABC123", "qty": 5}])


class StockBalanceTestRequest(BaseModel):
    warehouse_id: str = "MAIN"
    occurred_at: str = "2026-07-03T09:00:00Z"
    items: list[dict[str, Any]] = Field(default_factory=lambda: [{"sku": "ABC123", "qty": 12, "uom": "pcs", "batch": "B-001"}])


class InventoryResultTestRequest(BaseModel):
    inventory_id: str = "INV-1001"
    warehouse_id: str = "MAIN"
    completed_at: str = "2026-07-03T10:00:00Z"
    items: list[dict[str, Any]] = Field(default_factory=lambda: [{"sku": "ABC123", "expected_qty": 10, "actual_qty": 9, "uom": "pcs"}])


class ShipmentFactTestRead(BaseModel):
    event_id: UUID
    status: str
    timeline_url: str
