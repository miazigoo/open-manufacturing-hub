from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    username: str
    display_name: str | None = None


@dataclass(frozen=True)
class AuthContext:
    auth_available: bool
    auth_enabled: bool
    requires_login: bool
    bootstrap_required: bool
    user: CurrentUser | None = None
