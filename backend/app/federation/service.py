from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session
from app.core.errors import BadRequestError


class FederationAuthError(Exception):
    pass
from app.environments import repository as environments_repository
from app.environments.models import EnvironmentProfile, EnvironmentType, EnvironmentVariable
from app.federation.models import FederationSyncRun
from app.production.export_import import apply_import, export_objects

FEDERATION_KEYS = {
    "FEDERATION_CENTER_URL",
    "FEDERATION_TOKEN",
    "FEDERATION_ENABLED",
    "FEDERATION_SYNC_INTERVAL_SECONDS",
    "FEDERATION_LAST_APPLIED_VERSION",
}

DEFAULT_SYNC_INTERVAL_SECONDS = 300
SYNC_HTTP_TIMEOUT_SECONDS = 120


async def build_bundle(session: AsyncSession) -> dict[str, Any]:
    objects = await export_objects(session, secrets_policy="masked")
    version = await _current_version(session)
    return {
        "omh_export_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "version": version,
        "objects": objects,
        "warning": "Config bundle from the central OMH. Secret values are masked; re-enter secrets on branches after first sync.",
    }


async def _current_version(session: AsyncSession) -> str:
    from app.production.export_import import EXPORT_MODELS

    latest: datetime | None = None
    for model in EXPORT_MODELS.values():
        column = getattr(model, "updated_at", None) or getattr(model, "created_at", None)
        if column is None:
            continue
        value = (await session.execute(select(func.max(column)))).scalar_one_or_none()
        if value is not None and (latest is None or value > latest):
            latest = value
    return (latest or datetime.now(UTC)).isoformat()


async def serve_bundle(session: AsyncSession, token: str | None) -> dict[str, Any]:
    settings = await _federation_settings(session)
    expected = settings.get("FEDERATION_TOKEN") or ""
    if not expected:
        raise FederationAuthError("Раздача конфигов не настроена: задайте FEDERATION_TOKEN в переменных environment центра.")
    if token != expected:
        raise FederationAuthError("Неверный или отсутствующий X-OMH-Token.")
    return await build_bundle(session)


async def federation_status(session: AsyncSession) -> dict[str, Any]:
    settings = await _federation_settings(session)
    last_run = await _last_run(session)
    runs_count = (await session.execute(select(func.count()).select_from(FederationSyncRun))).scalar_one()
    return {
        "enabled": settings.get("FEDERATION_ENABLED") == "true",
        "center_url": settings.get("FEDERATION_CENTER_URL") or "",
        "token_set": bool(settings.get("FEDERATION_TOKEN")),
        "sync_interval_seconds": int(settings.get("FEDERATION_SYNC_INTERVAL_SECONDS") or DEFAULT_SYNC_INTERVAL_SECONDS),
        "last_applied_version": settings.get("FEDERATION_LAST_APPLIED_VERSION") or "",
        "local_version": await _current_version(session),
        "runs_count": runs_count,
        "last_run": _run_to_dict(last_run) if last_run else None,
    }


async def list_runs(session: AsyncSession, limit: int = 20) -> list[dict[str, Any]]:
    result = await session.execute(select(FederationSyncRun).order_by(FederationSyncRun.created_at.desc()).limit(min(limit, 100)))
    return [_run_to_dict(item) for item in result.scalars().all()]


def _run_to_dict(run: FederationSyncRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "direction": run.direction,
        "center_url": run.center_url,
        "version": run.version,
        "status": run.status,
        "message": run.message,
        "details_json": run.details_json,
        "created_at": run.created_at.isoformat(),
    }


