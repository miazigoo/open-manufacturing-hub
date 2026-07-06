from __future__ import annotations
import json
import re
from typing import Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url
from app.connectors.builtin.onec.odata import read_odata
from app.connectors.models import ConnectorInstance
from app.core.errors import BadRequestError, NotFoundError
from app.integration_bus.models import ODataLookupTemplate
from app.odata_explorer.schemas import ODataLookupCreateRequest, ODataQueryRequest
from app.packages_training.mock_odata import metadata_xml, query_mock_odata
from app.secrets.service import SecretResolver

DEFAULT_RESOURCES = ["Catalog_Контрагенты", "Catalog_Номенклатура", "Document_ЗаказКлиента", "InformationRegister_ПулКодовМаркировкиСУЗ"]

async def resources(session: AsyncSession, connector_id: UUID) -> dict[str, Any]:
    connector = await _onec_connector(session, connector_id)
    config = await SecretResolver(session).resolve_config(connector.config_json)
    mock_odata = config.get("mock_odata") if isinstance(config.get("mock_odata"), dict) else None
    if mock_odata:
        return {"connector_id": connector_id, "resources": sorted(mock_odata.keys()), "metadata_preview": metadata_xml(mock_odata)[:4000], "fallback": False}
    base_url = str(config.get("base_url") or "")
    if not base_url:
        return {"connector_id": connector_id, "resources": DEFAULT_RESOURCES, "metadata_preview": None, "fallback": True}
    client = OneCHTTPClient(config)
    response, _, error_code, _ = await client.request("GET", join_url(base_url, "$metadata"))
    if error_code or response is None:
        return {"connector_id": connector_id, "resources": DEFAULT_RESOURCES, "metadata_preview": None, "fallback": True}
    text = response.text
    found = sorted(set(re.findall(r'EntitySet\s+Name="([^"]+)"', text) + re.findall(r'<EntityType\s+Name="([^"]+)"', text)))
    return {"connector_id": connector_id, "resources": found or DEFAULT_RESOURCES, "metadata_preview": text[:4000], "fallback": not bool(found)}

async def query(session: AsyncSession, connector_id: UUID, request: ODataQueryRequest) -> dict[str, Any]:
    connector = await _onec_connector(session, connector_id)
    params: dict[str, Any] = {}
    if request.top:
        params["$top"] = request.top
    if request.filter:
        params["$filter"] = request.filter
    if request.select:
        params["$select"] = request.select
    if request.orderby:
        params["$orderby"] = request.orderby
    config = await SecretResolver(session).resolve_config(connector.config_json)
    mock_odata = config.get("mock_odata") if isinstance(config.get("mock_odata"), dict) else None
    if mock_odata:
        response = query_mock_odata(mock_odata, request.resource, params)
        items = response.get("value") if isinstance(response.get("value"), list) else []
        return {"request_url": f"mock://training-odata/{request.resource}", "request": {"resource": request.resource, "params": params}, "response": response, "items": items, "count": len(items), "artifact_ids": {}}
    if not request.paginate:
        config = {**config, "odata": {**(config.get("odata") or {}), "max_pages": 1}}
    result = await read_odata(config, request.resource, params)
    if not result.success:
        raise BadRequestError(_odata_error_message(result.error_message or result.error_code or "ODATA_QUERY_FAILED", result.request_payload, result.response_payload))
    return {"request_url": (result.request_payload or {}).get("url"), "request": result.request_payload or {}, "response": result.response_payload or {}, "items": result.items, "count": len(result.items), "artifact_ids": {}}

async def create_lookup(session: AsyncSession, connector_id: UUID, request: ODataLookupCreateRequest) -> ODataLookupTemplate:
    await _onec_connector(session, connector_id)
    template = ODataLookupTemplate(connector_id=connector_id, **request.model_dump())
    session.add(template)
    await session.flush()
    return template

async def _onec_connector(session: AsyncSession, connector_id: UUID) -> ConnectorInstance:
    connector = await session.get(ConnectorInstance, connector_id)
    if connector is None:
        raise NotFoundError("Connector not found")
    if connector.connector_type != "onec":
        raise BadRequestError("Connector must be connector_type=onec")
    return connector

def _odata_error_message(message: str, request_payload: dict[str, Any] | None, response_payload: dict[str, Any] | None) -> str:
    parts = [message]
    requests = (request_payload or {}).get("requests")
    if isinstance(requests, list) and requests:
        first_request = requests[0]
        if isinstance(first_request, dict):
            url = first_request.get("url")
            params = first_request.get("params")
            if url:
                parts.append(f"Request: {url}")
            if params:
                parts.append(f"Params: {_short_json(params)}")
    responses = (response_payload or {}).get("responses")
    if isinstance(responses, list) and responses:
        first_response = responses[0]
        if isinstance(first_response, dict):
            status_code = first_response.get("status_code")
            body = first_response.get("body")
            if status_code:
                parts.append(f"1C status: {status_code}")
            if body is not None:
                parts.append(f"1C response: {_short_json(body)}")
    return "\n".join(parts)

def _short_json(value: Any, limit: int = 1200) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False)
    except TypeError:
        text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."
