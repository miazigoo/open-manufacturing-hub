from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.enums import AuditActorType
from app.core.database import get_session
from app.packages_auth import repository, service
from app.packages_auth.dependencies import current_user_dep
from app.packages_auth.schemas import AuthSessionRead, AuthSettingsPatch, AuthSettingsRead, AuthState, AuthUserRead, LoginRequest, PasswordChangeRequest, PasswordRecoveryRequest, UserCreate, UserCreated, UserPatch

router = APIRouter(prefix="/api/auth", tags=["auth"])


def created_payload(user, keys: list[str]) -> dict:
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "recovery_keys": keys}


@router.get("/state", response_model=AuthState)
async def auth_state(request: Request, session: AsyncSession = Depends(get_session)):
    return await service.state(session, request)


@router.post("/bootstrap", response_model=UserCreated)
async def bootstrap(payload: UserCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    user, keys = await service.bootstrap(session, payload)
    await audit_service.record_change(session, request=http_request, actor={"actor_type": AuditActorType.SYSTEM}, action="user.created", category="users", object_type="auth_user", object_id=user.id, object_name=user.username, before=None, after=audit_service.snapshot_model(user), summary=f"Initial auth user {user.username} created", details={"bootstrap": True, "recovery_keys_issued": len(keys)})
    await session.commit()
    return created_payload(user, keys)


@router.post("/login", response_model=AuthUserRead)
async def login(payload: LoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    user = await service.login(session, payload, request, response)
    await audit_service.record_action(session, request=request, actor={"actor_type": AuditActorType.USER, "actor_user_id": user.id, "actor_username": user.username, "actor_display_name": user.display_name}, action="auth.login", category="auth", object_type="auth_user", object_id=user.id, object_name=user.username, summary=f"User {user.username} logged in")
    await session.commit()
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    user = await service.current_user(session, request)
    await service.logout(session, request, response)
    await audit_service.record_action(session, request=request, actor={"actor_type": AuditActorType.USER if user else AuditActorType.UNKNOWN, "actor_user_id": getattr(user, "id", None), "actor_username": getattr(user, "username", None), "actor_display_name": getattr(user, "display_name", None)}, action="auth.logout", category="auth", object_type="auth_user" if user else None, object_id=getattr(user, "id", None), object_name=getattr(user, "username", None), summary=f"User {user.username} logged out" if user else "Anonymous session logout")
    await session.commit()
    response.status_code = 204
    return response


@router.post("/recover-password", status_code=204)
async def recover_password(payload: PasswordRecoveryRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    await service.recover_password(session, payload.username, payload.recovery_key, payload.new_password)
    await audit_service.record_action(session, request=http_request, actor={"actor_type": AuditActorType.UNKNOWN, "actor_username": payload.username}, action="auth.recovery_key_used", category="auth", object_type="auth_user", object_name=payload.username, summary=f"Recovery key used for {payload.username}", details={"username": payload.username})
    await session.commit()
    return Response(status_code=204)


@router.get("/me", response_model=AuthUserRead)
async def me(user=Depends(current_user_dep)):
    return user


@router.post("/change-password", status_code=204)
async def change_password(payload: PasswordChangeRequest, http_request: Request, user=Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    await service.change_password(session, user, payload.current_password, payload.new_password)
    await audit_service.record_action(session, request=http_request, actor={"actor_type": AuditActorType.USER, "actor_user_id": user.id, "actor_username": user.username, "actor_display_name": user.display_name}, action="auth.password_changed", category="auth", object_type="auth_user", object_id=user.id, object_name=user.username, summary=f"User {user.username} changed password")
    await session.commit()
    return Response(status_code=204)


@router.get("/users", response_model=list[AuthUserRead])
async def users(_: object = Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    return await repository.list_users(session)


@router.post("/users", response_model=UserCreated)
async def create_user(payload: UserCreate, http_request: Request, actor=Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    user, keys = await service.create_user(session, payload)
    await audit_service.record_change(session, request=http_request, actor={"actor_type": AuditActorType.USER, "actor_user_id": actor.id, "actor_username": actor.username, "actor_display_name": actor.display_name}, action="user.created", category="users", object_type="auth_user", object_id=user.id, object_name=user.username, before=None, after=audit_service.snapshot_model(user), summary=f"User {user.username} created", details={"recovery_keys_issued": len(keys)})
    await session.commit()
    return created_payload(user, keys)


@router.get("/users/{user_id}", response_model=AuthUserRead)
async def get_user(user_id: UUID, _: object = Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    user = await repository.get_user(session, user_id)
    if user is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("User not found")
    return user


@router.patch("/users/{user_id}", response_model=AuthUserRead)
async def patch_user(user_id: UUID, payload: UserPatch, http_request: Request, actor=Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    existing = await repository.get_user(session, user_id)
    before = audit_service.snapshot_model(existing) if existing else None
    user = await service.patch_user(session, user_id, payload)
    await audit_service.record_change(session, request=http_request, actor={"actor_type": AuditActorType.USER, "actor_user_id": actor.id, "actor_username": actor.username, "actor_display_name": actor.display_name}, action="user.updated", category="users", object_type="auth_user", object_id=user.id, object_name=user.username, before=before, after=audit_service.snapshot_model(user), summary=f"User {user.username} updated")
    await session.commit()
    return user


@router.post("/users/{user_id}/disable", response_model=AuthUserRead)
async def disable_user(user_id: UUID, http_request: Request, actor=Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    existing = await repository.get_user(session, user_id)
    before = audit_service.snapshot_model(existing) if existing else None
    user = await service.set_user_enabled(session, user_id, False)
    await audit_service.record_change(session, request=http_request, actor={"actor_type": AuditActorType.USER, "actor_user_id": actor.id, "actor_username": actor.username, "actor_display_name": actor.display_name}, action="user.disabled", category="users", object_type="auth_user", object_id=user.id, object_name=user.username, before=before, after=audit_service.snapshot_model(user), summary=f"User {user.username} disabled")
    await session.commit()
    return user


@router.post("/users/{user_id}/enable", response_model=AuthUserRead)
async def enable_user(user_id: UUID, http_request: Request, actor=Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    existing = await repository.get_user(session, user_id)
    before = audit_service.snapshot_model(existing) if existing else None
    user = await service.set_user_enabled(session, user_id, True)
    await audit_service.record_change(session, request=http_request, actor={"actor_type": AuditActorType.USER, "actor_user_id": actor.id, "actor_username": actor.username, "actor_display_name": actor.display_name}, action="user.enabled", category="users", object_type="auth_user", object_id=user.id, object_name=user.username, before=before, after=audit_service.snapshot_model(user), summary=f"User {user.username} enabled")
    await session.commit()
    return user


@router.post("/users/{user_id}/reset-recovery-keys")
async def reset_keys(user_id: UUID, http_request: Request, actor=Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    keys = await service.reset_recovery_keys(session, user_id)
    target = await repository.get_user(session, user_id)
    await audit_service.record_action(session, request=http_request, actor={"actor_type": AuditActorType.USER, "actor_user_id": actor.id, "actor_username": actor.username, "actor_display_name": actor.display_name}, action="user.recovery_keys_reset", category="users", object_type="auth_user", object_id=user_id, object_name=target.username if target else None, summary=f"Recovery keys reset for {target.username if target else user_id}", details={"recovery_keys_issued": len(keys)})
    await session.commit()
    return {"recovery_keys": keys}


@router.get("/sessions", response_model=list[AuthSessionRead])
async def sessions(_: object = Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    return await repository.list_sessions(session)


@router.post("/sessions/{session_id}/revoke", status_code=204)
async def revoke_session(session_id: UUID, _: object = Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    item = await repository.get_session(session, session_id)
    if item is not None:
        item.revoked_at = service.now_utc()
    await session.commit()
    return Response(status_code=204)


@router.get("/settings", response_model=AuthSettingsRead)
async def get_settings(_: object = Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    return await service.settings(session)


@router.patch("/settings", response_model=AuthSettingsRead)
async def patch_settings(payload: AuthSettingsPatch, _: object = Depends(current_user_dep), session: AsyncSession = Depends(get_session)):
    item = await service.update_settings(session, payload)
    await session.commit()
    return item
