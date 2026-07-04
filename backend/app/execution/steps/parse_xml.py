from __future__ import annotations

from uuid import UUID

from app.core.enums import ArtifactType, IntegrationMessageStatus
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.onec_workbench.models import IntegrationMessage
from app.xml_bridge.parser import XMLBridgeError, parse_xml_safe


class ParseXMLStep:
    name = "parse_xml"
    display_name = "Parse XML"

    async def can_execute(self, context: PipelineContext) -> bool:
        payload = context.variables.get("payload") or {}
        return isinstance(payload, dict) and bool(payload.get("xml"))

    async def execute(self, context: PipelineContext) -> StepResult:
        payload = dict(context.variables.get("payload") or {})
        xml = str(payload.get("xml") or "")
        raw_artifact = ArtifactCreate("raw_xml", "raw_xml.xml", {"xml": xml, "size_bytes": len(xml.encode("utf-8"))})
        try:
            parsed = parse_xml_safe(xml)
        except XMLBridgeError as exc:
            await _mark_message(context, IntegrationMessageStatus.FAILED, str(exc))
            return StepResult.failed(exc.code, str(exc), artifacts=[raw_artifact, ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "xml_parse_error.json", {"error_code": exc.code, "error_message": str(exc)})])
        await _mark_message(context, IntegrationMessageStatus.PARSED, None, parsed)
        payload["parsed_xml"] = parsed
        return StepResult.success(
            "XML parsed",
            artifacts=[raw_artifact, ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "parsed_xml.json", parsed)],
            variables_update={"parsed_xml": parsed, "payload": payload, "canonical_payload": payload},
        )


async def _mark_message(context: PipelineContext, status: IntegrationMessageStatus, error: str | None, parsed: dict | None = None) -> None:
    message_id = (context.variables.get("payload") or {}).get("message_id") if isinstance(context.variables.get("payload"), dict) else None
    if not message_id:
        return
    message = await context.session.get(IntegrationMessage, UUID(str(message_id)))
    if message is None:
        return
    message.status = status
    message.last_error = error
    if parsed is not None:
        message.payload_json = parsed
    await context.session.flush()
