from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.change_sets import diff, repository
from app.change_sets.models import ChangeSet, ChangeSetItem, ChangeSetOperation, ChangeSetStatus
from app.change_sets.schemas import ChangeSetFromDraftsRequest, ChangeSetImportApplyRequest, ChangeSetImportPreviewRequest, ChangeSetImportPreview, ConfigObjectRef
from app.config_versions import repository as config_repository
from app.config_versions import service as config_service
from app.config_versions.models import ConfigVersionStatus
from app.config_versions.schemas import ConfigDraftRequest, ConfigPublishRequest
from app.core.database import new_uuid
from app.core.errors import BadRequestError, NotFoundError
from app.environments import repository as env_repository
from app.environments import service as env_service
from app.environments.models import EnvironmentVariable
from app.environments.schemas import EnvironmentVariableCreate
from app.packages.models import InstalledPackage
from app.secrets import repository as secrets_repository


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def list_change_sets(session: AsyncSession) -> list[ChangeSet]:
    return await repository.list_change_sets(session)


async def get_change_set_or_404(session: AsyncSession, change_set_id: UUID) -> ChangeSet:
    item = await repository.get_change_set(session, change_set_id)
    if item is None:
        raise NotFoundError("Change set not found")
    return item


async def create_from_drafts(session: AsyncSession, request: ChangeSetFromDraftsRequest, *, http_request: Request | None = None) -> ChangeSet:
    current = await env_repository.current_environment(session)
    actor = await _actor_name(session, http_request)
    change_set = ChangeSet(name=request.name, description=request.description, source_environment=current.code if current else None, status=ChangeSetStatus.DRAFT, created_by=actor, metadata_json={"include_dependencies": request.include_dependencies}, items=[])
    session.add(change_set)
    await session.flush()
    for ref in request.object_refs:
        version = await _selected_version(session, ref)
        dependencies = await _dependencies_for_config(ref.object_type, version.config_json, version.metadata_json or {}, include=request.include_dependencies)
        change_set.items.append(ChangeSetItem(object_type=ref.object_type, object_id=str(ref.object_id), object_name=version.object_name, operation=ChangeSetOperation.UPDATE, config_json=version.config_json, version_id=version.id, package_id=_primary_package(dependencies), dependencies_json=dependencies))
    await session.flush()
    await audit_service.record_action(session, request=http_request, action="change_set.created", category="change_sets", object_type="change_set", object_id=change_set.id, object_name=change_set.name, summary=f"Change set created: {change_set.name}", details={"items": len(request.object_refs), "source_environment": change_set.source_environment})
    return change_set


async def export_change_set(session: AsyncSession, change_set_id: UUID, *, http_request: Request | None = None) -> dict[str, Any]:
    change_set = await get_change_set_or_404(session, change_set_id)
    change_set.status = ChangeSetStatus.EXPORTED
    change_set.exported_at = utcnow()
    payload = _export_payload(change_set)
    await session.flush()
    await audit_service.record_action(session, request=http_request, action="change_set.exported", category="change_sets", object_type="change_set", object_id=change_set.id, object_name=change_set.name, summary=f"Change set exported: {change_set.name}", details={"items": len(change_set.items), "required_packages": payload["required_packages"]})
    return payload


async def import_preview(session: AsyncSession, request: ChangeSetImportPreviewRequest, *, http_request: Request | None = None, persist: bool = True) -> dict[str, Any]:
    payload = _coerce_export(request.change_set)
    mapping = request.mapping
    target = await env_repository.current_environment(session)
    preview = await _preview_payload(session, payload, mapping.model_dump(), target_code=target.code if target else None)
    change_set_id: UUID | None = None
    if persist:
        imported = _persist_imported_change_set(payload, target.code if target else None, ChangeSetStatus.IMPORT_PREVIEWED, preview)
        session.add(imported)
        await session.flush()
        change_set_id = imported.id
        preview["change_set_id"] = change_set_id
        await audit_service.record_action(session, request=http_request, action="change_set.import_previewed", category="change_sets", object_type="change_set", object_id=imported.id, object_name=imported.name, summary=f"Change set import previewed: {imported.name}", details=_preview_audit(preview))
    return preview


