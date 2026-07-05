from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.audit.diff import normalize_json
from app.config_versions import repository
from app.config_versions.diff import diff_config
from app.config_versions.models import ConfigVersion, ConfigVersionStatus, ConfigVersionTestStatus
from app.config_versions.schemas import ConfigDraftPatch, ConfigDraftRequest, ConfigPublishRequest, ConfigRollbackRequest, ConfigVersionTestRequest
from app.core.config import get_settings
from app.core.enums import EventStatus, RunMode, RunStatus, StepStatus
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import EventRun, EventStep, IntegrationEvent

SUPPORTED_OBJECT_TYPES = {
    "integration_flow",
    "workflow",
    "mapping",
    "business_rule",
    "resolver",
    "operation_template",
    "odata_lookup_template",
    "route",
    "endpoint",
}
EFFECTIVE_ACTIVE = {ConfigVersionStatus.ACTIVE, ConfigVersionStatus.ROLLBACK}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def versions(session: AsyncSession, object_type: str, object_id: UUID) -> dict[str, Any]:
    _ensure_supported(object_type)
    await ensure_active_version(session, object_type, object_id)
    rows = await repository.list_versions(session, object_type, object_id)
    active = next((item for item in rows if item.status in EFFECTIVE_ACTIVE), None)
    draft = next((item for item in rows if item.status == ConfigVersionStatus.DRAFT), None)
    return {"object_type": object_type, "object_id": object_id, "active_version": active, "draft_version": draft, "versions": rows}


async def get_version_or_404(session: AsyncSession, object_type: str, object_id: UUID, version_id: UUID) -> ConfigVersion:
    item = await repository.get_version(session, version_id)
    if item is None:
        raise NotFoundError(f"Config version not found: {version_id}")
    if item.object_type != object_type or str(item.object_id) != str(object_id):
        raise NotFoundError(f"Config version does not belong to {object_type}/{object_id}: {item.object_type}/{item.object_id}")
    return item


async def ensure_active_version(session: AsyncSession, object_type: str, object_id: UUID, *, created_by: str | None = "system") -> ConfigVersion:
    _ensure_supported(object_type)
    active = await repository.get_active(session, object_type, object_id)
    if active is not None:
        return active
    config, name, metadata = await read_object_config(session, object_type, object_id)
    item = ConfigVersion(
        object_type=object_type,
        object_id=object_id,
        object_name=name,
        version_number=1,
        status=ConfigVersionStatus.ACTIVE,
        config_json=config,
        metadata_json={**metadata, "baseline": True},
        created_by=created_by,
        published_by=created_by,
        published_at=utcnow(),
        test_status=ConfigVersionTestStatus.PASSED,
        comment="Baseline active version from current runtime config",
    )
    session.add(item)
    await session.flush()
    return item


async def create_or_update_draft(session: AsyncSession, object_type: str, object_id: UUID, request: ConfigDraftRequest, *, http_request: Request | None = None) -> ConfigVersion:
    active = await ensure_active_version(session, object_type, object_id)
    draft = await repository.get_draft(session, object_type, object_id)
    actor = await _actor_name(session, http_request)
    before = _version_snapshot(draft) if draft else None
    if draft is None:
        draft = ConfigVersion(
            object_type=object_type,
            object_id=object_id,
            object_name=active.object_name,
            version_number=await repository.next_version_number(session, object_type, object_id),
            status=ConfigVersionStatus.DRAFT,
            config_json=request.config_json or dict(active.config_json),
            metadata_json=request.metadata_json or {"draft_from_version_id": str(active.id), "draft_from_version": active.version_number},
            created_by=actor,
            test_status=ConfigVersionTestStatus.NOT_TESTED,
            comment=request.comment,
        )
        session.add(draft)
        action = "config.draft_created"
        summary = f"Draft v{draft.version_number} created for {object_type} {draft.object_name or object_id}"
    else:
        if request.config_json is not None:
            draft.config_json = request.config_json
        if request.metadata_json is not None:
            draft.metadata_json = request.metadata_json
        if request.comment is not None:
            draft.comment = request.comment
        draft.test_status = ConfigVersionTestStatus.NOT_TESTED
        draft.last_test_error = None
        action = "config.draft_updated"
        summary = f"Draft v{draft.version_number} updated for {object_type} {draft.object_name or object_id}"
    await validate_config(session, object_type, draft.config_json)
    await session.flush()
    await audit_service.record_change(
        session,
        request=http_request,
        action=action,
        category="config_versions",
        object_type=object_type,
        object_id=object_id,
        object_name=draft.object_name,
        before=before,
        after=_version_snapshot(draft),
        summary=summary,
        details={"version_number": draft.version_number, "comment": draft.comment},
    )
    return draft


