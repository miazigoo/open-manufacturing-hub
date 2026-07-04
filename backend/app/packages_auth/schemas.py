from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuthUserRead(BaseModel):
    id: UUID
    username: str
    display_name: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class AuthSessionRead(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    model_config = ConfigDict(from_attributes=True)


class AuthSettingsRead(BaseModel):
    enabled: bool
    protect_api: bool
    protect_ui: bool
    session_ttl_days: int
    cookie_name: str


class AuthSettingsPatch(BaseModel):
    enabled: bool | None = None
    protect_api: bool | None = None
    protect_ui: bool | None = None
    session_ttl_days: int | None = None
    cookie_name: str | None = None


class AuthState(BaseModel):
    auth_available: bool
    auth_enabled: bool
    requires_login: bool
    bootstrap_required: bool
    user: AuthUserRead | None = None


class UserCreate(BaseModel):
    username: str
    display_name: str | None = None
    password: str


class UserPatch(BaseModel):
    username: str | None = None
    display_name: str | None = None
    enabled: bool | None = None


class UserCreated(BaseModel):
    id: UUID
    username: str
    display_name: str | None = None
    recovery_keys: list[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordRecoveryRequest(BaseModel):
    username: str
    recovery_key: str
    new_password: str
