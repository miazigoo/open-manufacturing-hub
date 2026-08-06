from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules.models import BusinessRuleSet
from app.connectors.models import ConnectorInstance
from app.enterprise_runtime.models import BusinessRuleDefinition, CanonicalBusinessObject, ResolverDefinition
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute, ODataLookupTemplate
from app.integration_flows.models import IntegrationFlow
from app.maintenance.models import MaintenanceWindow
from app.mappings.models import MappingDefinition, MappingVersion
from app.notifications.models import NotificationRule
from app.operation_templates.models import OperationTemplate
from app.packages.models import InstalledPackage, PackageRuntimeCapability
from app.printing.models import PrintPrinter
from app.resolvers.models import ResolverDefinitionV2
from app.secrets.redaction import is_secret_ref
from app.test_console.models import SavedTestCase
from app.workflows.models import Workflow

SECRET_FIELD_MARKERS = ("password", "token", "secret", "authorization", "api_key", "apikey", "private_key")

EXPORT_MODELS: dict[str, type] = {
    "packages": InstalledPackage,
    "package_runtime_capabilities": PackageRuntimeCapability,
    "connectors": ConnectorInstance,
    "integration_endpoints": IntegrationEndpoint,
    "integration_routes": IntegrationRoute,
    "integration_flows": IntegrationFlow,
    "workflows": Workflow,
    "mappings": MappingDefinition,
    "mapping_versions": MappingVersion,
    "operation_templates": OperationTemplate,
    "odata_lookup_templates": ODataLookupTemplate,
    "resolvers": ResolverDefinitionV2,
    "runtime_resolvers": ResolverDefinition,
    "canonical_objects": CanonicalBusinessObject,
    "business_rules": BusinessRuleSet,
    "runtime_business_rules": BusinessRuleDefinition,
    "saved_test_cases": SavedTestCase,
    "notification_rules": NotificationRule,
    "maintenance_windows": MaintenanceWindow,
    "printer_configs": PrintPrinter,
}

IMPORT_KEYS: dict[str, str] = {
    "packages": "package_id",
    "package_runtime_capabilities": "id",
    "connectors": "name",
    "integration_endpoints": "slug",
    "integration_routes": "name",
    "integration_flows": "slug",
    "workflows": "name",
    "mappings": "name",
    "mapping_versions": "id",
    "operation_templates": "name",
    "odata_lookup_templates": "name",
    "resolvers": "name",
    "runtime_resolvers": "name",
    "canonical_objects": "name",
    "business_rules": "name",
    "runtime_business_rules": "name",
    "saved_test_cases": "name",
    "notification_rules": "name",
    "maintenance_windows": "id",
    "printer_configs": "name",
}


def export_warning() -> str:
    return "This export does not contain secret values. Secret references are preserved; raw passwords/tokens are masked."


async def export_objects(session: AsyncSession, *, secrets_policy: str = "masked") -> dict[str, Any]:
    objects: dict[str, Any] = {}
    for name, model in EXPORT_MODELS.items():
        result = await session.execute(select(model))
        objects[name] = [_mask_secrets(_row_to_dict(item), secrets_policy) for item in result.scalars().all()]
    return objects


def preview_import(export: dict[str, Any], mode: str, existing: dict[str, set[str]]) -> dict[str, Any]:
    objects = export.get("objects") if isinstance(export.get("objects"), dict) else {}
    will_create: dict[str, int] = {}
    will_update: dict[str, int] = {}
    conflicts: list[dict[str, Any]] = []
    warnings = _import_warnings(export)
    valid = export.get("omh_export_version") == 1 and isinstance(objects, dict)
    for name, rows in objects.items():
        if name not in IMPORT_KEYS or not isinstance(rows, list):
            continue
        key = IMPORT_KEYS[name]
        for row in rows:
            if not isinstance(row, dict):
                continue
            identity = str(row.get(key) or row.get("id") or "")
            exists = identity in existing.get(name, set())
            if exists and mode == "create_only":
                conflicts.append({"type": name, "name": identity, "reason": "already exists"})
            elif exists:
                will_update[name] = will_update.get(name, 0) + 1
            else:
                will_create[name] = will_create.get(name, 0) + 1
    return {"valid": valid, "mode": mode, "will_create": will_create, "will_update": will_update, "conflicts": conflicts, "warnings": warnings}


async def existing_identities(session: AsyncSession) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for name, model in EXPORT_MODELS.items():
        key = IMPORT_KEYS.get(name)
        if not key:
            continue
        rows = (await session.execute(select(model))).scalars().all()
        result[name] = {str(getattr(row, key, None) or getattr(row, "id", "")) for row in rows}
    return result