async def sync_from_center(session: AsyncSession, *, triggered_by: str = "manual") -> dict[str, Any]:
    settings = await _federation_settings(session)
    center_url = (settings.get("FEDERATION_CENTER_URL") or "").rstrip("/")
    token = settings.get("FEDERATION_TOKEN") or ""
    if not center_url:
        raise BadRequestError("Не задан FEDERATION_CENTER_URL — укажите адрес центрального OMH в переменных environment.")
    run = FederationSyncRun(direction="pull", center_url=center_url, status="failed", details_json={"triggered_by": triggered_by})
    session.add(run)
    await session.flush()
    try:
        async with httpx.AsyncClient(timeout=SYNC_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{center_url}/api/federation/config-bundle", headers={"X-OMH-Token": token})
    except httpx.HTTPError as exc:
        return await _finish_run(session, run, "failed", f"Центр недоступен: {exc}")
    if response.status_code in (401, 403):
        return await _finish_run(session, run, "failed", f"Центр отклонил токен (HTTP {response.status_code}). Проверьте FEDERATION_TOKEN с двух сторон.")
    if response.status_code >= 400:
        return await _finish_run(session, run, "failed", f"Центр вернул HTTP {response.status_code}: {response.text[:300]}")
    try:
        bundle = response.json()
    except ValueError:
        return await _finish_run(session, run, "failed", "Центр вернул не-JSON ответ.")

    version = str(bundle.get("version") or "")
    last_applied = settings.get("FEDERATION_LAST_APPLIED_VERSION") or ""
    if version and version == last_applied:
        return await _finish_run(session, run, "skipped", f"Конфигурация уже актуальна (версия {version}).", version=version)

    applied = await apply_import(session, {"omh_export_version": bundle.get("omh_export_version"), "objects": bundle.get("objects") or {}}, "upsert")
    if not applied.get("applied"):
        return await _finish_run(session, run, "failed", f"Центральный бандл не применился: {applied.get('conflicts') or applied.get('warnings')}", version=version, details=applied)

    if version:
        await _set_environment_value(session, "FEDERATION_LAST_APPLIED_VERSION", version)
    run.details_json = {**run.details_json, "will_create": applied.get("will_create"), "will_update": applied.get("will_update"), "warnings": applied.get("warnings")}
    return await _finish_run(session, run, "success", f"Применена версия {version}: создано {sum((applied.get('will_create') or {}).values())}, обновлено {sum((applied.get('will_update') or {}).values())}.", version=version, details=applied)


async def _finish_run(session: AsyncSession, run: FederationSyncRun, status: str, message: str, *, version: str = "", details: dict[str, Any] | None = None) -> dict[str, Any]:
    run.status = status
    run.message = message
    if version:
        run.version = version
    if details is not None:
        run.details_json = {**run.details_json, **{key: value for key, value in details.items() if key in {"will_create", "will_update", "warnings", "conflicts"}}}
    await session.flush()
    return {"status": status, "message": message, "version": run.version, "run_id": str(run.id)}


async def _federation_settings(session: AsyncSession) -> dict[str, str]:
    settings = get_settings()
    values: dict[str, str] = {
        "FEDERATION_CENTER_URL": getattr(settings, "federation_center_url", "") or "",
        "FEDERATION_TOKEN": getattr(settings, "federation_token", "") or "",
        "FEDERATION_ENABLED": "true" if getattr(settings, "federation_enabled", False) else "false",
        "FEDERATION_SYNC_INTERVAL_SECONDS": str(getattr(settings, "federation_sync_interval_seconds", DEFAULT_SYNC_INTERVAL_SECONDS)),
        "FEDERATION_LAST_APPLIED_VERSION": "",
    }
    environment = await environments_repository.current_environment(session)
    if environment is not None:
        for item in environment.variables:
            if item.key in FEDERATION_KEYS and item.value_json is not None:
                values[item.key] = str(item.value_json)
    return values


async def _set_environment_value(session: AsyncSession, key: str, value: str) -> None:
    environment = await environments_repository.current_environment(session)
    if environment is None:
        environment = EnvironmentProfile(name="Default Environment", code="default", environment_type=EnvironmentType.DEVELOPMENT, is_current=True)
        session.add(environment)
        await session.flush()
    current = await environments_repository.get_variable(session, environment.id, key)
    if current is None:
        session.add(EnvironmentVariable(environment_id=environment.id, key=key, value_json=value))
    else:
        current.value_json = value
    await session.flush()


async def _last_run(session: AsyncSession) -> FederationSyncRun | None:
    result = await session.execute(select(FederationSyncRun).order_by(FederationSyncRun.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def federation_sync_loop(stop_event: asyncio.Event) -> None:
    """Background pull loop for branch instances. Runs while FEDERATION_ENABLED."""
    while not stop_event.is_set():
        try:
            async with async_session() as session:
                settings = await _federation_settings(session)
                enabled = settings.get("FEDERATION_ENABLED") == "true"
                interval = int(settings.get("FEDERATION_SYNC_INTERVAL_SECONDS") or DEFAULT_SYNC_INTERVAL_SECONDS)
            if enabled:
                try:
                    async with async_session() as session:
                        result = await sync_from_center(session, triggered_by="scheduler")
                        await session.commit()
                        if result["status"] == "failed":
                            print(f"[federation] sync failed: {result['message']}")
                except Exception as exc:
                    print(f"[federation] sync error: {exc}")
        except Exception:
            interval = DEFAULT_SYNC_INTERVAL_SECONDS
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue
