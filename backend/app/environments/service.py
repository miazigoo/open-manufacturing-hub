from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.environments import repository
from app.environments.models import EnvironmentProfile, EnvironmentVariable
from app.environments.schemas import EnvironmentCreate, EnvironmentPatch, EnvironmentVariableCreate, EnvironmentVariablePatch


async def list_environments(session: AsyncSession) -> list[EnvironmentProfile]:
    return await repository.list_environments(session)


async def get_environment_or_404(session: AsyncSession, environment_id: UUID) -> EnvironmentProfile:
    item = await repository.get_environment(session, environment_id)
    if item is None:
        raise NotFoundError("Environment not found")
    return item


async def current(session: AsyncSession) -> EnvironmentProfile | None:
    return await repository.current_environment(session)


async def create_environment(session: AsyncSession, request: EnvironmentCreate, *, http_request: Request | None = None) -> EnvironmentProfile:
    if await repository.get_by_code(session, request.code):
        raise BadRequestError("ENVIRONMENT_CODE_EXISTS")
    item = EnvironmentProfile(
        name=request.name,
        code=request.code,
        environment_type=request.environment_type,
        description=request.description,
        is_current=False,
        base_url=request.base_url,
        variables=[EnvironmentVariable(**variable.model_dump()) for variable in request.variables],
    )
    session.add(item)
    await session.flush()
    if request.is_current:
        await set_current(session, item.id, http_request=http_request, record=False)
    await session.flush()
    await audit_service.record_action(session, request=http_request, action="environment.created", category="environments", object_type="environment", object_id=item.id, object_name=item.name, summary=f"Environment created: {item.name}", details={"code": item.code, "environment_type": item.environment_type.value})
    return item


async def patch_environment(session: AsyncSession, environment_id: UUID, request: EnvironmentPatch, *, http_request: Request | None = None) -> EnvironmentProfile:
    item = await get_environment_or_404(session, environment_id)
    before = audit_service.snapshot_model(item)
    data = request.model_dump(exclude_unset=True)
    set_current_requested = data.pop("is_current", None)
    if "code" in data and data["code"] != item.code and await repository.get_by_code(session, data["code"]):
        raise BadRequestError("ENVIRONMENT_CODE_EXISTS")
    for key, value in data.items():
        setattr(item, key, value)
    if set_current_requested is True:
        await set_current(session, item.id, http_request=http_request, record=False)
    elif set_current_requested is False:
        item.is_current = False
    await session.flush()
    await audit_service.record_change(session, request=http_request, action="environment.updated", category="environments", object_type="environment", object_id=item.id, object_name=item.name, before=before, after=audit_service.snapshot_model(item), summary=f"Environment updated: {item.name}")
    return item


async def set_current(session: AsyncSession, environment_id: UUID, *, http_request: Request | None = None, record: bool = True) -> EnvironmentProfile:
    item = await get_environment_or_404(session, environment_id)
    await session.execute(update(EnvironmentProfile).values(is_current=False))
    item.is_current = True
    await session.flush()
    if record:
        await audit_service.record_action(session, request=http_request, action="environment.set_current", category="environments", object_type="environment", object_id=item.id, object_name=item.name, summary=f"Current environment set: {item.name}", details={"code": item.code, "environment_type": item.environment_type.value})
    return item


async def delete_environment(session: AsyncSession, environment_id: UUID, *, http_request: Request | None = None) -> None:
    item = await get_environment_or_404(session, environment_id)
    if item.is_current:
        raise BadRequestError("CURRENT_ENVIRONMENT_CANNOT_BE_DELETED")
    await audit_service.record_action(session, request=http_request, action="environment.deleted", category="environments", object_type="environment", object_id=item.id, object_name=item.name, summary=f"Environment deleted: {item.name}")
    await session.delete(item)
    await session.flush()


async def upsert_variable(session: AsyncSession, environment_id: UUID, request: EnvironmentVariableCreate, *, http_request: Request | None = None) -> EnvironmentVariable:
    environment = await get_environment_or_404(session, environment_id)
    item = await repository.get_variable(session, environment_id, request.key)
    action = "environment_variable.created"
    before = None
    if item is None:
        item = EnvironmentVariable(environment_id=environment_id, **request.model_dump())
        session.add(item)
    else:
        before = _variable_snapshot(item)
        for key, value in request.model_dump().items():
            setattr(item, key, value)
        action = "environment_variable.updated"
    await session.flush()
    await audit_service.record_change(session, request=http_request, action=action, category="environments", object_type="environment_variable", object_id=item.id, object_name=item.key, before=before, after=_variable_snapshot(item), summary=f"Environment variable {item.key} saved for {environment.name}")
    return item


async def patch_variable(session: AsyncSession, environment_id: UUID, key: str, request: EnvironmentVariablePatch, *, http_request: Request | None = None) -> EnvironmentVariable:
    await get_environment_or_404(session, environment_id)
    item = await repository.get_variable(session, environment_id, key)
    if item is None:
        raise NotFoundError("Environment variable not found")
    before = _variable_snapshot(item)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.flush()
    await audit_service.record_change(session, request=http_request, action="environment_variable.updated", category="environments", object_type="environment_variable", object_id=item.id, object_name=item.key, before=before, after=_variable_snapshot(item), summary=f"Environment variable updated: {item.key}")
    return item


async def delete_variable(session: AsyncSession, environment_id: UUID, key: str, *, http_request: Request | None = None) -> None:
    item = await repository.get_variable(session, environment_id, key)
    if item is None:
        raise NotFoundError("Environment variable not found")
    await audit_service.record_action(session, request=http_request, action="environment_variable.deleted", category="environments", object_type="environment_variable", object_id=item.id, object_name=item.key, summary=f"Environment variable deleted: {item.key}")
    await session.delete(item)
    await session.flush()


class EnvironmentResolver:
    def __init__(self, session: AsyncSession, environment: EnvironmentProfile | None = None) -> None:
        self.session = session
        self.environment = environment
        self._variables: dict[str, EnvironmentVariable] | None = None

    async def resolve_config(self, config: dict[str, Any], environment: EnvironmentProfile | None = None) -> dict[str, Any]:
        resolved = await self.resolve_value(config, environment=environment)
        return resolved if isinstance(resolved, dict) else {}

    async def resolve_value(self, value: Any, environment: EnvironmentProfile | None = None) -> Any:
        if environment is not None:
            self.environment = environment
            self._variables = None
        if self.environment is None:
            self.environment = await current(self.session)
        if isinstance(value, dict) and set(value.keys()) == {"$env"}:
            return await self._resolve_env(str(value["$env"]))
        if isinstance(value, dict):
            return {str(key): await self.resolve_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [await self.resolve_value(item) for item in value]
        return value

    async def _resolve_env(self, key: str) -> Any:
        if self.environment is None:
            raise BadRequestError(f"ENVIRONMENT_NOT_SET_FOR_VARIABLE: {key}")
        if self._variables is None:
            self._variables = {item.key: item for item in await repository.variables_for_environment(self.session, self.environment.id)}
        variable = self._variables.get(key)
        if variable is None:
            raise BadRequestError(f"ENVIRONMENT_VARIABLE_NOT_FOUND: {key}")
        if variable.secret_ref:
            return {"$secret": variable.secret_ref}
        return variable.value_json


def _variable_snapshot(item: EnvironmentVariable | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {"id": str(item.id), "environment_id": str(item.environment_id), "key": item.key, "value_json": "***REDACTED***" if item.value_json is not None else None, "secret_ref": item.secret_ref, "description": item.description}
