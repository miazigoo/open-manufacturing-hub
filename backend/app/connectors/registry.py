from app.sdk.connector import Connector
from app.sdk.exceptions import ConnectorNotFoundError
from app.sdk.types import ConnectorMetadata


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        self._connectors[connector.connector_type] = connector

    def get(self, connector_type: str) -> Connector:
        try:
            return self._connectors[connector_type]
        except KeyError as exc:
            raise ConnectorNotFoundError(f"Connector type {connector_type} not found") from exc

    def list(self) -> list[ConnectorMetadata]:
        return [
            ConnectorMetadata(connector_type=connector.connector_type, display_name=connector.display_name, direction=connector.direction)
            for connector in self._connectors.values()
        ]


registry = ConnectorRegistry()


def register_builtin_connectors() -> None:
    from app.connectors.builtin.mock_erp_connector import MockERPConnector
    from app.connectors.builtin.mock_wms_connector import MockWMSConnector
    from app.connectors.builtin.onec_connector import OneCConnector
    from app.connectors.builtin.rest_connector import RESTConnector
    from app.connectors.builtin.webhook_connector import WebhookConnector
    from app.connectors.builtin.zpl_printer_connector import ZPLPrinterConnector

    for connector in [RESTConnector(), WebhookConnector(), MockERPConnector(), MockWMSConnector(), OneCConnector(), ZPLPrinterConnector()]:
        registry.register(connector)


register_builtin_connectors()
