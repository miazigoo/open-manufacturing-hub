from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import NotFoundError
from app.integration_bus import repository as bus_repository
from app.integration_flows.models import IntegrationFlow
from app.integration_flows import service as flow_service
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.packages import repository as package_repository
from app.packages.installer import PackageInstaller
from app.packages_training.examples import get_example, list_examples
from app.packages_training.presets import TRAINING_CONNECTORS, TRAINING_FLOWS
from app.packages_training.reset import reset_training_data
from app.test_console.models import SavedTestCase
from app.test_console.schemas import TestConsoleSendRequest
from app.test_console import service as test_console_service

PACKAGE_ID = "omh-package-training"


async def install_training_sandbox(session: AsyncSession) -> dict[str, Any]:
    if await package_repository.get_installed(session, PACKAGE_ID) is None:
        await PackageInstaller().install_package(session, PACKAGE_ID, install_demo_data=False)
    await reset_training_data(session)
    connectors = [await _upsert_connector(session, item) for item in TRAINING_CONNECTORS]
    flows = [await _create_training_flow(session, item) for item in TRAINING_FLOWS]
    test_cases = [await _upsert_example_test_case(session, example) for example in list_examples()]
    await session.flush()
    return {
        "installed": True,
        "package_id": PACKAGE_ID,
        "connectors": [_connector_row(item) for item in connectors],
        "flows": [{"id": str(item.id), "name": item.name, "slug": item.slug, "endpoint_url": flow_service.endpoint_url(item.slug)} for item in flows],
        "examples": list_examples(),
        "test_cases": [{"id": str(item.id), "name": item.name, "endpoint_id": str(item.endpoint_id) if item.endpoint_id else None} for item in test_cases],
    }


async def reset_sandbox(session: AsyncSession) -> dict[str, Any]:
    return {"reset": True, "deleted": await reset_training_data(session), "installed": False}


async def status(session: AsyncSession) -> dict[str, Any]:
    package = await package_repository.get_installed(session, PACKAGE_ID)
    connectors = await _training_connectors(session)
    flows = await _training_flows(session)
    cases = await _training_test_cases(session)
    return {
        "package": {"installed": package is not None, "enabled": bool(package and package.enabled), "status": package.status.value if package else None},
        "sandbox_installed": bool(connectors and flows and cases),
        "connectors": [_connector_row(item) for item in connectors],
        "flows": [{"id": str(item.id), "name": item.name, "slug": item.slug, "endpoint_url": flow_service.endpoint_url(item.slug)} for item in flows],
        "test_cases": [{"id": str(item.id), "name": item.name, "endpoint_id": str(item.endpoint_id) if item.endpoint_id else None, "last_run_status": item.last_run_status} for item in cases],
        "examples": list_examples(),
    }


async def run_example(session: AsyncSession, example_id: str) -> dict[str, Any]:
    example = get_example(example_id)
    if example is None:
        raise NotFoundError("Training example not found")
    endpoint = await bus_repository.get_endpoint_by_slug(session, example["endpoint_slug"])
    if endpoint is None:
        return {
            "success": True,
            "example_id": example_id,
            "requires_setup": True,
            "dry_run": True,
            "response": {
                "status": "requires_setup",
                "message": "Install Training Sandbox before running this example.",
                "open_in_test_console": f"/test-console?trainingExampleId={example_id}",
            },
            "event_id": None,
            "message_id": None,
            "timeline_url": None,
            "external_error": None,
        }
    request = TestConsoleSendRequest(
        endpoint_id=endpoint.id,
        input_mode=example.get("input_mode", "json"),
        headers_json={str(key): str(value) for key, value in (example.get("headers") or {}).items()},
        body_text=example.get("body_text"),
        body_json=example.get("body") if example.get("input_mode", "json") == "json" else None,
        dry_run=False,
    )
    result = await test_console_service.send(session, request)
    await _mark_example_case(session, example_id, result)
    return {
        "success": bool(result.get("success")),
        "example_id": example_id,
        "requires_setup": False,
        "dry_run": bool(result.get("dry_run")),
        "response": result.get("response") or {},
        "event_id": str(result["event_id"]) if result.get("event_id") else None,
        "message_id": str(result["message_id"]) if result.get("message_id") else None,
        "timeline_url": result.get("timeline_url"),
        "external_error": result.get("external_error"),
    }


