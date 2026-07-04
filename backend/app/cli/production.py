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


def main() -> None:
    parser = argparse.ArgumentParser(description="OMH production safety CLI")
    parser.add_argument("command", choices=["snapshot", "export-config", "pre-update-check", "post-update-check"])
    args = parser.parse_args()
    if args.command == "snapshot":
        asyncio.run(_snapshot())
    elif args.command == "export-config":
        asyncio.run(_export_config())
    elif args.command == "pre-update-check":
        asyncio.run(_pre_update())
    elif args.command == "post-update-check":
        asyncio.run(_post_update())


if __name__ == "__main__":
    main()
