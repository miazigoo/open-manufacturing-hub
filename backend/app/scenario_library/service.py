from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.integration_flows import service as flow_service
from app.integration_bus import repository as bus_repository
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute
from app.operation_templates.models import OperationTemplate
from app.scenario_library.presets import SCENARIOS, scenario_by_code
from app.scenario_library.schemas import ScenarioInstallRequest
from app.test_console.models import SavedTestCase
from app.workflows.models import Workflow


def list_scenarios() -> list[dict[str, Any]]:
    return SCENARIOS


def preview_scenario(code: str) -> dict[str, Any]:
    scenario = _scenario_or_error(code)
    names = _names(scenario, ScenarioInstallRequest())
    return {
        "scenario": code,
        "will_create": {"endpoints": 1, "routes": 1, "workflows": 1, "operation_templates": 1, "test_cases": 1},
        "objects": [
            {"type": "endpoint", "name": names["endpoint_name"]},
            {"type": "route", "name": names["route_name"]},
            {"type": "workflow", "name": names["workflow_name"]},
            {"type": "operation_template", "name": names["operation_name"]},
            {"type": "test_case", "name": names["test_case_name"]},
        ],
    }


async def install_scenario(session: AsyncSession, code: str, request: ScenarioInstallRequest) -> dict[str, Any]:
    if code == "marking_pool_to_internal_service":
        flow = await flow_service.install_marking_pool_preset(session)
        test_case_result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == f"Flow {flow.name} Test"))
        test_case = test_case_result.scalar_one_or_none()
        return {
            "scenario": code,
            "endpoint_id": flow.endpoint_id,
            "route_id": flow.route_id,
            "workflow_id": flow.workflow_id,
            "operation_template_id": flow.operation_template_id,
            "test_case_id": test_case.id if test_case else None,
            "endpoint_url": flow_service.endpoint_url(flow.slug),
            "curl_example": flow_service.curl_example(flow.slug, "json", flow.test_payload_json),
            "onec_http_example": flow_service.onec_http_example(flow.slug, "json"),
            "next_steps": ["Open Integration Flows", "Test matcher trace", "Send sample payload and inspect timeline artifacts"],
        }
    if code == "onec_post_two_odata_to_endpoint":
        flow = await flow_service.install_two_odata_to_endpoint_preset(session)
        test_case_result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == f"Flow {flow.name} Test"))
        test_case = test_case_result.scalar_one_or_none()
        return {
            "scenario": code,
            "endpoint_id": flow.endpoint_id,
            "route_id": flow.route_id,
            "workflow_id": flow.workflow_id,
            "operation_template_id": flow.operation_template_id,
            "test_case_id": test_case.id if test_case else None,
            "endpoint_url": flow_service.endpoint_url(flow.slug),
            "curl_example": flow_service.curl_example(flow.slug, "json", flow.test_payload_json),
            "onec_http_example": flow_service.onec_http_example(flow.slug, "json"),
            "next_steps": ["Open Visual Flow Builder", "Preview OData/JSON steps", "Send sample payload and inspect builder artifacts"],
        }
    if code == "dnp_pull_codes_by_order":
        flow = await flow_service.install_dnp_pull_codes_preset(session)
        test_case_result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == f"Flow {flow.name} Test"))
        test_case = test_case_result.scalar_one_or_none()
        return {
            "scenario": code,
            "endpoint_id": flow.endpoint_id,
            "route_id": flow.route_id,
            "workflow_id": flow.workflow_id,
            "operation_template_id": flow.operation_template_id,
            "test_case_id": test_case.id if test_case else None,
            "endpoint_url": flow_service.endpoint_url(flow.slug),
            "curl_example": flow_service.curl_example(flow.slug, "json", flow.test_payload_json),
            "onec_http_example": flow_service.onec_http_example(flow.slug, "json"),
            "next_steps": ["Open Integration Flows", "Check operation key dnp_key_connect_odata_pull_codes", "Run saved test case and inspect OData artifacts"],
        }
    scenario = _scenario_or_error(code)
    names = _names(scenario, request)
    workflow = await _upsert_workflow(session, scenario, names["workflow_name"], request)
    operation = await _upsert_operation_template(session, scenario, names["operation_name"], workflow.id)
    endpoint = await _upsert_endpoint(session, scenario, names["endpoint_name"], workflow.id, operation.id, request)
    route = await _upsert_route(session, scenario, names["route_name"], workflow.id, operation.id, request)
    endpoint.route_id = route.id
    test_case = await _upsert_test_case(session, scenario, names["test_case_name"], endpoint, request) if request.create_test_case else None
    await session.flush()
    endpoint_url = f"/api/bus/in/{endpoint.slug}"
    return {
        "scenario": code,
        "endpoint_id": endpoint.id,
        "route_id": route.id,
        "workflow_id": workflow.id,
        "operation_template_id": operation.id,
        "test_case_id": test_case.id if test_case else None,
        "endpoint_url": endpoint_url,
        "curl_example": curl_example(endpoint.slug, endpoint.input_mode, scenario["sample_payload"]),
        "onec_http_example": onec_http_example(endpoint.slug, endpoint.input_mode),
        "next_steps": ["Copy endpoint URL to 1C or the external system", "Run the saved test case", "Open the event timeline and inspect artifacts"],
    }