async def import_apply(session: AsyncSession, request: ChangeSetImportApplyRequest, *, http_request: Request | None = None) -> dict[str, Any]:
    payload = _coerce_export(request.change_set)
    mapping = request.mapping.model_dump()
    target = await env_repository.current_environment(session)
    preview = await _preview_payload(session, payload, mapping, target_code=target.code if target else None)
    if not preview["valid"]:
        failed = _persist_imported_change_set(payload, target.code if target else None, ChangeSetStatus.FAILED, preview)
        session.add(failed)
        await session.flush()
        await audit_service.record_action(session, request=http_request, action="change_set.apply_failed", category="change_sets", object_type="change_set", object_id=failed.id, object_name=failed.name, summary=f"Change set apply blocked: {failed.name}", details=_preview_audit(preview))
        raise BadRequestError("CHANGE_SET_IMPORT_HAS_UNRESOLVED_ISSUES")
    applied = _persist_imported_change_set(payload, target.code if target else None, ChangeSetStatus.APPLIED, preview)
    session.add(applied)
    await session.flush()
    await _upsert_environment_variables(session, mapping.get("environment_variables") or {}, target, http_request=http_request)
    applied_items: list[dict[str, Any]] = []
    resolver = env_service.EnvironmentResolver(session, target)
    for item in payload["items"]:
        if item.get("operation") == ChangeSetOperation.DELETE_DISABLED_IN_MVP.value:
            continue
        raw_config = _apply_import_mappings(item.get("config_json") or {}, mapping)
        runtime_config = await resolver.resolve_config(raw_config) if target else raw_config
        object_type = str(item.get("object_type"))
        existing = await _existing_object(session, object_type, item)
        object_id = await _ensure_runtime_object(session, object_type, item, runtime_config, existing)
        draft = await config_service.create_or_update_draft(session, object_type, object_id, ConfigDraftRequest(config_json=runtime_config, metadata_json={"change_set_id": str(applied.id), "source_change_set": payload.get("name"), "source_object_id": item.get("object_id"), "source_version_id": item.get("version_id")}, comment=f"Imported from change set {payload.get('name')}"), http_request=http_request)
        published = await config_service.publish(session, object_type, object_id, ConfigPublishRequest(version_id=draft.id, comment=f"Promoted from change set {payload.get('name')}", confirm_untested=True), http_request=http_request)
        applied_items.append({"object_type": object_type, "object_id": str(object_id), "version_id": str(published.id), "version_number": published.version_number})
        session.add(ChangeSetItem(change_set_id=applied.id, object_type=object_type, object_id=str(object_id), object_name=item.get("object_name"), operation=ChangeSetOperation(str(item.get("operation") or ChangeSetOperation.UPDATE.value)), config_json=runtime_config, version_id=published.id, package_id=item.get("package_id"), dependencies_json=item.get("dependencies_json") or {}))
    applied.applied_at = utcnow()
    applied.metadata_json = {**(applied.metadata_json or {}), "preview": _preview_audit(preview), "applied_items": applied_items}
    smoke = await run_smoke_tests(session, applied.id, http_request=http_request) if mapping.get("run_smoke_tests") else None
    await session.flush()
    await audit_service.record_action(session, request=http_request, action="change_set.applied", category="change_sets", object_type="change_set", object_id=applied.id, object_name=applied.name, summary=f"Change set applied: {applied.name}", details={"applied_items": applied_items, "target_environment": applied.target_environment})
    return {**preview, "valid": True, "applied": True, "applied_change_set_id": applied.id, "applied_items": applied_items, "smoke": smoke}


