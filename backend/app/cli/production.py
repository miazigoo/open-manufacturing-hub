from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import async_session
from app.production import service
from app.production.schemas import ExportConfigRequest


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _print(value) -> None:
    print(json.dumps(_jsonable(value), default=str, indent=2))


async def _snapshot() -> None:
    async with async_session() as session:
        _print(await service.snapshot(session))


async def _export_config() -> None:
    async with async_session() as session:
        _, payload = await service.export_config(session, ExportConfigRequest(created_by="cli"))
        await session.commit()
        _print(payload)


async def _pre_update() -> None:
    async with async_session() as session:
        _print(await service.pre_update_check(session))


async def _post_update() -> None:
    async with async_session() as session:
        _print(await service.post_update_check(session))


async def _doctor(*, as_json: bool = False) -> None:
    from app.production import release

    async with async_session() as session:
        payload = await release.doctor(session)
        if as_json:
            _print(payload)
            return
        print("OMH Doctor")
        print(f"Status: {payload['status']} | ok={payload['summary']['ok']} warning={payload['summary']['warning']} error={payload['summary']['error']}")
        for check in payload["checks"]:
            status = check.status if hasattr(check, "status") else check.get("status")
            name = check.name if hasattr(check, "name") else check.get("name")
            message = check.message if hasattr(check, "message") else check.get("message")
            mark = "✓" if status == "ok" else "✗" if status == "error" else "⚠"
            print(f"{mark} {name}: {message or status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="OMH production safety CLI")
    parser.add_argument("command", choices=["snapshot", "export-config", "pre-update-check", "post-update-check", "doctor"])
    parser.add_argument("--json", action="store_true", help="Print JSON for commands with human output")
    args = parser.parse_args()
    if args.command == "snapshot":
        asyncio.run(_snapshot())
    elif args.command == "export-config":
        asyncio.run(_export_config())
    elif args.command == "pre-update-check":
        asyncio.run(_pre_update())
    elif args.command == "post-update-check":
        asyncio.run(_post_update())
    elif args.command == "doctor":
        asyncio.run(_doctor(as_json=args.json))


if __name__ == "__main__":
    main()
