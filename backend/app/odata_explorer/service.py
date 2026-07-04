from __future__ import annotations
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
from app.secrets.service import SecretResolver

DEFAULT_RESOURCES = ["Catalog_Контрагенты", "Catalog_Номенклатура", "Document_ЗаказКлиента", "InformationRegister_ПулКодовМаркировкиСУЗ"]

async def resources(session: AsyncSession, connector_id: UUID) -> dict[str, Any]:
    connector = await _onec_connector(session, connector_id)
    config = await SecretResolver(session).resolve_config(connector.config_json)
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
    result = await read_odata(config, request.resource, params)
    if not result.success:
        raise BadRequestError(result.error_message or result.error_code or "ODATA_QUERY_FAILED")
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
