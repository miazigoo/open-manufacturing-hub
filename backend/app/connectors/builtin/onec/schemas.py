from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OneCReadResult:
    success: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    request_payload: dict[str, Any] = field(default_factory=dict)
    response_payload: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
