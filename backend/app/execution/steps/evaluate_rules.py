from __future__ import annotations

from typing import Any

from app.business_rules import repository as rule_repository
from app.business_rules.engine import engine as rules_engine
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult


class EvaluateRulesStep:
    name = "evaluate_rules"
    display_name = "Evaluate Business Rules"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = dict((context.current_step.step_config_json or {}).get("config") or {})
        try:
            rule_set = await _rule_set(context, config)
            result = rules_engine.evaluate(rule_set, {"payload": context.variables.get("payload") or {}, "variables": context.variables})
        except Exception as exc:
            return StepResult.failed("RULE_EVALUATION_FAILED", str(exc) or exc.__class__.__name__, artifacts=[ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "business_rules_error.json", {"error_code": "RULE_EVALUATION_FAILED", "error_message": str(exc)})])
        variables_update: dict[str, Any] = {"payload": result.payload, **result.variables}
        if result.target_system is not None:
            variables_update["target_system"] = result.target_system
        if result.operation is not None:
            variables_update["operation"] = result.operation
        if result.route is not None:
            variables_update["route"] = result.route
        variables_update["skip_steps"] = result.skip_steps
        steps = dict(context.variables.get("steps") or {})
        steps[str(config.get("step_id") or "evaluate_rules")] = result.model_dump(mode="json")
        variables_update["steps"] = steps
        artifact = ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "business_rules_trace.json", result.trace | {"matched_rules": result.matched_rules, "actions_applied": result.actions_applied, "status": result.status})
        if result.status == "failed":
            return StepResult.failed(result.error_code or "BUSINESS_RULE_FAILED", result.error_message or "Business rule failed", artifacts=[artifact], variables_update=variables_update, human_title="Business rule failed", human_summary=result.error_message, hint="Check rule set conditions and inbound payload.")
        if result.status == "retry":
            return StepResult.retry(result.error_message or "Retry requested by business rule", artifacts=[artifact], metadata={"error_code": result.error_code})
        return StepResult.success(f"Business rules evaluated: {len(result.matched_rules)} matched", artifacts=[artifact], variables_update=variables_update, metadata={"matched_rules": result.matched_rules, "status": result.status})


async def _rule_set(context: PipelineContext, config: dict[str, Any]) -> dict[str, Any]:
    if isinstance(config.get("rules_json"), dict):
        return config["rules_json"]
    if isinstance(config.get("rules"), list):
        return {"mode": config.get("mode") or "first_match", "rules": config["rules"], "name": config.get("rule_set") or config.get("display_name")}
    name = config.get("rule_set") or config.get("rule_set_name")
    if not name:
        raise ValueError("RULE_SET_NOT_FOUND: evaluate_rules requires rule_set or inline rules")
    item = await rule_repository.get_by_name_or_404(context.session, str(name))
    if not item.enabled:
        raise ValueError(f"RULE_SET_DISABLED: {name}")
    return {**item.rules_json, "name": item.name}