async def patch_draft(session: AsyncSession, object_type: str, object_id: UUID, request: ConfigDraftPatch, *, http_request: Request | None = None) -> ConfigVersion:
    await ensure_active_version(session, object_type, object_id)
    draft = await repository.get_draft(session, object_type, object_id)
    if draft is None:
        raise NotFoundError("Draft config version not found")
    before = _version_snapshot(draft)
    if request.config_json is not None:
        draft.config_json = request.config_json
        draft.test_status = ConfigVersionTestStatus.NOT_TESTED
        draft.last_test_error = None
    if request.metadata_json is not None:
        draft.metadata_json = request.metadata_json
    if request.comment is not None:
        draft.comment = request.comment
    await validate_config(session, object_type, draft.config_json)
    await session.flush()
    await audit_service.record_change(
        session,
        request=http_request,
        action="config.draft_updated",
        category="config_versions",
        object_type=object_type,
        object_id=object_id,
        object_name=draft.object_name,
        before=before,
        after=_version_snapshot(draft),
        summary=f"Draft v{draft.version_number} updated for {object_type} {draft.object_name or object_id}",
        details={"version_number": draft.version_number, "comment": draft.comment},
    )
    return draft


async def discard_draft(session: AsyncSession, object_type: str, object_id: UUID, *, http_request: Request | None = None) -> dict[str, bool]:
    draft = await repository.get_draft(session, object_type, object_id)
    if draft is None:
        raise NotFoundError("Draft config version not found")
    before = _version_snapshot(draft)
    draft.status = ConfigVersionStatus.REJECTED
    draft.archived_at = utcnow()
    await session.flush()
    await audit_service.record_change(
        session,
        request=http_request,
        action="config.draft_discarded",
        category="config_versions",
        object_type=object_type,
        object_id=object_id,
        object_name=draft.object_name,
        before=before,
        after=_version_snapshot(draft),
        summary=f"Draft v{draft.version_number} discarded for {object_type} {draft.object_name or object_id}",
    )
    return {"discarded": True}


async def publish(session: AsyncSession, object_type: str, object_id: UUID, request: ConfigPublishRequest, *, http_request: Request | None = None) -> ConfigVersion:
    version = await get_version_or_404(session, object_type, object_id, request.version_id)
    if version.status != ConfigVersionStatus.DRAFT:
        raise BadRequestError("Only draft versions can be published")
    await _guard_publish(version, request.comment, request.confirm_untested)
    await validate_config(session, object_type, version.config_json)
    before_runtime, _, _ = await read_object_config(session, object_type, object_id)
    active = await repository.get_active(session, object_type, object_id)
    if active is not None:
        active.status = ConfigVersionStatus.ARCHIVED
        active.archived_at = utcnow()
    actor = await _actor_name(session, http_request)
    version.status = ConfigVersionStatus.ACTIVE
    version.published_by = actor
    version.published_at = utcnow()
    if request.comment is not None:
        version.comment = request.comment
    await apply_object_config(session, object_type, object_id, version.config_json)
    after_runtime, name, _ = await read_object_config(session, object_type, object_id)
    version.object_name = name
    await session.flush()
    await audit_service.record_change(
        session,
        request=http_request,
        action="config.published",
        category="config_versions",
        object_type=object_type,
        object_id=object_id,
        object_name=version.object_name,
        before=before_runtime,
        after=after_runtime,
        summary=f"Published {object_type} {version.object_name or object_id} v{version.version_number}",
        details={"version_id": str(version.id), "version_number": version.version_number, "comment": version.comment, "diff": diff_config(before_runtime, after_runtime)},
    )
    return version