async def run_smoke_tests(session: AsyncSession, change_set_id: UUID, *, http_request: Request | None = None) -> dict[str, Any]:
    change_set = await get_change_set_or_404(session, change_set_id)
    from app.test_console.models import SavedTestCase
    from app.test_console import service as test_service
    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    for item in change_set.items:
        if item.object_type != "saved_test_case":
            continue
        name = item.config_json.get("name") or item.object_name
        test_case = None
        if item.object_id:
            try:
                test_case = await session.get(SavedTestCase, UUID(item.object_id))
            except Exception:
                test_case = None
        if test_case is None and name:
            test_case = (await session.execute(select(SavedTestCase).where(SavedTestCase.name == str(name)).limit(1))).scalar_one_or_none()
        if test_case is None:
            failed += 1
            results.append({"test_case": name or item.object_id, "status": "failed", "error": "Test case not found"})
            continue
        try:
            response = await test_service.run_test_case(session, test_case.id, dry_run=True)
            status = "passed" if response.get("success") else "failed"
            passed += 1 if status == "passed" else 0
            failed += 1 if status == "failed" else 0
            results.append({"test_case": test_case.name, "status": status, "timeline_url": response.get("timeline_url"), "event_id": response.get("event_id")})
        except Exception as exc:
            failed += 1
            results.append({"test_case": test_case.name, "status": "failed", "error": str(exc)})
    payload = {"passed": passed, "failed": failed, "results": results}
    change_set.metadata_json = {**(change_set.metadata_json or {}), "last_smoke": payload, "last_smoke_at": utcnow().isoformat()}
    if failed:
        change_set.status = ChangeSetStatus.FAILED
    await session.flush()
    await audit_service.record_action(session, request=http_request, action="change_set.smoke_test_run", category="change_sets", object_type="change_set", object_id=change_set.id, object_name=change_set.name, summary=f"Change set smoke tests run: {passed} passed, {failed} failed", details=payload)
    return payload


async def _selected_version(session: AsyncSession, ref: ConfigObjectRef):
    await config_service.ensure_active_version(session, ref.object_type, ref.object_id)
    draft = await config_repository.get_draft(session, ref.object_type, ref.object_id)
    if draft is not None:
        return draft
    active = await config_repository.get_active(session, ref.object_type, ref.object_id)
    if active is None:
        raise NotFoundError(f"No active or draft config for {ref.object_type}/{ref.object_id}")
    return active


async def _dependencies_for_config(object_type: str, config: dict[str, Any], metadata: dict[str, Any], *, include: bool) -> dict[str, Any]:
    packages: list[dict[str, str]] = []
    if include:
        text = str(config).lower()
        if object_type in {"odata_lookup_template"} or "odata" in text or "1c" in text or "onec" in text:
            packages.append({"package_id": "omh-package-onec", "version": ">=0.1.0"})
        if "printer" in text or "zebra" in text or object_type == "printer_config":
            packages.append({"package_id": "omh-package-printer", "version": ">=0.1.0"})
    return {"identity": metadata, "required_packages": packages, "secret_refs": diff.collect_secret_refs(config), "environment_refs": diff.collect_env_refs(config)}


def _primary_package(dependencies: dict[str, Any]) -> str | None:
    packages = dependencies.get("required_packages") if isinstance(dependencies, dict) else None
    if isinstance(packages, list) and packages:
        return str(packages[0].get("package_id"))
    return None


def _export_payload(change_set: ChangeSet) -> dict[str, Any]:
    required: dict[str, dict[str, Any]] = {}
    items: list[dict[str, Any]] = []
    for item in change_set.items:
        deps = item.dependencies_json or {}
        for package in deps.get("required_packages") or []:
            if isinstance(package, dict) and package.get("package_id"):
                required[str(package["package_id"])] = package
        if item.package_id:
            required.setdefault(item.package_id, {"package_id": item.package_id, "version": ">=0.1.0"})
        items.append({"object_type": item.object_type, "object_id": item.object_id, "object_name": item.object_name, "operation": item.operation.value, "config_json": diff.redact_export(item.config_json), "version_id": str(item.version_id) if item.version_id else None, "package_id": item.package_id, "dependencies_json": item.dependencies_json or {}})
    return {"omh_change_set_version": 1, "name": change_set.name, "description": change_set.description, "created_at": change_set.created_at.isoformat(), "source_environment": change_set.source_environment, "required_packages": list(required.values()), "items": items, "secrets_policy": "references_only", "warnings": ["Secret values are never exported. Map or create target secrets before apply.", "Delete operations are warnings only in this MVP."]}


