from typing import Protocol

from app.core.enums import ConnectorDirection
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class Connector(Protocol):
    connector_type: str
    display_name: str
    direction: ConnectorDirection

    async def validate_config(self, config: dict) -> ConnectorConfigValidationResult:
        ...

    async def healthcheck(self, config: dict) -> ConnectorHealthResult:
        ...

    async def send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        ...

    async def dry_run_send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        ...

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        ...