async def rollback(session: AsyncSession, object_type: str, object_id: UUID, request: ConfigRollbackRequest, *, http_request: Request | None = None) -> ConfigVersion:
    source = await get_version_or_404(session, object_type, object_id, request.target_version_id)
    if source.status == ConfigVersionStatus.DRAFT:
        raise BadRequestError("Cannot rollback to draft version")
    await _guard_publish(source, request.comment, request.confirm_untested, rollback=True)
    before_runtime, _, _ = await read_object_config(session, object_type, object_id)
    active = await repository.get_active(session, object_type, object_id)
    if active is not None:
        active.status = ConfigVersionStatus.ARCHIVED
        active.archived_at = utcnow()
    actor = await _actor_name(session, http_request)
    version = ConfigVersion(
        object_type=object_type,
        object_id=object_id,
        object_name=source.object_name,
        version_number=await repository.next_version_number(session, object_type, object_id),
        status=ConfigVersionStatus.ROLLBACK,
        config_json=dict(source.config_json),
        metadata_json={**(source.metadata_json or {}), "rollback_from_version": source.version_number},
        created_by=actor,
        published_by=actor,
        published_at=utcnow(),
        rollback_of_version_id=source.id,
        test_status=source.test_status,
        comment=request.comment or f"Rollback to v{source.version_number}",
    )
    session.add(version)
    await apply_object_config(session, object_type, object_id, version.config_json)
    after_runtime, name, _ = await read_object_config(session, object_type, object_id)
    version.object_name = name
    await session.flush()
    await audit_service.record_change(
        session,
        request=http_request,
        action="config.rollback",
        category="config_versions",
        object_type=object_type,
        object_id=object_id,
        object_name=version.object_name,
        before=before_runtime,
        after=after_runtime,
        summary=f"Rolled back {object_type} {version.object_name or object_id} to v{source.version_number}",
        details={"version_id": str(version.id), "target_version_id": str(source.id), "version_number": version.version_number, "comment": version.comment},
    )
    return version


async def diff_versions(session: AsyncSession, object_type: str, object_id: UUID, from_version: UUID, to_version: UUID) -> dict[str, Any]:
    left = await get_version_or_404(session, object_type, object_id, from_version)
    right = await get_version_or_404(session, object_type, object_id, to_version)
    diff = diff_config(left.config_json, right.config_json)
    return {"from_version_id": left.id, "to_version_id": right.id, **diff}


async def test_version(session: AsyncSession, object_type: str, object_id: UUID, version_id: UUID, request: ConfigVersionTestRequest, *, http_request: Request | None = None) -> dict[str, Any]:
    version = await get_version_or_404(session, object_type, object_id, version_id)
    if version.status not in {ConfigVersionStatus.DRAFT, ConfigVersionStatus.ACTIVE, ConfigVersionStatus.ROLLBACK}:
        raise BadRequestError("Only draft or active config versions can be tested")
    status = ConfigVersionTestStatus.PASSED
    result: dict[str, Any] = {}
    error: str | None = None
    try:
        result = await _run_object_test(session, object_type, version.config_json, request)
        if result.get("warning"):
            status = ConfigVersionTestStatus.WARNING
    except Exception as exc:  # record failure fidelity for users instead of hiding it in logs
        status = ConfigVersionTestStatus.FAILED
        error = str(exc)
        result = {"error": error}
    event, run = await _create_draft_test_timeline(session, version, status, result, error)
    version.test_status = status
    version.last_test_event_id = event.id
    version.last_test_run_at = utcnow()
    version.last_test_error = error
    await session.flush()
    await audit_service.record_action(
        session,
        request=http_request,
        action="config.version_tested",
        category="config_versions",
        object_type=object_type,
        object_id=object_id,
        object_name=version.object_name,
        summary=f"Tested {object_type} {version.object_name or object_id} v{version.version_number}: {status.value}",
        details={"version_id": str(version.id), "version_number": version.version_number, "status": status.value, "result": result, "run_id": str(run.id)},
        event_id=event.id,
    )
    return {"test_status": status, "event_id": event.id, "timeline_url": f"/events/{event.id}", "result": result, "error": error}


