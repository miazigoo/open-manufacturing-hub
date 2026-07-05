from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.events import service as events_service
from app.events.schemas import EventCreate
from app.onboarding import repository
from app.onboarding.models import OnboardingState
from app.onboarding.schemas import OnboardingExampleRunResponse, OnboardingStateRead, OnboardingStateResponse

CHECKLIST: list[dict[str, str | None]] = [
    {"key": "install_onec_package", "title": "Install required packages", "description": "Install and enable the 1C package before building 1C routes.", "route": "/plugin-store", "docs_url": "/docs/packages/packages/plugin-store"},
    {"key": "create_first_onec_connector", "title": "Create 1C connector", "description": "Register OData and HTTP-service URLs for your first 1C database.", "route": "/connectors", "docs_url": "/docs/onec/tools/connector"},
    {"key": "test_onec_connection", "title": "Test OData connection", "description": "Open OData Explorer, load resources and run a safe query.", "route": "/odata-explorer", "docs_url": "/docs/onec/tools/odata-explorer"},
    {"key": "create_first_integration_flow", "title": "Create first integration flow", "description": "Build the first route: 1C POST -> OData lookup -> JSON -> endpoint.", "route": "/onboarding/first-integration", "docs_url": "/docs/onec/tools/visual-flow-builder"},
    {"key": "run_first_test_case", "title": "Run test request", "description": "Send a known payload through Test Console and inspect the response.", "route": "/test-console", "docs_url": "/docs/onec/scenarios/onec-post-two-odata-json-endpoint"},
    {"key": "open_first_timeline", "title": "Open timeline", "description": "Check artifacts, steps and external errors for the test request.", "route": "/events", "docs_url": "/docs/core/start/overview"},
    {"key": "configure_backup", "title": "Configure backup", "description": "Export production configuration before real integrations go live.", "route": "/production", "docs_url": "/docs/core/start/concepts"},
    {"key": "enable_auth_or_skip", "title": "Configure auth if needed", "description": "Install Auth package when UI access must be restricted to named users.", "route": "/auth-settings", "docs_url": "/docs/auth/auth/install"},
    {"key": "create_first_secret", "title": "Create first secret", "description": "Move passwords and tokens out of connector JSON.", "route": "/secrets", "docs_url": "/docs/secrets/secrets/overview"},
]
CHECKLIST_BY_KEY = {item["key"]: item for item in CHECKLIST}

EXAMPLES: dict[str, dict[str, Any]] = {
    "onec_odata_lookup": {
        "message": "OData lookup example event created.",
        "event": EventCreate(source_system="Onboarding", target_system="1C OData", event_type="OnboardingODataLookupExample", entity_type="Contractor", entity_id="1234567890", payload={"order_id": "ONB-ODATA-1", "warehouse_id": "MAIN", "items": [{"sku": "DEMO", "qty": 1}], "inn": "1234567890", "resource": "Catalog_Контрагенты"}),
    },
    "onec_post_to_api": {
        "message": "1C POST to API example event created.",
        "event": EventCreate(source_system="1C ERP", target_system="Website API", event_type="OnboardingOneCPostToApiExample", entity_type="SalesOrder", entity_id="SO-ONB-1001", payload={"order_id": "SO-ONB-1001", "warehouse_id": "MAIN", "items": [{"sku": "ABC-123", "qty": 2}], "pool_type": "DNP"}),
    },
    "xml_raw_bridge": {
        "message": "XML raw bridge example event created.",
        "event": EventCreate(source_system="1C UPD", target_system="1C ERP", event_type="OneCXmlReceived", entity_type="UPD", entity_id="UPD-ONB-1", payload={"order_id": "UPD-ONB-1", "warehouse_id": "MAIN", "items": [{"sku": "XML", "qty": 1}], "raw_xml": "<Документ><Номер>UPD-ONB-1</Номер></Документ>"}),
    },
    "printer_print_batch": {
        "message": "Printer batch example event created.",
        "event": EventCreate(source_system="1C ERP", target_system="ZPL Printer", event_type="OnboardingPrinterExample", entity_type="PrintJob", entity_id="PRINT-ONB-1", payload={"order_id": "PRINT-ONB-1", "warehouse_id": "MAIN", "items": [{"sku": "LABEL", "qty": 1}], "zpl": "^XA^FO50,50^ADN,36,20^FDOMH DEMO^FS^XZ"}),
    },
}


