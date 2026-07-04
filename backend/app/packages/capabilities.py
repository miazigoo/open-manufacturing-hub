from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.packages.manifest import PackageManifest

CapabilityType = Literal[
    "connector",
    "router",
    "frontend_page",
    "navigation_item",
    "execution_step",
    "resolver",
    "transform",
    "business_object",
    "operation_template",
    "scenario_preset",
    "mapping_preset",
    "test_case",
    "docs",
    "health_check",
    "production_check",
    "flow_builder_block",
]

CAPABILITY_TYPES: tuple[str, ...] = (
    "connector",
    "router",
    "frontend_page",
    "navigation_item",
    "execution_step",
    "resolver",
    "transform",
    "business_object",
    "operation_template",
    "scenario_preset",
    "mapping_preset",
    "test_case",
    "docs",
    "health_check",
    "production_check",
    "flow_builder_block",
)

CONNECTOR_CLASS_CODES = {
    "OneCConnector": "onec",
    "ZPLPrinterConnector": "zpl_printer",
    "RESTConnector": "rest",
    "WebhookConnector": "webhook",
}

FLOW_BLOCKS_BY_PACKAGE = {
    "omh-package-onec": ["odata_query", "odata_lookup", "call_1c_http_service", "xml_extract"],
    "omh-package-printer": ["call_printer"],
}

HEALTH_CHECKS_BY_PACKAGE = {
    "omh-package-printer": ["printer_connection"],
}

PRODUCTION_CHECKS_BY_PACKAGE = {
    "omh-package-auth": ["auth_bootstrap", "session_cookie"],
    "omh-package-secrets": ["secrets_key"],
}


class PackageCapability(BaseModel):
    type: CapabilityType
    code: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def capabilities_for_manifest(manifest: PackageManifest) -> list[PackageCapability]:
    capabilities: list[PackageCapability] = []

    for router in manifest.backend.routers:
        capabilities.append(PackageCapability(type="router", code=_router_code(router), metadata={"ref": router}))

    for connector in manifest.backend.connectors:
        capabilities.append(PackageCapability(type="connector", code=_connector_code(connector), metadata={"ref": connector}))

    for step in manifest.backend.steps:
        capabilities.append(PackageCapability(type="execution_step", code=_class_code(step), metadata={"ref": step}))

    for page in manifest.frontend.pages:
        capabilities.append(PackageCapability(type="frontend_page", code=page.route, metadata=page.model_dump(mode="json")))

    for item in manifest.frontend.navigation:
        capabilities.append(PackageCapability(type="navigation_item", code=item.route, metadata=item.model_dump(mode="json")))

    if manifest.docs.readme:
        capabilities.append(PackageCapability(type="docs", code="readme", metadata={"ref": manifest.docs.readme}))
    if manifest.docs.quick_start:
        capabilities.append(PackageCapability(type="docs", code="quick_start", metadata={"ref": manifest.docs.quick_start}))

    for preset_type, ref in manifest.presets.items():
        capability_type = _preset_type(preset_type)
        capabilities.append(PackageCapability(type=capability_type, code=str(preset_type), metadata={"ref": ref}))

    for code in FLOW_BLOCKS_BY_PACKAGE.get(manifest.package_id, []):
        capabilities.append(PackageCapability(type="flow_builder_block", code=code, metadata={"source": "builtin"}))

    for code in HEALTH_CHECKS_BY_PACKAGE.get(manifest.package_id, []):
        capabilities.append(PackageCapability(type="health_check", code=code, metadata={"source": "builtin"}))

    for code in PRODUCTION_CHECKS_BY_PACKAGE.get(manifest.package_id, []):
        capabilities.append(PackageCapability(type="production_check", code=code, metadata={"source": "builtin"}))

    return _dedupe(capabilities)


def _router_code(ref: str) -> str:
    module = ref.split(":", 1)[0]
    return module.rsplit(".", 2)[-2] if module.endswith(".router") and "." in module else module.rsplit(".", 1)[-1]


def _connector_code(ref: str) -> str:
    class_name = ref.split(":", 1)[-1]
    return CONNECTOR_CLASS_CODES.get(class_name, _snake(class_name.removesuffix("Connector")))


def _class_code(ref: str) -> str:
    class_name = ref.split(":", 1)[-1]
    return _snake(class_name)


def _preset_type(preset_type: str) -> CapabilityType:
    lowered = preset_type.lower()
    if "mapping" in lowered:
        return "mapping_preset"
    if "test" in lowered:
        return "test_case"
    if "flow" in lowered:
        return "flow_builder_block"
    return "scenario_preset"


def _snake(value: str) -> str:
    result = []
    for index, char in enumerate(value):
        if char.isupper() and index and not value[index - 1].isupper():
            result.append("_")
        result.append(char.lower())
    return "".join(result).strip("_")


def _dedupe(items: list[PackageCapability]) -> list[PackageCapability]:
    seen: set[tuple[str, str]] = set()
    result: list[PackageCapability] = []
    for item in items:
        key = (item.type, item.code)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
