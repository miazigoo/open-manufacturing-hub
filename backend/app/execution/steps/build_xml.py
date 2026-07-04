from __future__ import annotations

from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.xml_bridge.parser import build_xml_from_dict


class BuildXMLStep:
    name = "build_xml"
    display_name = "Build XML"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = (context.current_step.step_config_json or {}).get("config") or {}
        source_variable = config.get("source_variable", "mapped_payload")
        target_variable = config.get("target_variable", "xml_payload")
        root = str(config.get("root") or "Document")
        source = context.variables.get(source_variable) or context.variables.get("payload") or {}
        if not isinstance(source, dict):
            return StepResult.failed("XML_BUILD_FAILED", f"{source_variable} must be an object")
        xml = build_xml_from_dict(source, root=root)
        payload = dict(context.variables.get("payload") or {})
        payload[target_variable] = xml
        payload["xml"] = xml
        return StepResult.success("XML built", artifacts=[ArtifactCreate("built_xml", "built_xml.xml", {"xml": xml, "root": root})], variables_update={target_variable: xml, "payload": payload, "mapped_payload": payload})
