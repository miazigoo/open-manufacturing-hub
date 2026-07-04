from __future__ import annotations

from app.packages_auth.security import new_recovery_key

RECOVERY_KEY_COUNT = 5


def generate_recovery_keys(count: int = RECOVERY_KEY_COUNT) -> list[str]:
    return [new_recovery_key() for _ in range(count)]
