from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.secrets import crypto, repository
from app.secrets.models import Secret
from app.secrets.redaction import collect_secret_references, is_secret_ref, raw_secret_warnings, safe_preview
from app.secrets.schemas import SecretConfigValidationResponse, SecretCreate, SecretPatch, SecretRead, SecretReferenceStatus, SecretRotateRequest


class SecretResolutionError(BadRequestError):
    pass


def as_read(secret: Secret) -> SecretRead:
    return SecretRead(
        id=secret.id,
        name=secret.name,
        description=secret.description,
        secret_type=secret.secret_type,
        value_preview=secret.value_preview,
        enabled=secret.enabled,
        reference={"$secret": secret.name},
        created_at=secret.created_at,
        updated_at=secret.updated_at,
        last_used_at=secret.last_used_at,
        rotated_at=secret.rotated_at,
        created_by=secret.created_by,
        updated_by=secret.updated_by,
    )


async def create_secret(session: AsyncSession, request: SecretCreate, *, actor: str | None = None) -> Secret:
    existing = await repository.get_by_name(session, request.name)
    if existing is not None:
        raise BadRequestError("SECRET_NAME_EXISTS")
    try:
        encrypted_value = crypto.encrypt_value(request.value)
    except crypto.SecretCryptoError as exc:
        raise BadRequestError(str(exc)) from exc
    secret = Secret(
        name=request.name,
        description=request.description,
        secret_type=request.secret_type,
        encrypted_value=encrypted_value,
        value_preview=safe_preview(request.value),
        enabled=True,
        created_by=actor,
        updated_by=actor,
    )
    session.add(secret)
    await session.flush()
    return secret


async def patch_secret(session: AsyncSession, secret_id: UUID, request: SecretPatch, *, actor: str | None = None) -> Secret:
    secret = await get_secret_or_404(session, secret_id)
    data = request.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != secret.name:
        existing = await repository.get_by_name(session, data["name"])
        if existing is not None:
            raise BadRequestError("SECRET_NAME_EXISTS")
    for key, value in data.items():
        setattr(secret, key, value)
    secret.updated_by = actor
    await session.flush()
    return secret


async def rotate_secret(session: AsyncSession, secret_id: UUID, request: SecretRotateRequest, *, actor: str | None = None) -> Secret:
    secret = await get_secret_or_404(session, secret_id)
    try:
        secret.encrypted_value = crypto.encrypt_value(request.value)
    except crypto.SecretCryptoError as exc:
        raise BadRequestError(str(exc)) from exc
    secret.value_preview = safe_preview(request.value)
    secret.rotated_at = datetime.now(timezone.utc)
    secret.updated_by = actor
    await session.flush()
    return secret


async def set_enabled(session: AsyncSession, secret_id: UUID, enabled: bool, *, actor: str | None = None) -> Secret:
    secret = await get_secret_or_404(session, secret_id)
    secret.enabled = enabled
    secret.updated_by = actor
    await session.flush()
    return secret


async def delete_secret(session: AsyncSession, secret_id: UUID) -> Secret:
    secret = await get_secret_or_404(session, secret_id)
    await session.delete(secret)
    await session.flush()
    return secret


async def get_secret_or_404(session: AsyncSession, secret_id: UUID) -> Secret:
    secret = await repository.get_secret(session, secret_id)
    if secret is None:
        raise NotFoundError("Secret not found")
    return secret


class SecretResolver:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._cache: dict[str, Secret] = {}
        self._used: set[str] = set()

    async def resolve_config(self, config: dict[str, Any]) -> dict[str, Any]:
        resolved = await self._resolve_value(config, "")
        await self.mark_used()
        return resolved if isinstance(resolved, dict) else {}

    async def resolve_value(self, value: Any) -> Any:
        resolved = await self._resolve_value(value, "")
        await self.mark_used()
        return resolved

    async def mark_used(self) -> None:
        if not self._used:
            return
        now = datetime.now(timezone.utc)
        for name in self._used:
            secret = self._cache.get(name)
            if secret is not None:
                secret.last_used_at = now
        await self.session.flush()

    async def _resolve_value(self, value: Any, path: str) -> Any:
        if is_secret_ref(value):
            return await self._decrypt_named(value["$secret"], path)
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in value.items():
                key_str = str(key)
                if key_str.endswith("_secret") and isinstance(item, str) and item:
                    result[key_str.removesuffix("_secret")] = await self._decrypt_named(item, f"{path}.{key_str}" if path else key_str)
                else:
                    result[key_str] = await self._resolve_value(item, f"{path}.{key_str}" if path else key_str)
            return result
        if isinstance(value, list):
            return [await self._resolve_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
        return value

    async def _decrypt_named(self, name: str, path: str) -> str:
        secret = await self._load(name)
        if secret is None:
            raise SecretResolutionError(f"SECRET_NOT_FOUND: {name} at {path or '$'}")
        if not secret.enabled:
            raise SecretResolutionError(f"SECRET_DISABLED: {name} at {path or '$'}")
        try:
            value = crypto.decrypt_value(secret.encrypted_value)
        except crypto.SecretDecryptError as exc:
            raise SecretResolutionError(f"SECRET_DECRYPT_FAILED: {name} at {path or '$'}") from exc
        self._used.add(name)
        return value

    async def _load(self, name: str) -> Secret | None:
        if name not in self._cache:
            secret = await repository.get_by_name(self.session, name)
            if secret is not None:
                self._cache[name] = secret
            else:
                return None
        return self._cache[name]


async def validate_config(session: AsyncSession, config: dict[str, Any]) -> SecretConfigValidationResponse:
    references: list[SecretReferenceStatus] = []
    valid = True
    for name, path in collect_secret_references(config):
        secret = await repository.get_by_name(session, name)
        if secret is None:
            status = "missing"
            preview = None
            valid = False
        elif not secret.enabled:
            status = "disabled"
            preview = secret.value_preview
            valid = False
        else:
            status = "ok"
            preview = secret.value_preview
        references.append(SecretReferenceStatus(name=name, status=status, path=path, value_preview=preview))
    warnings = raw_secret_warnings(config)
    return SecretConfigValidationResponse(valid=valid and not any(item.status != "ok" for item in references), references=references, raw_secret_warnings=warnings)


async def test_reference(session: AsyncSession, reference: dict[str, str] | str) -> dict[str, Any]:
    name = reference if isinstance(reference, str) else reference.get("$secret")
    if not name:
        return {"valid": False, "name": None, "status": "invalid", "message": "SECRET_REFERENCE_INVALID"}
    secret = await repository.get_by_name(session, name)
    if secret is None:
        return {"valid": False, "name": name, "status": "missing", "message": "SECRET_NOT_FOUND"}
    if not secret.enabled:
        return {"valid": False, "name": name, "status": "disabled", "value_preview": secret.value_preview, "message": "SECRET_DISABLED"}
    return {"valid": True, "name": name, "status": "ok", "value_preview": secret.value_preview}