async def read_object_config(session: AsyncSession, object_type: str, object_id: UUID) -> tuple[dict[str, Any], str | None, dict[str, Any]]:
    if object_type == "integration_flow":
        from app.integration_flows.models import IntegrationFlow
        item = await _get(session, IntegrationFlow, object_id, "Integration flow")
        return _flow_config(item), item.name, {"slug": item.slug}
    if object_type == "workflow":
        from app.workflows.models import Workflow
        item = await _get(session, Workflow, object_id, "Workflow")
        return _workflow_config(item), item.name, {}
    if object_type == "mapping":
        from app.mappings.models import MappingDefinition
        item = await _get(session, MappingDefinition, object_id, "Mapping")
        latest = sorted(item.versions, key=lambda row: row.version)[-1] if item.versions else None
        return _mapping_config(item, latest), item.name, {"latest_mapping_version": latest.version if latest else None}
    if object_type == "business_rule":
        from app.business_rules.models import BusinessRuleSet
        item = await _get(session, BusinessRuleSet, object_id, "Business rule set")
        return _business_rule_config(item), item.name, {}
    if object_type == "resolver":
        from app.resolvers.models import ResolverDefinitionV2
        item = await _get(session, ResolverDefinitionV2, object_id, "Resolver")
        return _resolver_config(item), item.name, {"resolver_code": item.resolver_code}
    if object_type == "operation_template":
        from app.operation_templates.models import OperationTemplate
        item = await _get(session, OperationTemplate, object_id, "Operation template")
        return _operation_template_config(item), item.name, {}
    if object_type == "odata_lookup_template":
        from app.integration_bus.models import ODataLookupTemplate
        item = await _get(session, ODataLookupTemplate, object_id, "OData lookup template")
        return _odata_lookup_config(item), item.name, {}
    if object_type == "route":
        from app.integration_bus.models import IntegrationRoute
        item = await _get(session, IntegrationRoute, object_id, "Integration route")
        return _route_config(item), item.name, {}
    if object_type == "endpoint":
        from app.integration_bus.models import IntegrationEndpoint
        item = await _get(session, IntegrationEndpoint, object_id, "Integration endpoint")
        return _endpoint_config(item), item.name, {}
    raise BadRequestError(f"Unsupported config object type: {object_type}")


async def apply_object_config(session: AsyncSession, object_type: str, object_id: UUID, config: dict[str, Any]) -> None:
    if object_type == "integration_flow":
        from app.integration_flows.models import IntegrationFlow
        item = await _get(session, IntegrationFlow, object_id, "Integration flow")
        await _assign(item, config, _flow_fields())
        return
    if object_type == "workflow":
        from app.workflows.models import Workflow
        item = await _get(session, Workflow, object_id, "Workflow")
        await _assign(item, config, _workflow_fields())
        return
    if object_type == "mapping":
        from app.mappings.models import MappingDefinition, MappingVersion
        item = await _get(session, MappingDefinition, object_id, "Mapping")
        await _assign(item, config, ["name", "description", "source_entity", "target_entity"])
        payload = config.get("version_payload") if isinstance(config.get("version_payload"), dict) else {}
        if payload:
            next_version = max([version.version for version in item.versions] or [0]) + 1
            session.add(MappingVersion(mapping_id=item.id, version=next_version, rules_json=payload.get("rules_json") or [], source_schema_json=payload.get("source_schema_json") or {}, target_schema_json=payload.get("target_schema_json") or {}, notes=payload.get("notes") or "Published from config version"))
        await session.flush()
        return
    if object_type == "business_rule":
        from app.business_rules.models import BusinessRuleSet
        item = await _get(session, BusinessRuleSet, object_id, "Business rule set")
        await _assign(item, config, ["name", "description", "enabled", "scope", "rules_json"])
        return
    if object_type == "resolver":
        from app.resolvers.models import ResolverDefinitionV2
        item = await _get(session, ResolverDefinitionV2, object_id, "Resolver")
        await _assign(item, config, ["name", "resolver_code", "object_type", "enabled", "strategy", "connector_id", "input_schema_json", "output_schema_json", "config_json", "cache_enabled", "cache_ttl_seconds"])
        return
    if object_type == "operation_template":
        from app.operation_templates.models import OperationTemplate
        item = await _get(session, OperationTemplate, object_id, "Operation template")
        await _assign(item, config, _operation_template_fields())
        return
    if object_type == "odata_lookup_template":
        from app.integration_bus.models import ODataLookupTemplate
        item = await _get(session, ODataLookupTemplate, object_id, "OData lookup template")
        await _assign(item, config, ["name", "connector_id", "resource", "filter_template", "extract_json", "required", "cache_ttl_seconds"])
        return
    if object_type == "route":
        from app.integration_bus.models import IntegrationRoute
        item = await _get(session, IntegrationRoute, object_id, "Integration route")
        await _assign(item, config, ["name", "enabled", "source_system", "target_system", "event_type", "message_type", "operation", "condition_json", "workflow_id", "target_connector_id", "operation_template_id", "priority"])
        return
    if object_type == "endpoint":
        from app.integration_bus.models import IntegrationEndpoint
        item = await _get(session, IntegrationEndpoint, object_id, "Integration endpoint")
        await _assign(item, config, ["name", "slug", "enabled", "description", "input_mode", "response_mode", "processing_mode", "default_source_system", "default_target_system", "default_event_type", "default_entity_type", "workflow_id", "route_id", "operation_template_id", "auth_mode", "auth_config_json"])
        return
    raise BadRequestError(f"Unsupported config object type: {object_type}")


