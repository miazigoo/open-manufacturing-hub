from __future__ import annotations

from typing import Any

from app.connectors.models import ConnectorInstance


def connector_profile_kinds(connector: ConnectorInstance) -> list[str]:
    config = connector.config_json or {}
    omh = config.get("omh") if isinstance(config.get("omh"), dict) else {}
    explicit = omh.get("connection_profile_kind")
    if explicit in {"onec_odata", "onec_http_service", "rest_api", "printer", "smb_share", "local_directory", "training_mock"}:
        return [str(explicit)]

    if connector.connector_type == "onec":
        kinds: list[str] = []
        odata = config.get("odata") if isinstance(config.get("odata"), dict) else {}
        if config.get("base_url") and odata.get("enabled", True) is not False:
            kinds.append("onec_odata")
        if _has_onec_http_service(config):
            kinds.append("onec_http_service")
        return kinds

    if connector.connector_type == "rest":
        if _is_training_printer(config, connector.name):
            return ["printer"]
        if _is_training_onec_http(config, connector.name):
            return ["onec_http_service"]
        return ["rest_api"]
    if connector.connector_type == "zpl_printer":
        return ["printer"]
    if connector.connector_type == "smb_share":
        return ["smb_share"]
    if connector.connector_type == "local_directory":
        return ["local_directory"]
    return []


def is_training_connector(connector: ConnectorInstance) -> bool:
    config = connector.config_json or {}
    omh = config.get("omh") if isinstance(config.get("omh"), dict) else {}
    tags = omh.get("tags") if isinstance(omh.get("tags"), list) else []
    if connector.name.startswith("Training ") or "training" in {str(tag).lower() for tag in tags}:
        return True
    return _has_training_marker(config)


def _has_onec_http_service(config: dict[str, Any]) -> bool:
    if config.get("http_service_base_url"):
        return True
    http_services = config.get("http_services")
    if isinstance(http_services, dict) and http_services.get("enabled", True) is not False:
        return True
    operations = config.get("operations")
    if isinstance(operations, dict):
        return any(isinstance(operation, dict) and operation.get("type") == "http_service" for operation in operations.values())
    return False


def _is_training_printer(config: dict[str, Any], name: str) -> bool:
    return bool(config.get("training_mock_printer")) or (name.startswith("Training ") and "printer" in name.lower())


def _is_training_onec_http(config: dict[str, Any], name: str) -> bool:
    if config.get("training_mock_onec_writeback") or config.get("training_mock_onec_shipment_facts"):
        return True
    return name.startswith("Training ") and "1c http" in name.lower()


def _has_training_marker(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).startswith("training_mock") or _has_training_marker(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_training_marker(item) for item in value)
    return False
