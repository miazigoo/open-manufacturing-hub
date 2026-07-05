from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.core.enums import EventStatus
from app.events import service as events_service
from app.events.models import IntegrationEvent
from app.flow_steps.registry import BUILDER_STEP_TYPES
from app.integration_bus import repository as bus_repository
from app.integration_bus.schemas import INPUT_MODES, RESPONSE_MODES
from app.integration_flows import repository as flow_repository
from app.integration_flows import service as flow_service
from app.matchers.schemas import MATCHER_TYPES
from app.operation_templates import repository as operation_repository
from app.odata_connections import service as odata_connection_service
from app.packages import repository as package_repository
from app.packages.service import package_navigation
from app.scenario_library.service import list_scenarios
from app.test_console import repository as test_case_repository

ONEC_PACKAGE = "omh-package-onec"

QUICK_ACTIONS = [
    {"code": "onec_to_api", "title": "1C -> Website/API", "description": "1C sends JSON/XML to an external API.", "preset": "onec_to_api"},
    {"code": "api_to_onec", "title": "Website/API -> 1C", "description": "External API calls a 1C HTTP service.", "preset": "api_to_onec"},
    {"code": "onec_xml_raw_bridge", "title": "1C XML -> 1C", "description": "Forward raw XML safely between 1C services.", "preset": "onec_xml_raw_bridge"},
    {"code": "onec_to_printer", "title": "1C -> Printer", "description": "Route 1C print requests to ZPL printers.", "preset": "onec_to_printer"},
    {"code": "onec_post_two_odata_to_endpoint", "title": "1C POST -> OData -> API", "description": "Read fields, query OData, build JSON and send endpoint.", "preset": "onec_post_two_odata_to_endpoint", "primary": True},
]


async def navigation(session: AsyncSession) -> list[dict[str, Any]]:
    package_items = await package_navigation(session)
    groups = [
        ("Operate", [
            ("Documentation", "/docs", None, False),
            ("Onboarding", "/onboarding", None, False),
            ("Dashboard", "/", None, False),
            ("Transaction Monitor", "/runtime/monitor", None, False),
            ("Integration Queue", "/runtime/queue", None, False),
            ("DLQ", "/runtime/dlq", None, False),
            ("Audit Log", "/audit", None, False),
            ("Event Journal", "/events", None, False),
            ("Incidents", "/incidents", None, False),
            ("Health", "/health", None, False),
        ]),
        ("Build", [
            ("1C Integration Cockpit", "/onec-cockpit", ONEC_PACKAGE, False),
            ("Integration Flows", "/integration-flows", None, False),
            ("Training Sandbox", "/training", "omh-package-training", False),
            ("Test Console", "/test-console", None, False),
            ("Saved Test Cases", "/test-cases", None, False),
        ]),
        ("Data Tools", [
            ("OData Connections", "/odata-connections", ONEC_PACKAGE, False),
            ("OData Explorer", "/odata-explorer", ONEC_PACKAGE, False),
            ("XML Tools", "/xml-tools", ONEC_PACKAGE, False),
            ("JSON Builder / Mappings", "/mappings", None, False),
            ("Business Objects", "/business-objects", None, False),
            ("Resolvers", "/resolvers", None, False),
            ("Resolver Cache", "/resolvers/cache", None, False),
            ("Transform Library", "/transforms", None, False),
            ("Business Rules", "/business-rules", None, False),
        ]),
        ("Packages", [
            ("Packages", "/packages", None, False),
            ("Plugin Store", "/plugin-store", None, False),
            ("1C Package", "/packages/omh-package-onec", ONEC_PACKAGE, False),
            ("Printer Package", "/packages/omh-package-printer", "omh-package-printer", False),
            ("Training Package", "/packages/omh-package-training", "omh-package-training", False),
        ]),
        ("Advanced", [
            ("Connectors", "/connectors", None, True),
            ("Secrets", "/secrets", "omh-package-secrets", True),
            ("Integration Bus", "/integration-bus", None, True),
            ("Workflows", "/workflows", None, True),
            ("Execution Steps", "/execution/steps", None, True),
            ("Maintenance", "/maintenance", None, True),
            ("Environments", "/environments", None, True),
            ("Change Sets", "/change-sets", None, True),
            ("Production", "/production", None, True),
            ("Retention", "/retention", None, True),
            ("Notifications", "/notifications", None, True),
        ]),
    ]
    enabled_by_package = {item["package_id"]: item["enabled"] for item in package_items}
    installed_package_ids = {item.package_id for item in await package_repository.list_installed(session)}
    result: list[dict[str, Any]] = []
    for group, items in groups:
        for title, route, package_id, advanced in items:
            enabled = True
            installed = False
            if package_id:
                installed = package_id in installed_package_ids
                enabled = installed and bool(enabled_by_package.get(package_id, False))
            result.append({"group": group, "title": title, "route": route, "package_id": package_id, "enabled": enabled, "installed": installed, "advanced": advanced})
    return result


async def cockpit_summary(session: AsyncSession) -> dict[str, Any]:
    package_state = await _package_state(session, ONEC_PACKAGE)
    flows = await flow_repository.list_flows(session)
    events = await events_service.get_event_journal(session)
    connectors = await connector_repository.list_instances(session)
    onec_events = [_event_row(item) for item in events if _is_onec_event(item.source_system, item.target_system, item.event_type, item.entity_type)][:8]
    onec_flows = [flow for flow in flows if flow.source_type.value == "onec" or flow.target_type.value == "onec" or "onec" in flow.slug]
    return {
        "package_state": package_state,
        "metrics": {
            "enabled_integrations": sum(1 for flow in onec_flows if flow.enabled),
            "failed_events": sum(1 for event in events if event.status == EventStatus.FAILED),
            "attention_events": sum(1 for event in events if event.requires_attention),
            "connectors": len(connectors),
        },
        "quick_actions": QUICK_ACTIONS,
        "integrations": [_flow_row(flow) for flow in onec_flows],
        "connection_health": [_connector_health(connector) for connector in connectors if connector.connector_type in {"onec", "rest", "zpl_printer"}],
        "recent_events": onec_events,
    }


