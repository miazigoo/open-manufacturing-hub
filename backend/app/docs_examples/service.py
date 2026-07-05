from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.integration_bus import repository as bus_repository
from app.test_console import service as test_console_service
from app.test_console.schemas import TestConsoleSendRequest

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "frontend" / "src" / "docs" / "examples" / "index.json"


@lru_cache(maxsize=1)
def _registry() -> dict[str, dict[str, Any]]:
    with REGISTRY_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise RuntimeError("Docs examples registry must be a JSON object")
    return data


def list_examples() -> list[dict[str, Any]]:
    return [_with_id(example_id, example) for example_id, example in sorted(_registry().items())]


def get_example(example_id: str) -> dict[str, Any] | None:
    example = _registry().get(example_id)
    return _with_id(example_id, example) if example else None


async def run_example(session: AsyncSession, example_id: str) -> dict[str, Any]:
    example = get_example(example_id)
    if example is None:
        raise NotFoundError("Documentation example not found")

    endpoint = await bus_repository.get_endpoint_by_slug(session, example["endpoint_slug"])
    if endpoint is None:
        return {
            "success": True,
            "example_id": example_id,
            "runnable": bool(example.get("runnable")),
            "requires_setup": True,
            "dry_run": True,
            "response": {
                "status": "requires_setup",
                "message": "Create or install the documented endpoint before running this example.",
                "endpoint": f"POST /api/bus/in/{example['endpoint_slug']}",
                "open_in_test_console": f"/test-console?exampleId={example_id}",
            },
            "event_id": None,
            "message_id": None,
            "timeline_url": None,
            "external_error": None,
        }

    request = TestConsoleSendRequest(
        endpoint_id=endpoint.id,
        input_mode=example.get("input_mode", "json"),
        headers_json={str(key): str(value) for key, value in example.get("headers", {}).items()},
        body_text=example.get("body_text") or (json.dumps(example.get("body", {}), ensure_ascii=False) if example.get("input_mode") != "json" else None),
        body_json=example.get("body") if example.get("input_mode", "json") == "json" else None,
        dry_run=False,
    )
    result = await test_console_service.send(session, request)
    return {
        "success": bool(result.get("success")),
        "example_id": example_id,
        "runnable": True,
        "requires_setup": False,
        "dry_run": bool(result.get("dry_run")),
        "response": result.get("response") or {},
        "event_id": str(result["event_id"]) if result.get("event_id") else None,
        "message_id": str(result["message_id"]) if result.get("message_id") else None,
        "timeline_url": result.get("timeline_url"),
        "external_error": result.get("external_error"),
    }


def _with_id(example_id: str, example: dict[str, Any]) -> dict[str, Any]:
    return {"id": example_id, **example}
