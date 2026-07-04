from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.integration_bus import repository as bus_repository
from app.integration_bus import service as bus_service
from app.integration_bus.models import IntegrationEndpoint
from app.test_console import repository
from app.test_console.models import SavedTestCase
from app.test_console.schemas import SavedTestCaseCreate, SavedTestCasePatch, TestConsoleSendRequest


async def send(session: AsyncSession, request: TestConsoleSendRequest) -> dict[str, Any]:
    endpoint = await _endpoint_from_request(session, request.endpoint_id, request.slug)
    parsed = _parsed_payload(request.input_mode, request.body_text, request.body_json)
    if request.dry_run:
        return {"success": True, "response": {"dry_run": True, "would_post": f"/api/bus/in/{endpoint.slug}", "parsed": parsed}, "event_id": None, "message_id": None, "timeline_url": None, "external_error": None, "dry_run": True}
    response = await bus_service.dispatch_parsed(session, endpoint, parsed)
    return _send_response(response)


async def create_test_case(session: AsyncSession, request: SavedTestCaseCreate) -> SavedTestCase:
    test_case = SavedTestCase(**request.model_dump())
    session.add(test_case)
    await session.flush()
    return test_case


async def patch_test_case(session: AsyncSession, test_case_id: UUID, request: SavedTestCasePatch) -> SavedTestCase:
    test_case = await get_test_case_or_404(session, test_case_id)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(test_case, key, value)
    await session.flush()
    return test_case


async def get_test_case_or_404(session: AsyncSession, test_case_id: UUID) -> SavedTestCase:
    test_case = await repository.get_test_case(session, test_case_id)
    if test_case is None:
        raise NotFoundError("Test case not found")
    return test_case


async def run_test_case(session: AsyncSession, test_case_id: UUID, dry_run: bool = False) -> dict[str, Any]:
    test_case = await get_test_case_or_404(session, test_case_id)
    if test_case.endpoint_id is None:
        raise BadRequestError("Test case is not linked to an endpoint")
    request = TestConsoleSendRequest(
        endpoint_id=test_case.endpoint_id,
        input_mode=test_case.input_mode,
        headers_json={str(k): str(v) for k, v in (test_case.headers_json or {}).items()},
        body_text=test_case.body_text,
        body_json=test_case.body_json,
        dry_run=dry_run,
    )
    response = await send(session, request)
    test_case.last_run_event_id = response.get("event_id")
    test_case.last_run_status = "dry_run" if dry_run else "success" if response.get("success") else "failed"
    await session.flush()
    return response


async def _endpoint_from_request(session: AsyncSession, endpoint_id: UUID | None, slug: str | None) -> IntegrationEndpoint:
    endpoint = await bus_repository.get_endpoint(session, endpoint_id) if endpoint_id else await bus_repository.get_endpoint_by_slug(session, slug or "")
    if endpoint is None:
        raise NotFoundError("Integration endpoint not found")
    return endpoint


def _parsed_payload(input_mode: str, body_text: str | None, body_json: dict[str, Any] | None) -> dict[str, Any]:
    if input_mode == "json":
        if body_json is not None:
            return body_json
        if body_text:
            parsed = json.loads(body_text)
            return parsed if isinstance(parsed, dict) else {"payload": parsed}
        return {}
    if input_mode == "xml":
        xml = body_text or ""
        return {"xml": xml, "payload": {"xml": xml}, "message_type": "XML", "payload_size_bytes": len(xml.encode("utf-8"))}
    if input_mode == "raw_text":
        text = body_text or ""
        return {"text": text, "payload": {"text": text}}
    return body_json or {"payload": body_text or ""}


def _send_response(response: dict[str, Any]) -> dict[str, Any]:
    success = bool(response.get("success")) if "success" in response else response.get("status") == "success" if "status" in response else response.get("accepted") is True
    return {
        "success": success,
        "response": response,
        "event_id": response.get("event_id"),
        "message_id": response.get("message_id"),
        "timeline_url": response.get("timeline_url"),
        "external_error": response.get("external_error"),
        "dry_run": False,
    }