async def cockpit_options(session: AsyncSession) -> dict[str, Any]:
    return {
        "package_state": await _package_state(session, ONEC_PACKAGE),
        **await _shared_options(session),
        "scenario_presets": list_scenarios(),
        "input_modes": sorted(INPUT_MODES),
        "response_modes": sorted(RESPONSE_MODES),
    }


async def flow_builder_options(session: AsyncSession) -> dict[str, Any]:
    return {
        "package_state": await _package_state(session, ONEC_PACKAGE),
        **await _shared_options(session),
        "matcher_types": sorted(MATCHER_TYPES),
        "action_types": ["call_rest_api", "call_1c_http_service", "call_printer", "call_odata_lookup", "create_event_only"],
        "available_steps": [{"type": key, "description": value} for key, value in BUILDER_STEP_TYPES.items()],
        "saved_test_cases": [_test_case_option(item) for item in await test_case_repository.list_test_cases(session)],
    }


async def flow_builder_state(session: AsyncSession, flow_id: UUID) -> dict[str, Any]:
    flow = await flow_service.get_flow_or_404(session, flow_id)
    return {"flow_id": flow.id, "flow": await flow_service._read_flow(flow, session), "builder_json": flow.builder_json or {}, "options": await flow_builder_options(session)}


async def _shared_options(session: AsyncSession) -> dict[str, Any]:
    connectors = await connector_repository.list_instances(session)
    operations = await operation_repository.list_templates(session)
    lookups = await bus_repository.list_lookup_templates(session)
    odata_connections = await odata_connection_service.list_connections(session)
    connector_options = [_connector_option(item) for item in connectors]
    return {
        "connectors": connector_options,
        "onec_connectors": [_connector_option(item) for item in connectors if item.connector_type == "onec"],
        "odata_connections": [{"id": str(item.id), "label": item.name, "type": "odata_connection", "meta": {"connector_id": str(item.connector_id), "base_url": item.base_url, "enabled": item.enabled, "tags": item.tags}} for item in odata_connections],
        "rest_connectors": [_connector_option(item) for item in connectors if item.connector_type == "rest"],
        "printer_connectors": [_connector_option(item) for item in connectors if item.connector_type == "zpl_printer"],
        "operation_templates": [{"id": str(item.id), "label": item.name, "type": item.system_type, "meta": {"operation": item.operation, "input_mode": item.input_mode, "output_mode": item.output_mode}} for item in operations],
        "odata_lookup_templates": [{"id": str(item.id), "label": item.name, "type": "odata_lookup", "meta": {"resource": item.resource, "required": item.required}} for item in lookups],
    }


async def _package_state(session: AsyncSession, package_id: str) -> dict[str, Any]:
    package = await package_repository.get_installed(session, package_id)
    if package is None:
        return {"package_id": package_id, "installed": False, "enabled": False, "status": None, "action_label": "Install package"}
    return {"package_id": package_id, "installed": True, "enabled": package.enabled, "status": package.status.value, "action_label": "Enable package" if not package.enabled else "Open"}


def _connector_option(item: Any) -> dict[str, Any]:
    return {"id": str(item.id), "label": item.name, "type": item.connector_type, "meta": {"enabled": item.enabled, "status": item.status.value if hasattr(item.status, "value") else str(item.status), "direction": item.direction.value if hasattr(item.direction, "value") else str(item.direction)}}


def _connector_health(item: Any) -> dict[str, Any]:
    status = item.last_health_status.value if item.last_health_status and hasattr(item.last_health_status, "value") else ("ok" if item.enabled else "disabled")
    return {"id": str(item.id), "name": item.name, "connector_type": item.connector_type, "status": status, "message": item.last_health_message or ("Enabled" if item.enabled else "Disabled"), "updated_at": item.last_health_at.isoformat() if item.last_health_at else None}


def _flow_row(flow: Any) -> dict[str, Any]:
    return {"id": str(flow.id), "name": flow.name, "slug": flow.slug, "enabled": flow.enabled, "endpoint_url": flow_service.endpoint_url(flow.slug), "source": flow.source_type.value, "target": flow.target_type.value, "last_status": "enabled" if flow.enabled else "disabled", "last_error": None, "builder_url": f"/integration-flows/{flow.id}/builder", "onec_http_example": flow_service.onec_http_example(flow.slug, "json")}


def _event_row(item: Any) -> dict[str, Any]:
    return {"id": str(item.id), "status": item.status.value if hasattr(item.status, "value") else str(item.status), "title": item.human_title, "summary": item.human_summary, "source": item.source_display, "target": item.target_display, "created_at": item.created_at.isoformat(), "timeline_url": f"/events/{item.id}", "requires_attention": item.requires_attention, "last_error_code": item.last_error_code}


def _test_case_option(item: Any) -> dict[str, Any]:
    return {"id": str(item.id), "label": item.name, "type": item.input_mode, "meta": {"endpoint_id": str(item.endpoint_id) if item.endpoint_id else None, "expected_status": item.expected_status}}


def _is_onec_event(source: str | None, target: str | None, event_type: str | None, entity_type: str | None) -> bool:
    text = " ".join(str(part or "") for part in (source, target, event_type, entity_type)).lower()
    return any(marker in text for marker in ("1c", "onec", "xml", "odata", "print"))
