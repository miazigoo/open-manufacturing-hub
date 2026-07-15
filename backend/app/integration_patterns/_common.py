from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.integration_bus import repository as bus_repository
from app.integration_flows import repository as flow_repository
from app.integration_master import service as master_service
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.schemas import InputContract


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def default_headers(body_type: str) -> dict[str, Any]:
    if body_type == "xml":
        return {"Content-Type": "application/xml; charset=utf-8"}
    if body_type == "raw_text":
        return {"Content-Type": "text/plain; charset=utf-8"}
    return {"Content-Type": "application/json"}


def request_variable(contract: InputContract) -> dict[str, Any]:
    if contract.input_mode == "json":
        sample = contract.sample
        if isinstance(sample, str):
            try:
                sample = json.loads(sample)
            except json.JSONDecodeError:
                sample = {"payload": sample}
        return {"body": sample if isinstance(sample, dict) else {"payload": sample}}
    if contract.input_mode == "raw_text":
        return {"body": {}, "raw_text": str(contract.sample or "")}
    return {"body": {}, "xml": str(contract.sample or "")}


async def ensure_slug_available(session: AsyncSession, slug: str) -> None:
    master_service.validate_slug(slug)
    draft_result = await session.execute(select(IntegrationMasterDraft.id).where(IntegrationMasterDraft.slug == slug).limit(1))
    if draft_result.scalar_one_or_none() is not None:
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await bus_repository.get_endpoint_by_slug(session, slug):
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await flow_repository.get_by_slug(session, slug):
        raise BadRequestError(f"Integration Flow со slug {slug} уже существует. Выберите другой slug.")