def curl_example(slug: str, input_mode: str, payload: Any) -> str:
    if input_mode == "xml":
        return f"curl -X POST http://localhost:8000/api/bus/in/{slug} -H 'Content-Type: application/xml' --data-binary @document.xml"
    body = json.dumps(payload if isinstance(payload, dict) else {"payload": payload}, ensure_ascii=False)
    return f"curl -X POST http://localhost:8000/api/bus/in/{slug} -H 'Content-Type: application/json' --data '{body}'"


def onec_http_example(slug: str, input_mode: str) -> str:
    content_type = "application/xml" if input_mode == "xml" else "application/json"
    body = "XMLСтрока" if input_mode == "xml" else "JSONСтрока"
    return "\n".join([
        'HTTPСоединение = Новый HTTPСоединение("server", 8000);',
        f'Запрос = Новый HTTPЗапрос("/api/bus/in/{slug}");',
        f'Запрос.Заголовки.Вставить("Content-Type", "{content_type}");',
        f"Запрос.УстановитьТелоИзСтроки({body});",
        "Ответ = HTTPСоединение.ОтправитьДляОбработки(Запрос);",
    ])


def _scenario_or_error(code: str) -> dict[str, Any]:
    scenario = scenario_by_code(code)
    if scenario is None:
        raise BadRequestError(f"Unknown scenario: {code}")
    return scenario


def _names(scenario: dict[str, Any], request: ScenarioInstallRequest) -> dict[str, str]:
    title = scenario["title"]
    slug = request.endpoint_slug or scenario["default_slug"]
    suffix = f" [{slug}]" if request.endpoint_slug and request.endpoint_slug != scenario["default_slug"] else ""
    return {
        "endpoint_name": request.endpoint_name or f"Designer {title}{suffix} Endpoint",
        "route_name": f"Designer {title}{suffix} Route",
        "workflow_name": f"Designer {title}{suffix} Workflow",
        "operation_name": f"Designer {title}{suffix} Operation",
        "test_case_name": f"Test {title}{suffix}",
        "slug": slug,
    }


async def _upsert_workflow(session: AsyncSession, scenario: dict[str, Any], name: str, request: ScenarioInstallRequest) -> Workflow:
    result = await session.execute(select(Workflow).where(Workflow.name == name))
    workflow = result.scalar_one_or_none()
    steps = [{"name": item} if isinstance(item, str) else item for item in scenario["workflow_steps"]]
    data = {
        "name": name,
        "description": scenario["description"],
        "event_type": scenario["event_type"],
        "source_system": request.source_system or scenario["source"],
        "target_system": request.target_system or scenario["target"],
        "entity_type": scenario.get("entity_type"),
        "version": 1,
        "enabled": True,
        "steps_json": steps,
        "validation_json": {"required_fields": []},
    }
    if workflow is None:
        workflow = Workflow(**data)
        session.add(workflow)
    else:
        for key, value in data.items():
            setattr(workflow, key, value)
    await session.flush()
    return workflow


