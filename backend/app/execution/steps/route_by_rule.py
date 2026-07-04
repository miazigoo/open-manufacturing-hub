from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enums import IntegrationMessageStatus
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.mappings.engine import get_path
from app.onec_workbench.models import IntegrationMessage


class RouteByRuleStep:
    name = "route_by_rule"
    display_name = "Route by Rule"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        config = (context.current_step.step_config_json or {}).get("config") or {}
        payload = dict(context.variables.get("payload") or {})
        decision = _decide(config, payload, context)
        if decision.get("target_system"):
            context.target_system = decision["target_system"]
            context.event.target_system = decision["target_system"]
        route = {"target_system": context.target_system, "operation": decision.get("operation"), "matched_rule": decision.get("matched_rule")}
        payload.setdefault("_omh", {})
        if isinstance(payload["_omh"], dict) and decision.get("operation"):
            payload["_omh"]["operation"] = decision["operation"]
        await _mark_message_routed(context, route)
        return StepResult.success("Route selected", artifacts=[ArtifactCreate("routing_decision", "routing_decision.json", route)], variables_update={"route": route, "payload": payload})


def _decide(config: dict[str, Any], payload: dict[str, Any], context: PipelineContext) -> dict[str, Any]:
    candidates = {**payload, "source_system": context.source_system, "target_system": context.target_system, "event_type": context.event.event_type, "message_type": context.event.entity_type}
    for index, rule in enumerate(config.get("rules") or []):
        when = rule.get("when") or {}
        if all(_value(candidates, key) == expected for key, expected in when.items()):
            return {**rule, "matched_rule": index}
    return {**(config.get("default") or {}), "matched_rule": None}


def _value(payload: dict[str, Any], key: str) -> Any:
    if key in payload:
        return payload[key]
    return get_path(payload, key)


async def _mark_message_routed(context: PipelineContext, route: dict[str, Any]) -> None:
    payload = context.variables.get("payload") if isinstance(context.variables.get("payload"), dict) else {}
    message_id = payload.get("message_id")
    if not message_id:
        return
    message = await context.session.get(IntegrationMessage, UUID(str(message_id)))
    if message is None:
        return
    message.status = IntegrationMessageStatus.ROUTED
    message.target_system = route.get("target_system") or message.target_system
    message.route_key = route.get("operation") or message.route_key
    await context.session.flush()