async def validate_config(session: AsyncSession, object_type: str, config: dict[str, Any]) -> None:
    if object_type == "integration_flow":
        from app.flow_builder.validator import validate_builder
        from app.matchers.validators import validate_matcher_group
        validate_matcher_group(config.get("matcher_group_json") or {"mode": "all", "rules": [{"type": "always"}]})
        if config.get("builder_json"):
            validation = validate_builder(config["builder_json"])
            if not validation.get("valid"):
                raise BadRequestError(f"FLOW_BUILDER_INVALID: {validation}")
        return
    if object_type == "workflow":
        from app.workflows.service import _validate_workflow_payload
        await _validate_workflow_payload(session, config)
        return
    if object_type == "mapping":
        from app.mappings.engine import MappingEngine
        payload = config.get("version_payload") if isinstance(config.get("version_payload"), dict) else {}
        validation = MappingEngine().validate(payload.get("rules_json") or [])
        if not validation["valid"]:
            raise BadRequestError("; ".join(validation["errors"]))
        return
    if object_type == "business_rule":
        from app.business_rules.engine import engine
        engine.evaluate(config.get("rules_json") or {"mode": "first_match", "rules": []}, {"payload": {}, "variables": {}})
        return
    if object_type == "resolver":
        from app.resolvers.schemas import ResolverDefinitionCreate
        from app.resolvers.service import validate_definition
        validate_definition(ResolverDefinitionCreate(**{key: config.get(key) for key in ["name", "resolver_code", "object_type", "enabled", "strategy", "connector_id", "input_schema_json", "output_schema_json", "config_json", "cache_enabled", "cache_ttl_seconds"]}))
        return
    if object_type == "operation_template":
        from app.operation_templates.service import _validate_template
        _validate_template(config.get("request_template_json") or {})
        return
    # Endpoint/route/OData configs rely on DB constraints and runtime validation.


async def _run_object_test(session: AsyncSession, object_type: str, config: dict[str, Any], request: ConfigVersionTestRequest) -> dict[str, Any]:
    if object_type == "mapping":
        from app.mappings.engine import MappingEngine
        payload = config.get("version_payload") if isinstance(config.get("version_payload"), dict) else {}
        validation = MappingEngine().validate(payload.get("rules_json") or [], request.payload)
        if not validation["valid"]:
            raise BadRequestError("; ".join(validation["errors"]))
        return validation
    if object_type == "business_rule":
        from app.business_rules.engine import engine
        result = engine.evaluate(config.get("rules_json") or {"mode": "first_match", "rules": []}, {"payload": request.payload, "variables": request.variables})
        return result.model_dump(mode="json")
    if object_type == "resolver":
        # Draft resolver test is intentionally side-effect free. static_map can be evaluated without mutating the active resolver.
        if config.get("strategy") == "static_map":
            input_data = request.input or request.payload
            for entry in (config.get("config_json") or {}).get("entries", []):
                match = entry.get("match") if isinstance(entry, dict) else None
                if isinstance(match, dict) and all(str(input_data.get(key, "")) == str(value) for key, value in match.items()):
                    return {"success": True, "object_json": entry.get("object") or entry.get("value") or {}, "source": {"type": "static_map_draft"}}
            raise BadRequestError("OBJECT_NOT_FOUND")
        return {"success": True, "warning": "Resolver draft validation passed. Publish before running connector-backed resolver tests.", "strategy": config.get("strategy")}
    if object_type == "integration_flow":
        from app.flow_builder.validator import validate_builder
        from app.matchers.engine import evaluate_matcher_group
        matcher = evaluate_matcher_group(config.get("matcher_group_json") or {"mode": "all", "rules": [{"type": "always"}]}, {"body": request.payload, "text": str(request.payload), "headers": {}, "query": {}})
        builder_validation = validate_builder(config["builder_json"]) if config.get("builder_json") else {"valid": True, "errors": []}
        if not builder_validation.get("valid"):
            raise BadRequestError(f"FLOW_BUILDER_INVALID: {builder_validation}")
        return {"matcher": matcher, "builder_validation": builder_validation, "target_action": config.get("action_json")}
    await validate_config(session, object_type, config)
    return {"success": True, "message": f"{object_type} draft validation passed"}


