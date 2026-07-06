from __future__ import annotations

from dataclasses import dataclass

from app.execution.exceptions import StepNotFoundError
from app.execution.step import ExecutionStep


@dataclass(frozen=True, slots=True)
class StepMetadata:
    name: str
    display_name: str


class StepRegistry:
    def __init__(self) -> None:
        self._steps: dict[str, ExecutionStep] = {}

    def register(self, step: ExecutionStep, *aliases: str) -> None:
        self._steps[step.name] = step
        for alias in aliases:
            self._steps[alias] = step

    def get(self, name: str) -> ExecutionStep:
        try:
            return self._steps[name]
        except KeyError as exc:
            raise StepNotFoundError(f"Execution step {name} not found") from exc

    def list(self) -> list[StepMetadata]:
        seen: set[int] = set()
        items: list[StepMetadata] = []
        for name, step in self._steps.items():
            if id(step) in seen:
                continue
            seen.add(id(step))
            items.append(StepMetadata(name=name, display_name=step.display_name))
        return sorted(items, key=lambda item: item.name)


registry = StepRegistry()


def register_builtin_steps() -> None:
    from app.execution.steps.build_xml import BuildXMLStep
    from app.execution.steps.call_connector import CallConnectorStep
    from app.execution.steps.call_print_operation import CallPrintOperationStep
    from app.execution.steps.create_incident import CreateIncidentStep
    from app.execution.steps.apply_transforms import ApplyTransformsStep
    from app.execution.steps.evaluate_rules import EvaluateRulesStep
    from app.execution.steps.flow_builder_steps import FlowBuildJsonStep, FlowCallEndpointStep, FlowConditionStep, FlowODataQueryStep, FlowReadVariableStep, FlowReturnResponseStep
    from app.execution.steps.handle_response import HandleResponseStep
    from app.execution.steps.maintenance_guard import MaintenanceGuardStep
    from app.execution.steps.map_payload import MapPayloadStep
    from app.execution.steps.normalize import NormalizePayloadStep
    from app.execution.steps.odata_lookup import ODataLookupStep
    from app.execution.steps.parse_xml import ParseXMLStep
    from app.execution.steps.receive import ReceiveEventStep
    from app.execution.steps.resolve_object import ResolveObjectStep
    from app.execution.steps.route_by_rule import RouteByRuleStep
    from app.execution.steps.save_integration_message import SaveIntegrationMessageStep
    from app.execution.steps.send_notifications import SendNotificationsStep
    from app.execution.steps.validate import ValidatePayloadStep
    from app.xml_toolkit.steps import RawXmlForwardStep, XmlExtractStep

    registry.register(ReceiveEventStep())
    registry.register(SaveIntegrationMessageStep())
    registry.register(ParseXMLStep())
    registry.register(BuildXMLStep())
    registry.register(FlowReadVariableStep())
    registry.register(FlowODataQueryStep())
    registry.register(FlowBuildJsonStep())
    registry.register(FlowConditionStep())
    registry.register(FlowCallEndpointStep())
    registry.register(FlowReturnResponseStep())
    registry.register(XmlExtractStep())
    registry.register(RawXmlForwardStep())
    registry.register(ApplyTransformsStep())
    registry.register(EvaluateRulesStep())
    registry.register(ResolveObjectStep())
    registry.register(ODataLookupStep())
    registry.register(RouteByRuleStep())
    registry.register(MaintenanceGuardStep())
    registry.register(NormalizePayloadStep(), "map_to_canonical")
    registry.register(ValidatePayloadStep())
    registry.register(MapPayloadStep(), "map_to_target")
    registry.register(CallConnectorStep(), "send_to_target")
    registry.register(CallPrintOperationStep())
    registry.register(HandleResponseStep())
    registry.register(CreateIncidentStep())
    registry.register(SendNotificationsStep())


register_builtin_steps()