async def apply_import(session: AsyncSession, export: dict[str, Any], mode: str) -> dict[str, Any]:
    existing = await existing_identities(session)
    preview = preview_import(export, mode, existing)
    if not preview["valid"]:
        return {**preview, "applied": False}
    if mode == "create_only" and preview["conflicts"]:
        return {**preview, "applied": False}
    objects = export.get("objects") if isinstance(export.get("objects"), dict) else {}
    for name, rows in objects.items():
        model = EXPORT_MODELS.get(name)
        key = IMPORT_KEYS.get(name)
        if model is None or key is None or not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            identity = str(row.get(key) or row.get("id") or "")
            existing_row = None
            if identity:
                identity_value = _coerce_identity(model, key, row.get(key))
                existing_row = (await session.execute(select(model).where(getattr(model, key) == identity_value))).scalar_one_or_none()
            if existing_row is not None and mode == "create_only":
                continue
            values = _coerce_for_model(model, _drop_runtime_columns(row))
            if existing_row is None:
                session.add(model(**values))
            else:
                for column, value in values.items():
                    if column != "id":
                        setattr(existing_row, column, value)
    await session.flush()
    return {**preview, "applied": True}


def _row_to_dict(item: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in item.__table__.columns:
        result[column.name] = _jsonable(getattr(item, column.name))
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _mask_secrets(value: Any, policy: str) -> Any:
    if is_secret_ref(value):
        return value
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(key):
                masked[key] = _mask_secret_item(item, policy)
            else:
                masked[key] = _mask_secrets(item, policy)
        return masked
    if isinstance(value, list):
        return [_mask_secrets(item, policy) for item in value]
    return value


def _mask_secret_item(value: Any, policy: str) -> Any:
    if is_secret_ref(value):
        return value
    if isinstance(value, dict):
        return {str(key): _mask_secret_item(item, policy) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_secret_item(item, policy) for item in value]
    return "***REFERENCE_ONLY***" if policy == "references_only" else "***MASKED***"


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SECRET_FIELD_MARKERS)


def _drop_runtime_columns(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"created_at", "updated_at", "last_health_at", "last_run_event_id", "last_run_status", "last_triggered_at"}}


def _coerce_for_model(model: type, row: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for column in model.__table__.columns:
        if column.name not in row:
            continue
        raw = row[column.name]
        if isinstance(raw, str) and raw in {"***MASKED***", "***REFERENCE_ONLY***"}:
            continue
        values[column.name] = _coerce_value(_python_type(column), _strip_masked(raw))
    return values


def _python_type(column: Any) -> Any:
    try:
        return column.type.python_type
    except Exception:
        return None


def _strip_masked(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_masked(item) for key, item in value.items() if not _is_masked_value(item)}
    if isinstance(value, list):
        return [_strip_masked(item) for item in value]
    return value


def _is_masked_value(value: Any) -> bool:
    return isinstance(value, str) and value in {"***MASKED***", "***REFERENCE_ONLY***"}


def _coerce_value(python_type: Any, value: Any) -> Any:
    if value is None:
        return None
    try:
        if python_type is UUID and isinstance(value, str):
            return UUID(value)
        if python_type is datetime and isinstance(value, str):
            return datetime.fromisoformat(value)
    except Exception:
        return value
    return value


def _coerce_identity(model: type, key: str, value: Any) -> Any:
    """Coerce an exported identity value back to the model column type so the
    lookup works on both postgres and sqlite (string UUIDs vs UUID columns)."""
    if key not in model.__table__.columns:
        return value
    try:
        return _coerce_value(_python_type(model.__table__.columns[key]), value)
    except Exception:
        return value


def _import_warnings(export: dict[str, Any]) -> list[str]:
    warnings = list(export.get("warnings") or []) if isinstance(export.get("warnings"), list) else []
    if export.get("secrets_policy") in {"masked", "references_only"}:
        warnings.append(export_warning())
    objects = export.get("objects") if isinstance(export.get("objects"), dict) else {}
    package_ids = {str(row.get("package_id")) for row in objects.get("packages", []) if isinstance(row, dict) and row.get("package_id")}
    for name, rows in objects.items():
        if name in {"packages", "package_runtime_capabilities"} or not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            package_id = row.get("package_id") or row.get("owner_package_id")
            if package_id and str(package_id) not in package_ids:
                warnings.append(f"Object group {name} references package {package_id}, but that package is not included in export.")
    return sorted(set(str(item) for item in warnings))