def _coerce_export(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("omh_change_set_version") != 1 or not isinstance(payload.get("items"), list):
        raise BadRequestError("INVALID_CHANGE_SET_EXPORT")
    return payload


async def _preview_payload(session: AsyncSession, payload: dict[str, Any], mapping: dict[str, Any], *, target_code: str | None) -> dict[str, Any]:
    will_create: list[dict[str, Any]] = []
    will_update: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    missing_packages: list[dict[str, Any]] = []
    missing_secrets: list[dict[str, Any]] = []
    missing_environment_variables: list[dict[str, Any]] = []
    warnings = list(payload.get("warnings") or [])
    installed = {item.package_id: item for item in (await session.execute(select(InstalledPackage))).scalars().all()}
    for package in payload.get("required_packages") or []:
        package_id = str(package.get("package_id")) if isinstance(package, dict) else str(package)
        installed_package = installed.get(package_id)
        if installed_package is None or not installed_package.enabled:
            missing_packages.append({"package_id": package_id, "reason": "not installed or disabled"})
    target_env = await env_repository.current_environment(session)
    existing_env_keys = {item.key for item in await env_repository.variables_for_environment(session, target_env.id)} if target_env else set()
    provided_env = set((mapping.get("environment_variables") or {}).keys())
    for item in payload["items"]:
        operation = str(item.get("operation") or "update")
        object_type = str(item.get("object_type"))
        if operation == ChangeSetOperation.DELETE_DISABLED_IN_MVP.value:
            warnings.append(f"Delete skipped for {object_type}/{item.get('object_name') or item.get('object_id')}: destructive delete is disabled in MVP.")
            continue
        mapped_config = _apply_import_mappings(item.get("config_json") or {}, mapping)
        for ref in diff.collect_secret_refs(mapped_config):
            secret = await secrets_repository.get_by_name(session, ref["name"])
            if secret is None:
                missing_secrets.append(ref)
        for ref in diff.collect_env_refs(mapped_config):
            if ref["key"] not in existing_env_keys and ref["key"] not in provided_env:
                missing_environment_variables.append(ref)
        existing = await _existing_object(session, object_type, item)
        row = {"object_type": object_type, "object_id": item.get("object_id"), "object_name": item.get("object_name"), "operation": operation, "target_environment": target_code}
        if existing is None:
            will_create.append(row)
        else:
            row["target_object_id"] = str(existing.id)
            if item.get("object_id") and str(existing.id) != str(item.get("object_id")):
                conflicts.append({**row, "reason": "same natural key exists with different ID"})
            will_update.append(row)
    valid = not (missing_packages or missing_secrets or missing_environment_variables or (conflicts and not mapping.get("allow_conflicts")))
    return {"valid": valid, "change_set_id": None, "will_create": will_create, "will_update": will_update, "conflicts": conflicts, "missing_packages": missing_packages, "missing_secrets": missing_secrets, "missing_environment_variables": missing_environment_variables, "warnings": sorted(set(warnings))}


def _persist_imported_change_set(payload: dict[str, Any], target_environment: str | None, status: ChangeSetStatus, preview: dict[str, Any]) -> ChangeSet:
    return ChangeSet(name=str(payload.get("name") or "Imported change set"), description=payload.get("description"), source_environment=payload.get("source_environment"), target_environment=target_environment, status=status, metadata_json={"import_preview": _preview_audit(preview), "source_created_at": payload.get("created_at")})


def _preview_audit(preview: dict[str, Any]) -> dict[str, Any]:
    return {key: preview.get(key) for key in ["valid", "will_create", "will_update", "conflicts", "missing_packages", "missing_secrets", "missing_environment_variables", "warnings"]}


def _apply_import_mappings(value: Any, mapping: dict[str, Any]) -> Any:
    connector_mapping = mapping.get("connector_mapping") or {}
    secret_mapping = mapping.get("secret_mapping") or {}
    if isinstance(value, dict):
        if set(value.keys()) == {"$secret"}:
            name = str(value["$secret"])
            return {"$secret": secret_mapping.get(name, name)}
        return {str(key): _apply_import_mappings(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [_apply_import_mappings(item, mapping) for item in value]
    if isinstance(value, str):
        return connector_mapping.get(value, secret_mapping.get(value, value))
    return value


async def _upsert_environment_variables(session: AsyncSession, values: dict[str, Any], target, *, http_request: Request | None = None) -> None:
    if not values:
        return
    if target is None:
        raise BadRequestError("CURRENT_ENVIRONMENT_REQUIRED_FOR_VARIABLES")
    for key, value in values.items():
        payload = EnvironmentVariableCreate(key=str(key), value_json=value if not (isinstance(value, dict) and "$secret" in value) else None, secret_ref=value.get("$secret") if isinstance(value, dict) and "$secret" in value else None, description="Provided during change set import")
        await env_service.upsert_variable(session, target.id, payload, http_request=http_request)


async def _existing_object(session: AsyncSession, object_type: str, item: dict[str, Any]):
    model, key, identity = _target_identity(object_type, item)
    if model is None:
        raise BadRequestError(f"Unsupported change set object type: {object_type}")
    object_id = item.get("object_id")
    if object_id:
        try:
            by_id = await session.get(model, UUID(str(object_id)))
            if by_id is not None:
                return by_id
        except Exception:
            pass
    if key and identity:
        return (await session.execute(select(model).where(getattr(model, key) == identity).limit(1))).scalar_one_or_none()
    return None


def _target_identity(object_type: str, item: dict[str, Any]) -> tuple[type | None, str | None, Any]:
    config = item.get("config_json") or {}
    deps = item.get("dependencies_json") or {}
    identity = deps.get("identity") if isinstance(deps, dict) else {}
    if object_type == "integration_flow":
        from app.integration_flows.models import IntegrationFlow
        return IntegrationFlow, "slug", (identity or {}).get("slug") or _slug(config.get("name") or item.get("object_name") or "integration-flow")
    if object_type == "workflow":
        from app.workflows.models import Workflow
        return Workflow, "name", config.get("name") or item.get("object_name")
    if object_type == "mapping":
        from app.mappings.models import MappingDefinition
        return MappingDefinition, "name", config.get("name") or item.get("object_name")
    if object_type == "business_rule":
        from app.business_rules.models import BusinessRuleSet
        return BusinessRuleSet, "name", config.get("name") or item.get("object_name")
    if object_type == "resolver":
        from app.resolvers.models import ResolverDefinitionV2
        return ResolverDefinitionV2, "resolver_code", config.get("resolver_code") or item.get("object_name")
    if object_type == "endpoint":
        from app.integration_bus.models import IntegrationEndpoint
        return IntegrationEndpoint, "slug", config.get("slug") or _slug(config.get("name") or item.get("object_name") or "endpoint")
    if object_type == "route":
        from app.integration_bus.models import IntegrationRoute
        return IntegrationRoute, "name", config.get("name") or item.get("object_name")
    if object_type == "odata_lookup_template":
        from app.integration_bus.models import ODataLookupTemplate
        return ODataLookupTemplate, "name", config.get("name") or item.get("object_name")
    if object_type == "operation_template":
        from app.operation_templates.models import OperationTemplate
        return OperationTemplate, "name", config.get("name") or item.get("object_name")
    if object_type == "saved_test_case":
        from app.test_console.models import SavedTestCase
        return SavedTestCase, "name", config.get("name") or item.get("object_name")
    return None, None, None


async def _ensure_runtime_object(session: AsyncSession, object_type: str, item: dict[str, Any], config: dict[str, Any], existing: Any | None) -> UUID:
    if existing is not None:
        return existing.id
    object_id = _source_uuid_or_new(item.get("object_id"))
    if object_type == "business_rule":
        from app.business_rules.models import BusinessRuleSet
        obj = BusinessRuleSet(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported rule {object_id}"), description=config.get("description"), enabled=bool(config.get("enabled", True)), scope=config.get("scope"), rules_json=config.get("rules_json") or {"mode": "first_match", "rules": []})
    elif object_type == "resolver":
        from app.resolvers.models import ResolverDefinitionV2
        obj = ResolverDefinitionV2(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported resolver {object_id}"), resolver_code=str(config.get("resolver_code") or _slug(config.get("name") or str(object_id))), object_type=str(config.get("object_type") or "Object"), enabled=bool(config.get("enabled", True)), strategy=str(config.get("strategy") or "static_map"), connector_id=_uuid_or_none(config.get("connector_id")), input_schema_json=config.get("input_schema_json") or {}, output_schema_json=config.get("output_schema_json"), config_json=config.get("config_json") or {}, cache_enabled=bool(config.get("cache_enabled", True)), cache_ttl_seconds=int(config.get("cache_ttl_seconds") or 3600))
    elif object_type == "mapping":
        from app.mappings.models import MappingDefinition, MappingVersion
        obj = MappingDefinition(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported mapping {object_id}"), description=config.get("description"), source_entity=config.get("source_entity"), target_entity=config.get("target_entity"))
        session.add(obj)
        await session.flush()
        payload = config.get("version_payload") if isinstance(config.get("version_payload"), dict) else {}
        session.add(MappingVersion(mapping_id=obj.id, version=1, rules_json=payload.get("rules_json") or [], source_schema_json=payload.get("source_schema_json") or {}, target_schema_json=payload.get("target_schema_json") or {}, notes=payload.get("notes") or "Imported baseline"))
        await session.flush()
        return obj.id
    elif object_type == "workflow":
        from app.workflows.models import Workflow
        obj = Workflow(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported workflow {object_id}"), description=config.get("description"), event_type=config.get("event_type"), source_system=config.get("source_system"), target_system=config.get("target_system"), entity_type=config.get("entity_type"), version=int(config.get("version") or 1), enabled=bool(config.get("enabled", True)), steps_json=config.get("steps_json") or [], validation_json=config.get("validation_json") or {}, source_mapping_version_id=_uuid_or_none(config.get("source_mapping_version_id")), target_mapping_version_id=_uuid_or_none(config.get("target_mapping_version_id")))
    elif object_type == "integration_flow":
        from app.integration_flows.models import IntegrationFlow
        deps = item.get("dependencies_json") or {}
        identity = deps.get("identity") if isinstance(deps, dict) else {}
        obj = IntegrationFlow(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported flow {object_id}"), slug=str((identity or {}).get("slug") or _slug(config.get("name") or item.get("object_name") or str(object_id))), description=config.get("description"), enabled=bool(config.get("enabled", True)), source_type="onec", target_type="external_api", matcher_group_json=config.get("matcher_group_json") or {"mode": "all", "rules": [{"type": "always"}]}, action_json=config.get("action_json") or {"type": "create_event_only"}, response_config_json=config.get("response_config_json") or {}, builder_json=config.get("builder_json"), test_payload_json=config.get("test_payload_json"), test_payload_text=config.get("test_payload_text"))
    elif object_type == "endpoint":
        from app.integration_bus.models import IntegrationEndpoint
        obj = IntegrationEndpoint(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported endpoint {object_id}"), slug=str(config.get("slug") or _slug(config.get("name") or str(object_id))), enabled=bool(config.get("enabled", True)), description=config.get("description"), input_mode=str(config.get("input_mode") or "json"), response_mode=str(config.get("response_mode") or "accepted_event"), processing_mode=str(config.get("processing_mode") or "async_queue"), default_source_system=config.get("default_source_system"), default_target_system=config.get("default_target_system"), default_event_type=str(config.get("default_event_type") or "ImportedEvent"), default_entity_type=config.get("default_entity_type"), workflow_id=_uuid_or_none(config.get("workflow_id")), route_id=_uuid_or_none(config.get("route_id")), operation_template_id=_uuid_or_none(config.get("operation_template_id")), auth_mode=str(config.get("auth_mode") or "none"), auth_config_json=config.get("auth_config_json") or {})
    elif object_type == "saved_test_case":
        from app.test_console.models import SavedTestCase
        obj = SavedTestCase(id=object_id, name=str(config.get("name") or item.get("object_name") or f"Imported test {object_id}"), description=config.get("description"), endpoint_id=_uuid_or_none(config.get("endpoint_id")), method=str(config.get("method") or "POST"), headers_json=config.get("headers_json") or {}, body_text=config.get("body_text"), body_json=config.get("body_json"), input_mode=str(config.get("input_mode") or "json"), expected_status=config.get("expected_status"))
    else:
        raise BadRequestError(f"Create is not supported for {object_type} in promotion MVP")
    session.add(obj)
    await session.flush()
    return obj.id


def _source_uuid_or_new(value: Any) -> UUID:
    try:
        return UUID(str(value)) if value else new_uuid()
    except Exception:
        return new_uuid()


def _uuid_or_none(value: Any) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except Exception:
        return None


def _slug(value: Any) -> str:
    raw = str(value or "item").lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in raw).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:80] or "item"


async def _actor_name(session: AsyncSession, request: Request | None) -> str | None:
    actor = await audit_service.actor_from_request(session, request)
    return actor.get("actor_username") or actor.get("actor_display_name") or actor.get("actor_type")
