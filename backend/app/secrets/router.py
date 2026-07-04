from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.secrets import repository, service
from app.secrets.schemas import SecretConfigValidationRequest, SecretConfigValidationResponse, SecretCreate, SecretPatch, SecretRead, SecretReferenceTestRequest, SecretReferenceTestResponse, SecretRotateRequest

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


@router.get("", response_model=list[SecretRead])
async def list_secrets(session: AsyncSession = Depends(get_session)):
    return [service.as_read(secret) for secret in await repository.list_secrets(session)]


@router.post("", response_model=SecretRead)
async def create_secret(payload: SecretCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    actor = _actor_username(http_request)
    secret = await service.create_secret(session, payload, actor=actor)
    read = service.as_read(secret)
    await audit_service.record_action(session, request=http_request, action="secret.created", category="secrets", object_type="secret", object_id=secret.id, object_name=secret.name, summary=f"Secret {secret.name} created", details={"name": secret.name, "secret_type": secret.secret_type.value, "value": "***REDACTED***"})
    await session.commit()
    return read


@router.post("/test-reference", response_model=SecretReferenceTestResponse)
async def test_reference(payload: SecretReferenceTestRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_reference(session, payload.reference)


@router.post("/validate-config", response_model=SecretConfigValidationResponse)
async def validate_config(payload: SecretConfigValidationRequest, session: AsyncSession = Depends(get_session)):
    return await service.validate_config(session, payload.config)


@router.get("/{secret_id}", response_model=SecretRead)
async def get_secret(secret_id: UUID, session: AsyncSession = Depends(get_session)):
    return service.as_read(await service.get_secret_or_404(session, secret_id))


@router.patch("/{secret_id}", response_model=SecretRead)
async def patch_secret(secret_id: UUID, payload: SecretPatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = service.as_read(await service.get_secret_or_404(session, secret_id)).model_dump(mode="json")
    secret = await service.patch_secret(session, secret_id, payload, actor=_actor_username(http_request))
    after = service.as_read(secret).model_dump(mode="json")
    await audit_service.record_change(session, request=http_request, action="secret.updated", category="secrets", object_type="secret", object_id=secret.id, object_name=secret.name, before=before, after=after, summary=f"Secret {secret.name} updated")
    await session.commit()
    return service.as_read(secret)


@router.delete("/{secret_id}", status_code=204)
async def delete_secret(secret_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    secret = await service.get_secret_or_404(session, secret_id)
    before = service.as_read(secret).model_dump(mode="json")
    await audit_service.record_change(session, request=http_request, action="secret.deleted", category="secrets", object_type="secret", object_id=secret.id, object_name=secret.name, before=before, after=None, summary=f"Secret {secret.name} deleted")
    await session.delete(secret)
    await session.commit()
    return Response(status_code=204)


@router.post("/{secret_id}/rotate", response_model=SecretRead)
async def rotate_secret(secret_id: UUID, payload: SecretRotateRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    before = service.as_read(await service.get_secret_or_404(session, secret_id)).model_dump(mode="json")
    secret = await service.rotate_secret(session, secret_id, payload, actor=_actor_username(http_request))
    after = service.as_read(secret).model_dump(mode="json")
    await audit_service.record_change(session, request=http_request, action="secret.rotated", category="secrets", object_type="secret", object_id=secret.id, object_name=secret.name, before=before, after=after, summary=f"Secret {secret.name} rotated")
    await session.commit()
    return service.as_read(secret)


@router.post("/{secret_id}/disable", response_model=SecretRead)
async def disable_secret(secret_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    secret = await service.set_enabled(session, secret_id, False, actor=_actor_username(http_request))
    await audit_service.record_action(session, request=http_request, action="secret.disabled", category="secrets", object_type="secret", object_id=secret.id, object_name=secret.name, summary=f"Secret {secret.name} disabled")
    await session.commit()
    return service.as_read(secret)


@router.post("/{secret_id}/enable", response_model=SecretRead)
async def enable_secret(secret_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    secret = await service.set_enabled(session, secret_id, True, actor=_actor_username(http_request))
    await audit_service.record_action(session, request=http_request, action="secret.enabled", category="secrets", object_type="secret", object_id=secret.id, object_name=secret.name, summary=f"Secret {secret.name} enabled")
    await session.commit()
    return service.as_read(secret)


def _actor_username(request: Request) -> str | None:
    user = getattr(request.state, "auth_user", None)
    return getattr(user, "username", None)