async def state(session: AsyncSession) -> OnboardingStateResponse:
    persisted = {item.key: item for item in await repository.list_states(session)}
    rows = [_read_item(definition, persisted.get(str(definition["key"]))) for definition in CHECKLIST]
    completed_count = sum(1 for item in rows if item.completed or item.skipped)
    return OnboardingStateResponse(items=rows, completed_count=completed_count, total_count=len(rows), setup_done=completed_count == len(rows))


async def complete(session: AsyncSession, key: str, metadata: dict[str, Any] | None = None) -> OnboardingStateRead:
    _ensure_key(key)
    row = await _get_or_create(session, key)
    row.completed = True
    row.completed_at = datetime.now(timezone.utc)
    row.skipped = False
    row.skipped_at = None
    row.metadata_json = {**(row.metadata_json or {}), **(metadata or {})}
    await session.flush()
    return _read_item(CHECKLIST_BY_KEY[key], row)


async def skip(session: AsyncSession, key: str, metadata: dict[str, Any] | None = None) -> OnboardingStateRead:
    _ensure_key(key)
    row = await _get_or_create(session, key)
    row.skipped = True
    row.skipped_at = datetime.now(timezone.utc)
    row.completed = False
    row.completed_at = None
    row.metadata_json = {**(row.metadata_json or {}), **(metadata or {})}
    await session.flush()
    return _read_item(CHECKLIST_BY_KEY[key], row)


async def reset(session: AsyncSession, key: str | None = None) -> OnboardingStateResponse:
    if key:
        _ensure_key(key)
        row = await repository.get_state(session, key)
        if row:
            await session.delete(row)
    else:
        for row in await repository.list_states(session):
            await session.delete(row)
    await session.flush()
    return await state(session)


async def run_example(session: AsyncSession, example_id: str) -> OnboardingExampleRunResponse:
    example = EXAMPLES.get(example_id)
    if example is None:
        raise BadRequestError(f"Unknown onboarding example: {example_id}")
    event = await events_service.create_event(session, example["event"])
    await complete(session, "run_first_test_case", {"example_id": example_id, "event_id": str(event.id)})
    return OnboardingExampleRunResponse(success=True, example_id=example_id, event_id=event.id, timeline_url=f"/events/{event.id}", message=example["message"])


async def _get_or_create(session: AsyncSession, key: str) -> OnboardingState:
    row = await repository.get_state(session, key)
    if row is not None:
        return row
    row = OnboardingState(key=key, metadata_json={})
    session.add(row)
    await session.flush()
    return row


def _read_item(definition: dict[str, str | None], row: OnboardingState | None) -> OnboardingStateRead:
    return OnboardingStateRead(
        id=row.id if row else None,
        key=str(definition["key"]),
        title=str(definition["title"]),
        description=str(definition["description"]),
        route=definition.get("route"),
        docs_url=definition.get("docs_url"),
        completed=bool(row.completed) if row else False,
        completed_at=row.completed_at if row else None,
        skipped=bool(row.skipped) if row else False,
        skipped_at=row.skipped_at if row else None,
        metadata_json=row.metadata_json if row else {},
        created_at=row.created_at if row else None,
        updated_at=row.updated_at if row else None,
    )


def _ensure_key(key: str) -> None:
    if key not in CHECKLIST_BY_KEY:
        raise BadRequestError(f"Unknown onboarding key: {key}")
