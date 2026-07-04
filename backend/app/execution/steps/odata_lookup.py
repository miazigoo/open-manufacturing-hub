from __future__ import annotations

from typing import Any

from app.connectors import repository as connector_repository
from app.connectors.models import ConnectorInstance
from app.connectors.builtin.onec.odata import read_odata
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.mappings.engine import get_path
from app.onec_workbench.lookup import extract_fields, render_filter_template
from app.integration_bus import repository as bus_repository


class ODataLookupStep:
    name = "odata_lookup"
    display_name = "OData Lookup"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = (context.current_step.step_config_json or {}).get("config") or {}
        template = await bus_repository.get_lookup_template_by_name(context.session, str(config["template"])) if config.get("template") else None
        connector: ConnectorInstance | None
        if template is not None:
            connector = await context.session.get(ConnectorInstance, template.connector_id)
            resource = template.resource
            filter_template = template.filter_template
            extract = template.extract_json
            required = template.required
            params = {}
        else:
            connector_name = config.get("connector") or context.target_system
            connector = await connector_repository.get_by_name(context.session, connector_name)
            resource = str(config.get("resource") or "")
            filter_template = str(config.get("filter_template") or "")
            extract = config.get("extract") or {}
            required = config.get("required", True)
            params = dict(config.get("params") or {})
        if connector is None:
            return StepResult.failed("CONNECTOR_NOT_FOUND", f"1C connector for lookup {config.get('template') or config.get('connector') or context.target_system} not found")
        if connector.connector_type != "onec":
            return StepResult.failed("INVALID_CONNECTOR_TYPE", f"Connector {connector.name} is not 1C")
        payload = dict(context.variables.get("payload") or {})
        inputs = {name: get_path(context.variables, path) for name, path in (config.get("input") or {}).items()}
        query = params
        query["$filter"] = render_filter_template(filter_template, inputs)
        result = await read_odata(connector.config_json, resource, query)
        artifacts = [ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "odata_lookup_request.json", result.request_payload or {"query": query})]
        if result.response_payload is not None:
            artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_lookup_response.json", result.response_payload))
        if not result.success:
            return StepResult.failed(result.error_code or "ODATA_LOOKUP_FAILED", result.error_message or "OData lookup failed", artifacts=artifacts)
        if not result.items and required:
            missing = ", ".join(f"{key}={value}" for key, value in inputs.items())
            return StepResult.failed("ODATA_LOOKUP_NOT_FOUND", f"Lookup {config.get('template') or resource} returned no rows for {missing}", artifacts=artifacts)
        extracted = extract_fields(result.items[0] if result.items else {}, extract)
        for target_path, source_key in (config.get("inject") or {}).items():
            _set_path(payload, target_path.replace("payload.", "", 1), extracted.get(source_key))
        lookup = dict(context.variables.get("lookup") or {})
        result_path = str(config.get("result_path") or "result")
        _set_path(lookup, result_path.replace("lookup.", "", 1), extracted)
        artifacts.append(ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "odata_lookup_result.json", extracted))
        return StepResult.success("OData lookup complete", artifacts=artifacts, variables_update={"lookup": lookup, "payload": payload, "canonical_payload": payload})


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    current = target
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    if parts:
        current[parts[-1]] = value
