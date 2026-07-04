from __future__ import annotations
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.integration_designer.schemas import DesignerBuildRequest
from app.scenario_library.schemas import ScenarioInstallRequest
from app.scenario_library.service import install_scenario

async def build(session: AsyncSession, request: DesignerBuildRequest) -> dict[str, Any]:
    source = request.source or {}
    target = request.target or {}
    logic = request.logic or {}
    install_request = ScenarioInstallRequest(
        endpoint_slug=source.get("endpoint_slug") or logic.get("endpoint_slug"),
        endpoint_name=source.get("endpoint_name"),
        source_system=source.get("source_system"),
        target_system=target.get("target_system"),
        target_connector_id=target.get("target_connector_id"),
        response_mode=logic.get("response_mode") or "sync_response",
        input_mode=source.get("input_mode"),
        auth_mode=source.get("auth_mode") or "none",
        auth_config_json=source.get("auth_config_json") or {},
        create_test_case=True,
    )
    result = await install_scenario(session, request.scenario_code, install_request)
    return {
        "created": {
            "endpoint_id": result["endpoint_id"],
            "route_id": result["route_id"],
            "workflow_id": result["workflow_id"],
            "operation_template_id": result.get("operation_template_id"),
            "test_case_id": result.get("test_case_id"),
        },
        "endpoint_url": result["endpoint_url"],
        "curl_example": result["curl_example"],
        "onec_http_example": result["onec_http_example"],
        "next_steps": result["next_steps"],
    }