async def _upsert_operation_template(session: AsyncSession, scenario: dict[str, Any], name: str, workflow_id) -> OperationTemplate:
    result = await session.execute(select(OperationTemplate).where(or_(OperationTemplate.name == name, OperationTemplate.operation_code == scenario["operation_code"])))
    template = result.scalar_one_or_none()
    data = {
        "name": name,
        "operation_code": scenario["operation_code"],
        "system_type": "onec" if "onec" in scenario["operation_code"] else "printing" if "printer" in scenario["operation_code"] else "rest",
        "operation": scenario["operation_code"].split(".")[-1],
        "direction": "inbound",
        "input_mode": scenario["input_modes"][0],
        "output_mode": "json",
        "description": scenario["description"],
        "enabled": True,
        "request_template_json": {"sample": scenario["sample_payload"]},
        "example_request_json": scenario["sample_payload"] if isinstance(scenario["sample_payload"], dict) else {"xml": scenario["sample_payload"]},
        "default_workflow_id": workflow_id,
    }
    if template is None:
        template = OperationTemplate(**data)
        session.add(template)
    else:
        for key, value in data.items():
            setattr(template, key, value)
    await session.flush()
    return template


async def _upsert_endpoint(session: AsyncSession, scenario: dict[str, Any], name: str, workflow_id, operation_id, request: ScenarioInstallRequest) -> IntegrationEndpoint:
    slug = request.endpoint_slug or scenario["default_slug"]
    endpoint = await bus_repository.get_endpoint_by_slug(session, slug)
    input_mode = request.input_mode or ("xml" if "xml" in scenario["input_modes"] else "json")
    data = {
        "name": name,
        "slug": slug,
        "enabled": True,
        "description": scenario["description"],
        "input_mode": input_mode,
        "response_mode": request.response_mode,
        "default_source_system": request.source_system or scenario["source"],
        "default_target_system": request.target_system or scenario["target"],
        "default_event_type": scenario["event_type"],
        "default_entity_type": scenario.get("entity_type"),
        "workflow_id": workflow_id,
        "operation_template_id": operation_id,
        "auth_mode": request.auth_mode,
        "auth_config_json": request.auth_config_json,
    }
    if endpoint is None:
        endpoint = IntegrationEndpoint(**data)
        session.add(endpoint)
    else:
        for key, value in data.items():
            setattr(endpoint, key, value)
    await session.flush()
    return endpoint


async def _upsert_route(session: AsyncSession, scenario: dict[str, Any], name: str, workflow_id, operation_id, request: ScenarioInstallRequest) -> IntegrationRoute:
    result = await session.execute(select(IntegrationRoute).where(IntegrationRoute.name == name))
    route = result.scalar_one_or_none()
    data = {
        "name": name,
        "enabled": True,
        "source_system": request.source_system or scenario["source"],
        "target_system": request.target_system or scenario["target"],
        "event_type": scenario["event_type"],
        "message_type": scenario.get("entity_type"),
        "document_type": scenario.get("entity_type"),
        "operation": scenario["operation_code"].split(".")[-1],
        "condition_json": {},
        "workflow_id": workflow_id,
        "target_connector_id": request.target_connector_id,
        "operation_template_id": operation_id,
        "priority": 50,
    }
    if route is None:
        route = IntegrationRoute(**data)
        session.add(route)
    else:
        for key, value in data.items():
            setattr(route, key, value)
    await session.flush()
    return route


async def _upsert_test_case(session: AsyncSession, scenario: dict[str, Any], name: str, endpoint: IntegrationEndpoint, request: ScenarioInstallRequest) -> SavedTestCase:
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.name == name))
    test_case = result.scalar_one_or_none()
    payload = scenario["sample_payload"]
    data = {
        "name": name,
        "description": scenario["description"],
        "endpoint_id": endpoint.id,
        "method": "POST",
        "headers_json": {"Content-Type": "application/xml" if endpoint.input_mode == "xml" else "application/json"},
        "body_text": payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2),
        "body_json": payload if isinstance(payload, dict) else None,
        "input_mode": endpoint.input_mode,
        "expected_status": "success",
    }
    if test_case is None:
        test_case = SavedTestCase(**data)
        session.add(test_case)
    else:
        for key, value in data.items():
            setattr(test_case, key, value)
    await session.flush()
    return test_case
