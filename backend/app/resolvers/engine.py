from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.odata import read_odata
from app.core.errors import BadRequestError
from app.resolvers import cache, repository
from app.resolvers.models import ResolverDefinitionV2
from app.resolvers.schemas import ResolverArtifact, ResolverResult
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template


class ResolverEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def resolve(self, resolver_code: str, input_data: dict[str, Any], context: dict[str, Any] | None = None, use_cache: bool = True) -> ResolverResult:
        resolver = await repository.get_by_code_or_404(self.session, resolver_code)
        artifacts = [_artifact("resolver_input.json", "validation_result", {"resolver_code": resolver_code, "input": input_data, "context": context or {}})]
        if not resolver.enabled:
            return self._error(resolver, "RESOLVER_DISABLED", f"Resolver {resolver_code} is disabled", artifacts, cache_status="disabled")
        validation_error = self._validate_input(resolver, input_data)
        if validation_error:
            return self._error(resolver, "RESOLVER_INPUT_INVALID", validation_error, artifacts, cache_status="disabled")

        cache_key = cache.cache_key_for(input_data, resolver.config_json or {})
        cache_status = "disabled"
        if resolver.cache_enabled and use_cache:
            entry, expired = await cache.get_entry(self.session, resolver, cache_key)
            cache_status = "expired" if expired else "miss"
            artifacts.append(_artifact("resolver_cache_result.json", "validation_result", {"status": cache_status, "cache_key": cache_key, "entry_id": str(entry.id) if entry else None}))
            if entry is not None and not expired:
                return ResolverResult(
                    success=True,
                    resolver_code=resolver.resolver_code,
                    object_type=resolver.object_type,
                    object_json=entry.resolved_object_json,
                    cache_status="hit",
                    source={"type": "cache", "entry_id": str(entry.id), "resolver_code": resolver.resolver_code},
                    artifacts=artifacts + [_artifact("resolved_object.json", "canonical_payload", entry.resolved_object_json)],
                )
        else:
            cache_status = "bypass" if use_cache is False else "disabled"
            artifacts.append(_artifact("resolver_cache_result.json", "validation_result", {"status": cache_status, "cache_key": cache_key}))

        if resolver.strategy == "static_map":
            result = await self._resolve_static_map(resolver, input_data, context or {}, artifacts)
        elif resolver.strategy == "odata":
            result = await self._resolve_odata(resolver, input_data, context or {}, artifacts)
        elif resolver.strategy == "rest":
            result = await self._resolve_rest(resolver, input_data, context or {}, artifacts)
        elif resolver.strategy == "chain":
            result = await self._resolve_chain(resolver, input_data, context or {}, artifacts, use_cache=use_cache)
        else:
            result = self._error(resolver, "RESOLVER_STRATEGY_UNSUPPORTED", f"Unsupported resolver strategy: {resolver.strategy}", artifacts, cache_status=cache_status)

        if result.success and result.object_json and resolver.cache_enabled and use_cache:
            entry = await cache.store_entry(
                self.session,
                resolver,
                cache_key=cache_key,
                input_data=input_data,
                object_json=result.object_json,
                source_system=str(result.source.get("system") or result.source.get("type") or resolver.strategy),
            )
            result.cache_status = "stored"
            result.artifacts.append(_artifact("resolver_cache_result.json", "validation_result", {"status": "stored", "cache_key": cache_key, "entry_id": str(entry.id), "expires_at": entry.expires_at.isoformat() if entry.expires_at else None}))
        elif result.cache_status == "disabled":
            result.cache_status = cache_status
        return result

    async def _resolve_static_map(self, resolver: ResolverDefinitionV2, input_data: dict[str, Any], context: dict[str, Any], artifacts: list[ResolverArtifact]) -> ResolverResult:
        config = resolver.config_json or {}
        request_payload = {"strategy": "static_map", "key_fields": config.get("key_fields"), "input": input_data}
        artifacts.append(_artifact("resolver_request.json", "outgoing_request", request_payload))
        for entry in _entries(config):
            if _entry_matches(entry, input_data):
                object_json = _normalize_object(resolver, _render_mapping(entry.get("object") or entry.get("value") or {}, input_data, context))
                artifacts.append(_artifact("resolver_response.json", "incoming_response", {"matched": True, "entry": _safe_entry(entry)}))
                artifacts.append(_artifact("resolved_object.json", "canonical_payload", object_json))
                return ResolverResult(success=True, resolver_code=resolver.resolver_code, object_type=resolver.object_type, object_json=object_json, cache_status="disabled", source={"type": "static_map"}, artifacts=artifacts)
        artifacts.append(_artifact("resolver_response.json", "incoming_response", {"matched": False}))
        return self._error(resolver, "OBJECT_NOT_FOUND", f"{resolver.object_type} was not found by {resolver.resolver_code}", artifacts)

    async def _resolve_odata(self, resolver: ResolverDefinitionV2, input_data: dict[str, Any], context: dict[str, Any], artifacts: list[ResolverArtifact]) -> ResolverResult:
        config = resolver.config_json or {}
        connector = await connector_repository.get_instance(self.session, resolver.connector_id) if resolver.connector_id else None
        if connector is None:
            return self._error(resolver, "RESOLVER_CONNECTOR_NOT_FOUND", "Resolver OData connector is not configured", artifacts)
        query = self._odata_query(config, input_data, context)
        resource = str(config.get("resource") or "")
        request_payload = {"connector_id": str(connector.id), "connector": connector.name, "resource": resource, "query": query}
        artifacts.append(_artifact("resolver_request.json", "outgoing_request", request_payload))
        mock_items = _mock_odata_items(config, connector.config_json)
        if mock_items is not None:
            items = _filter_mock_items(mock_items, input_data, config)
            response_payload: dict[str, Any] = {"mock": True, "value": items}
        else:
            result = await read_odata(connector.config_json, resource, query)
            response_payload = result.response_payload or {"count": len(result.items)}
            if not result.success:
                artifacts.append(_artifact("resolver_response.json", "incoming_response", response_payload if isinstance(response_payload, dict) else {"response": response_payload}))
                return self._error(resolver, result.error_code or "ODATA_RESOLVE_FAILED", result.error_message or "OData resolver failed", artifacts)
            items = result.items
        artifacts.append(_artifact("resolver_response.json", "incoming_response", response_payload))
        if not items:
            return self._error(resolver, "OBJECT_NOT_FOUND", f"{resolver.object_type} was not found in OData", artifacts)
        object_json = _normalize_object(resolver, _map_object(items[0], config.get("mapping") or config.get("output_mapping") or {}))
        artifacts.append(_artifact("resolved_object.json", "canonical_payload", object_json))
        return ResolverResult(success=True, resolver_code=resolver.resolver_code, object_type=resolver.object_type, object_json=object_json, cache_status="disabled", source={"type": "odata", "system": connector.name, "connector_id": str(connector.id)}, artifacts=artifacts)

    async def _resolve_rest(self, resolver: ResolverDefinitionV2, input_data: dict[str, Any], context: dict[str, Any], artifacts: list[ResolverArtifact]) -> ResolverResult:
        config = resolver.config_json or {}
        connector = await connector_repository.get_instance(self.session, resolver.connector_id) if resolver.connector_id else None
        connector_config = connector.config_json if connector is not None else {}
        scope = _scope(input_data, context)
        method = str(config.get("method") or "GET").upper()
        path = str(render_template(config.get("path_template") or config.get("path") or "", scope))
        base_url = str(config.get("base_url") or connector_config.get("base_url") or "").rstrip("/")
        url = path if path.startswith("http") else f"{base_url}/{path.lstrip('/')}"
        params = _render_mapping(config.get("params") or {}, input_data, context)
        body = _render_mapping(config.get("body") or {}, input_data, context)
        request_payload = {"connector_id": str(connector.id) if connector else None, "method": method, "url": url, "params": params, "body": body}
        artifacts.append(_artifact("resolver_request.json", "outgoing_request", request_payload))
        if "mock_response_json" in config:
            response_json = config["mock_response_json"]
            response_payload = {"mock": True, "status_code": 200, "body": response_json}
        elif not url or url == "/":
            return self._error(resolver, "REST_RESOLVER_URL_NOT_CONFIGURED", "REST resolver URL is not configured", artifacts)
        else:
            async with httpx.AsyncClient(timeout=float(config.get("timeout_seconds") or 15)) as client:
                response = await client.request(method, url, params=params or None, json=body or None, headers=config.get("headers") or None)
            try:
                response_json = response.json()
            except ValueError:
                response_json = {"text": response.text}
            response_payload = {"status_code": response.status_code, "body": response_json}
            if response.status_code >= 400:
                artifacts.append(_artifact("resolver_response.json", "incoming_response", response_payload))
                return self._error(resolver, "REST_RESOLVER_FAILED", f"REST resolver returned {response.status_code}", artifacts)
        artifacts.append(_artifact("resolver_response.json", "incoming_response", response_payload))
        source_payload = response_json if isinstance(response_json, dict) else {"value": response_json}
        root_path = config.get("result_path")
        if root_path:
            try:
                source_payload = resolve_path(source_payload, str(root_path))
            except PathResolutionError as exc:
                return self._error(resolver, "REST_RESULT_PATH_INVALID", str(exc), artifacts)
        if isinstance(source_payload, list):
            source_payload = source_payload[0] if source_payload else None
        if not isinstance(source_payload, dict):
            return self._error(resolver, "OBJECT_NOT_FOUND", f"{resolver.object_type} was not found in REST response", artifacts)
        object_json = _normalize_object(resolver, _map_object(source_payload, config.get("mapping") or config.get("output_mapping") or {}))
        artifacts.append(_artifact("resolved_object.json", "canonical_payload", object_json))
        return ResolverResult(success=True, resolver_code=resolver.resolver_code, object_type=resolver.object_type, object_json=object_json, cache_status="disabled", source={"type": "rest", "system": connector.name if connector else base_url, "connector_id": str(connector.id) if connector else None}, artifacts=artifacts)

    async def _resolve_chain(self, resolver: ResolverDefinitionV2, input_data: dict[str, Any], context: dict[str, Any], artifacts: list[ResolverArtifact], *, use_cache: bool) -> ResolverResult:
        config = resolver.config_json or {}
        steps = config.get("steps") if isinstance(config.get("steps"), list) else []
        artifacts.append(_artifact("resolver_request.json", "outgoing_request", {"strategy": "chain", "steps": steps}))
        if not steps:
            return self._error(resolver, "CHAIN_EMPTY", "Chain resolver has no steps", artifacts)
        last_error: ResolverResult | None = None
        for step in steps:
            if not isinstance(step, dict):
                continue
            code = str(step.get("resolver_code") or step.get("resolver") or "")
            if not code:
                continue
            child_input = _render_mapping(step.get("input") or input_data, input_data, context)
            child_result = await self.resolve(code, child_input if isinstance(child_input, dict) else input_data, context=context, use_cache=use_cache)
            artifacts.append(_artifact("resolver_response.json", "incoming_response", {"child_resolver": code, "success": child_result.success, "error_code": child_result.error_code, "object": child_result.object_json}))
            if child_result.success and child_result.object_json:
                object_json = _normalize_object(resolver, child_result.object_json)
                artifacts.append(_artifact("resolved_object.json", "canonical_payload", object_json))
                return ResolverResult(success=True, resolver_code=resolver.resolver_code, object_type=resolver.object_type, object_json=object_json, cache_status="disabled", source={"type": "chain", "resolver_code": code}, artifacts=artifacts)
            last_error = child_result
            if step.get("stop_on_error") and child_result.error_code != "OBJECT_NOT_FOUND":
                break
        return self._error(resolver, last_error.error_code if last_error else "OBJECT_NOT_FOUND", last_error.error_message if last_error else f"{resolver.object_type} was not resolved by chain", artifacts)

    def _odata_query(self, config: dict[str, Any], input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        scope = _scope(input_data, context)
        query = dict(config.get("query") or {})
        if config.get("filter_template"):
            query["$filter"] = render_template(config["filter_template"], scope)
        if config.get("select"):
            query["$select"] = config["select"] if isinstance(config["select"], str) else ",".join(config["select"])
        query.setdefault("$top", int(config.get("top") or 1))
        return query

    def _validate_input(self, resolver: ResolverDefinitionV2, input_data: dict[str, Any]) -> str | None:
        if not isinstance(input_data, dict):
            return "Resolver input must be an object"
        schema = resolver.input_schema_json or {}
        required = schema.get("required") if isinstance(schema.get("required"), list) else []
        missing = [field for field in required if input_data.get(str(field)) in (None, "")]
        if missing:
            return f"Missing required resolver input fields: {', '.join(map(str, missing))}"
        any_of = schema.get("anyOf") if isinstance(schema.get("anyOf"), list) else []
        if any_of and not any(input_data.get(str(field)) not in (None, "") for field in any_of):
            return f"At least one resolver input field is required: {', '.join(map(str, any_of))}"
        return None

    def _error(self, resolver: ResolverDefinitionV2, code: str, message: str, artifacts: list[ResolverArtifact], *, cache_status: str = "disabled") -> ResolverResult:
        return ResolverResult(success=False, resolver_code=resolver.resolver_code, object_type=resolver.object_type, cache_status=cache_status, source={"type": resolver.strategy}, error_code=code, error_message=message, artifacts=artifacts)


def _artifact(name: str, type_: str, payload: dict[str, Any]) -> ResolverArtifact:
    return ResolverArtifact(name=name, type=type_, payload=payload)


def _scope(input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return build_runtime_scope(request_body=context.get("request") if isinstance(context.get("request"), dict) else {}, variables={"input": input_data, **context}, context=context)


def _entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    entries = config.get("entries") if isinstance(config.get("entries"), list) else []
    static_map = config.get("map") if isinstance(config.get("map"), dict) else {}
    if static_map:
        key_field = str(config.get("key_field") or "key")
        entries.extend({"match": {key_field: key}, "object": value} for key, value in static_map.items() if isinstance(value, dict))
    return [entry for entry in entries if isinstance(entry, dict)]


def _entry_matches(entry: dict[str, Any], input_data: dict[str, Any]) -> bool:
    match = entry.get("match") if isinstance(entry.get("match"), dict) else {}
    if match:
        return all(str(input_data.get(key, "")) == str(value) for key, value in match.items())
    key_field = entry.get("key_field")
    key = entry.get("key")
    return bool(key_field and str(input_data.get(str(key_field), "")) == str(key))


def _render_mapping(mapping: Any, input_data: dict[str, Any], context: dict[str, Any]) -> Any:
    if isinstance(mapping, dict):
        return {key: _render_mapping(value, input_data, context) for key, value in mapping.items()}
    if isinstance(mapping, list):
        return [_render_mapping(item, input_data, context) for item in mapping]
    if isinstance(mapping, str):
        if "{{" in mapping:
            return render_template(mapping, _scope(input_data, context))
        if mapping.startswith("input."):
            try:
                return resolve_path({"input": input_data}, mapping)
            except PathResolutionError:
                return None
    return mapping


def _map_object(source: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    if not mapping:
        return dict(source)
    result: dict[str, Any] = {}
    for target, source_path in mapping.items():
        if isinstance(source_path, str):
            try:
                result[target] = resolve_path(source, source_path)
            except PathResolutionError:
                result[target] = source.get(source_path)
        else:
            result[target] = source_path
    return result


def _normalize_object(resolver: ResolverDefinitionV2, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.setdefault("object_type", resolver.object_type)
    return result


def _safe_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {"match": entry.get("match"), "has_object": isinstance(entry.get("object") or entry.get("value"), dict)}


def _mock_odata_items(config: dict[str, Any], connector_config: dict[str, Any]) -> list[dict[str, Any]] | None:
    if isinstance(config.get("mock_items"), list):
        return [item for item in config["mock_items"] if isinstance(item, dict)]
    mock_odata = (connector_config or {}).get("mock_odata") or {}
    items = mock_odata.get(config.get("resource")) if isinstance(mock_odata, dict) else None
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else None


def _filter_mock_items(items: list[dict[str, Any]], input_data: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    match_fields = config.get("mock_match_fields") or config.get("key_fields") or []
    if not isinstance(match_fields, list) or not match_fields:
        return items
    result = []
    for item in items:
        for field in match_fields:
            item_value = item.get(str(field)) or item.get(str(field).capitalize())
            if item_value is not None and str(item_value) in {str(value) for value in input_data.values() if value not in (None, "")}:
                result.append(item)
                break
    return result
