from __future__ import annotations

from functools import wraps
from typing import Any, Callable


def audit_action(*_: Any, **__: Any) -> Callable:
    """Marker decorator for endpoints that are audited explicitly in routers."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