async def _create_draft_test_timeline(session: AsyncSession, version: ConfigVersion, status: ConfigVersionTestStatus, result: dict[str, Any], error: str | None) -> tuple[IntegrationEvent, EventRun]:
    now = utcnow()
    event = IntegrationEvent(
        correlation_id=f"draft-test-{version.object_type}-{version.version_number}",
        source_system="Config Draft Test",
        target_system=version.object_type,
        event_type="DraftTestRun",
        entity_type=version.object_type,
        entity_id=str(version.object_id),
        status=EventStatus.SUCCESS if status in {ConfigVersionTestStatus.PASSED, ConfigVersionTestStatus.WARNING} else EventStatus.FAILED,
    )
    session.add(event)
    await session.flush()
    run = EventRun(event_id=event.id, run_number=1, mode=RunMode.DRY_RUN, status=RunStatus.DRY_RUN_SUCCESS if event.status == EventStatus.SUCCESS else RunStatus.DRY_RUN_FAILED, started_at=now, finished_at=now, workflow_name="Draft Test Run", workflow_version=version.version_number, mapping_versions_json={"object_type": version.object_type, "version_id": str(version.id), "not_production_traffic": True})
    session.add(run)
    await session.flush()
    session.add(EventStep(run_id=run.id, step_order=1, step_name="draft_test", status=StepStatus.SUCCESS if event.status == EventStatus.SUCCESS else StepStatus.FAILED, started_at=now, finished_at=now, duration_ms=0, error_message=error, step_config_json={"object_type": version.object_type, "version_number": version.version_number, "draft_test": True, "result": result}, condition="on_dry_run"))
    await session.flush()
    return event, run


async def _guard_publish(version: ConfigVersion, comment: str | None, confirm_untested: bool, *, rollback: bool = False) -> None:
    settings = get_settings()
    production = settings.app_env.lower() in {"production", "prod"}
    require_comment = settings.config_require_comment_on_publish if settings.config_require_comment_on_publish is not None else production
    require_test = settings.config_require_test_before_publish if settings.config_require_test_before_publish is not None else production
    if require_comment and not (comment or version.comment):
        raise BadRequestError("PUBLISH_COMMENT_REQUIRED")
    if version.test_status == ConfigVersionTestStatus.FAILED:
        raise BadRequestError("PUBLISH_BLOCKED_TEST_FAILED")
    if require_test and version.test_status not in {ConfigVersionTestStatus.PASSED, ConfigVersionTestStatus.WARNING} and not confirm_untested:
        raise BadRequestError("PUBLISH_REQUIRES_PASSED_TEST")


async def _actor_name(session: AsyncSession, request: Request | None) -> str | None:
    actor = await audit_service.actor_from_request(session, request)
    return actor.get("actor_username") or actor.get("actor_display_name") or actor.get("actor_type")


async def _get(session: AsyncSession, model: type, object_id: UUID, label: str):
    item = await session.get(model, object_id)
    if item is None:
        raise NotFoundError(f"{label} not found")
    return item


async def _assign(item: Any, config: dict[str, Any], fields: list[str]) -> None:
    from uuid import UUID as UUIDType
    for field in fields:
        if field in config:
            value = config[field]
            if field.endswith("_id") and isinstance(value, str):
                value = UUIDType(value)
            setattr(item, field, value)


def _version_snapshot(version: ConfigVersion | None) -> dict[str, Any] | None:
    if version is None:
        return None
    return {"id": str(version.id), "object_type": version.object_type, "object_id": str(version.object_id), "version_number": version.version_number, "status": version.status.value, "test_status": version.test_status.value, "config_json": version.config_json, "comment": version.comment}


