from __future__ import annotations

from typing import Any

from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope
from app.xml_toolkit import service


class XmlExtractStep:
    name = "xml_extract"
    display_name = "Extract XML fields"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            raw_xml = _source_xml(context, str(config.get("source") or "request.body_raw"))
        except ValueError as exc:
            return StepResult.failed("XML_SOURCE_EMPTY", str(exc), hint="Use an XML endpoint or select the correct source field.")
        fields = [field for field in config.get("fields") or [] if isinstance(field, dict)]
        parsed = service.parse(raw_xml)
        artifacts = [
            ArtifactCreate(ArtifactType.RAW_PAYLOAD.value, "xml_parse_input.xml", {"xml": raw_xml, "size_bytes": len(raw_xml.encode("utf-8")), "sha256": parsed.sha256}),
            ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "xml_parse_tree.json", parsed.model_dump(mode="json")),
        ]
        if not parsed.success:
            return StepResult.failed("XML_PARSE_FAILED", "; ".join(parsed.errors), artifacts=artifacts, hint="Check incoming XML, Content-Type, encoding and namespaces.")
        extraction = service.extract(raw_xml, fields=[_field_model(field) for field in fields])
        values, errors = extraction.values, extraction.errors
        artifacts.append(ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "xml_extracted_fields.json", {"fields": fields, "values": values, "errors": errors}))
        if errors:
            return StepResult.failed("XML_REQUIRED_FIELD_MISSING", "; ".join(str(item.get("message")) for item in errors), artifacts=artifacts, variables_update={"xml_fields": values}, hint="Open XML path picker and check required field paths.")
        step_id = str(config.get("step_id") or "xml_extract")
        steps = dict(context.variables.get("steps") or {})
        steps[step_id] = values
        return StepResult.success("XML fields extracted", artifacts=artifacts, variables_update={**values, "xml_fields": values, "steps": steps})


class RawXmlForwardStep:
    name = "raw_xml_forward"
    display_name = "Raw XML forward"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            raw_xml = _source_xml(context, str(config.get("source") or "request.body_raw"))
        except ValueError as exc:
            return StepResult.failed("XML_SOURCE_EMPTY", str(exc), hint="Use an XML endpoint or select the correct source field.")
        preview = service.raw_forward_preview(raw_xml, str(config.get("forwarded_xml")) if config.get("forwarded_xml") is not None else None)
        step_id = str(config.get("step_id") or "raw_xml_forward")
        result = {"forwarded": False, "method": str(config.get("method") or "POST").upper(), "path": config.get("path"), **preview.model_dump(mode="json")}
        artifacts = [
            ArtifactCreate(ArtifactType.RAW_PAYLOAD.value, "raw_xml_forward_input.xml", {"xml": raw_xml, "sha256": preview.input_sha256}),
            ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "raw_xml_forward.json", result),
        ]
        steps = dict(context.variables.get("steps") or {})
        steps[step_id] = result
        return StepResult.success("Raw XML preserved for forwarding", artifacts=artifacts, variables_update={"raw_xml_forward": result, "steps": steps})


def _field_model(field: dict[str, Any]):
    from app.xml_toolkit.schemas import XmlExtractField

    return XmlExtractField(**field)


def _config(context: PipelineContext) -> dict[str, Any]:
    return dict((context.current_step.step_config_json or {}).get("config") or {})


def _source_xml(context: PipelineContext, source: str) -> str:
    scope = build_runtime_scope(
        request_body=context.variables.get("payload") or {},
        variables=context.variables,
        headers=(context.variables.get("payload") or {}).get("_headers") if isinstance(context.variables.get("payload"), dict) else {},
        query=(context.variables.get("payload") or {}).get("_query") if isinstance(context.variables.get("payload"), dict) else {},
        raw_text=(context.variables.get("payload") or {}).get("text") if isinstance(context.variables.get("payload"), dict) else None,
        xml=(context.variables.get("payload") or {}).get("xml") if isinstance(context.variables.get("payload"), dict) else None,
        context={"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id},
    )
    aliases = {
        "request.body_raw": "request.raw_text",
        "request.xml": "request.xml",
        "payload.xml": "variables.payload.xml",
        "payload.text": "variables.payload.text",
    }
    candidate = aliases.get(source, source)
    try:
        value = resolve_path(scope, candidate)
    except PathResolutionError:
        payload = context.variables.get("payload") or {}
        value = payload.get("xml") or payload.get("text") if isinstance(payload, dict) else None
    if value in (None, ""):
        raise ValueError(f"XML source is empty: {source}")
    return str(value)