async def open_test_console(example_id: str) -> dict[str, Any]:
    example = get_example(example_id)
    if example is None:
        raise NotFoundError("Training example not found")
    return {"example": example, "url": f"/test-console?trainingExampleId={example_id}"}


async def _upsert_connector(session: AsyncSession, data: dict[str, Any]) -> ConnectorInstance:
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == data["name"]))
    connector = result.scalar_one_or_none()
    direction = ConnectorDirection(data.get("direction") or "target")
    payload = {
        "name": data["name"],
        "connector_type": data["connector_type"],
        "direction": direction,
        "enabled": True,
        "status": ConnectorInstanceStatus.ENABLED,
        "config_json": data["config_json"],
    }
    if connector is None:
        connector = ConnectorInstance(**payload)
        session.add(connector)
    else:
        for key, value in payload.items():
            setattr(connector, key, value)
    await session.flush()
    return connector


async def _create_training_flow(session: AsyncSession, data: dict[str, Any]):
    request = IntegrationFlowCreate(
        name=data["name"],
        slug=data["slug"],
        description=data.get("description"),
        source_type=IntegrationFlowSourceType.ONEC,
        target_type=IntegrationFlowTargetType(data.get("target_type") or "external_api"),
        endpoint=EndpointBuilderConfig(**data.get("endpoint", {})),
        matcher_group_json={"mode": "all", "rules": [{"type": "always"}]},
        action_json={**data.get("action_json", {}), "business_object": data["slug"]},
        response_config_json={"training": True},
        builder_json=data.get("builder_json"),
        test_payload_json=data.get("test_payload_json"),
        test_payload_text=data.get("test_payload_text"),
    )
    return await flow_service.create_flow(session, request)


async def _upsert_example_test_case(session: AsyncSession, example: dict[str, Any]) -> SavedTestCase:
    endpoint = await bus_repository.get_endpoint_by_slug(session, example["endpoint_slug"])
    name = f"Training Example — {example['id']}"
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == name))
    test_case = result.scalar_one_or_none()
    data = {
        "name": name,
        "description": _localized(example.get("description")),
        "endpoint_id": endpoint.id if endpoint else None,
        "method": example.get("method", "POST"),
        "headers_json": example.get("headers") or {},
        "body_text": example.get("body_text"),
        "body_json": example.get("body") if example.get("input_mode", "json") == "json" else None,
        "input_mode": example.get("input_mode", "json"),
        "expected_status": "success" if not str(example["id"]).startswith("training.errors.") else "failed",
    }
    if test_case is None:
        test_case = SavedTestCase(**data)
        session.add(test_case)
    else:
        for key, value in data.items():
            setattr(test_case, key, value)
    await session.flush()
    return test_case


async def _mark_example_case(session: AsyncSession, example_id: str, result: dict[str, Any]) -> None:
    db_result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == f"Training Example — {example_id}"))
    test_case = db_result.scalar_one_or_none()
    if test_case:
        test_case.last_run_event_id = result.get("event_id")
        test_case.last_run_status = "success" if result.get("success") else "failed"
        await session.flush()


async def _training_connectors(session: AsyncSession) -> list[ConnectorInstance]:
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name.like("Training %")).order_by(ConnectorInstance.name.asc()))
    return list(result.scalars().all())


async def _training_flows(session: AsyncSession):
    result = await session.execute(select(IntegrationFlow).where(IntegrationFlow.name.like("Training %")).order_by(IntegrationFlow.name.asc()))
    return list(result.scalars().all())


async def _training_test_cases(session: AsyncSession) -> list[SavedTestCase]:
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.name.like("Training Example %")).order_by(SavedTestCase.name.asc()))
    return list(result.scalars().all())


def _connector_row(item: ConnectorInstance) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "connector_type": item.connector_type,
        "direction": item.direction.value if hasattr(item.direction, "value") else str(item.direction),
        "enabled": item.enabled,
        "status": item.status.value if hasattr(item.status, "value") else str(item.status),
        "base_url": (item.config_json or {}).get("base_url") or (item.config_json or {}).get("url"),
    }


def _localized(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("ru") or value.get("en") or next(iter(value.values()), None)
    return value if isinstance(value, str) else None