def _ensure_supported(object_type: str) -> None:
    if object_type not in SUPPORTED_OBJECT_TYPES:
        raise BadRequestError(f"Unsupported config object type: {object_type}")


def _flow_fields() -> list[str]:
    return ["name", "description", "enabled", "matcher_group_json", "action_json", "response_config_json", "builder_json", "test_payload_json", "test_payload_text"]


def _workflow_fields() -> list[str]:
    return ["name", "description", "event_type", "source_system", "target_system", "entity_type", "version", "enabled", "steps_json", "validation_json", "source_mapping_version_id", "target_mapping_version_id"]


def _operation_template_fields() -> list[str]:
    return ["name", "operation_code", "system_type", "operation", "direction", "input_mode", "output_mode", "target_connector_type", "default_body_mode", "default_content_type", "description", "enabled", "request_schema_json", "request_template_json", "response_schema_json", "example_request_json", "example_response_json", "default_workflow_id"]


def _flow_config(item: Any) -> dict[str, Any]:
    return _jsonable({field: getattr(item, field) for field in _flow_fields()})


def _workflow_config(item: Any) -> dict[str, Any]:
    return _jsonable({field: getattr(item, field) for field in _workflow_fields()})


def _mapping_config(item: Any, latest: Any | None) -> dict[str, Any]:
    return _jsonable({"name": item.name, "description": item.description, "source_entity": item.source_entity, "target_entity": item.target_entity, "version_payload": {"rules_json": latest.rules_json if latest else [], "source_schema_json": latest.source_schema_json if latest else {}, "target_schema_json": latest.target_schema_json if latest else {}, "notes": latest.notes if latest else None}})


def _business_rule_config(item: Any) -> dict[str, Any]:
    return _jsonable({"name": item.name, "description": item.description, "enabled": item.enabled, "scope": item.scope, "rules_json": item.rules_json})


def _resolver_config(item: Any) -> dict[str, Any]:
    return _jsonable({"name": item.name, "resolver_code": item.resolver_code, "object_type": item.object_type, "enabled": item.enabled, "strategy": item.strategy, "connector_id": str(item.connector_id) if item.connector_id else None, "input_schema_json": item.input_schema_json, "output_schema_json": item.output_schema_json, "config_json": item.config_json, "cache_enabled": item.cache_enabled, "cache_ttl_seconds": item.cache_ttl_seconds})


def _operation_template_config(item: Any) -> dict[str, Any]:
    return _jsonable({field: getattr(item, field) for field in _operation_template_fields()})


def _odata_lookup_config(item: Any) -> dict[str, Any]:
    return _jsonable({"name": item.name, "connector_id": str(item.connector_id), "resource": item.resource, "filter_template": item.filter_template, "extract_json": item.extract_json, "required": item.required, "cache_ttl_seconds": item.cache_ttl_seconds})


def _route_config(item: Any) -> dict[str, Any]:
    return _jsonable({"name": item.name, "enabled": item.enabled, "source_system": item.source_system, "target_system": item.target_system, "event_type": item.event_type, "message_type": item.message_type, "operation": item.operation, "condition_json": item.condition_json, "workflow_id": str(item.workflow_id) if item.workflow_id else None, "target_connector_id": str(item.target_connector_id) if item.target_connector_id else None, "operation_template_id": str(item.operation_template_id) if item.operation_template_id else None, "priority": item.priority})


def _endpoint_config(item: Any) -> dict[str, Any]:
    return _jsonable({"name": item.name, "slug": item.slug, "enabled": item.enabled, "description": item.description, "input_mode": item.input_mode, "response_mode": item.response_mode, "processing_mode": item.processing_mode, "default_source_system": item.default_source_system, "default_target_system": item.default_target_system, "default_event_type": item.default_event_type, "default_entity_type": item.default_entity_type, "workflow_id": str(item.workflow_id) if item.workflow_id else None, "route_id": str(item.route_id) if item.route_id else None, "operation_template_id": str(item.operation_template_id) if item.operation_template_id else None, "auth_mode": item.auth_mode, "auth_config_json": item.auth_config_json})


def _jsonable(value: Any) -> Any:
    return normalize_json(value)
