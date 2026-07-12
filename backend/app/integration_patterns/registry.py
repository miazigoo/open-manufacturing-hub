from __future__ import annotations

from app.core.errors import BadRequestError, NotFoundError
from app.integration_patterns.schemas import IntegrationPattern


class IntegrationPatternRegistry:
    def __init__(self) -> None:
        self._patterns: dict[str, IntegrationPattern] = {}

    def register(self, pattern: IntegrationPattern) -> None:
        if pattern.pattern_id in self._patterns:
            raise BadRequestError(f"Duplicate integration pattern: {pattern.pattern_id}")
        self._patterns[pattern.pattern_id] = pattern

    def list(self) -> list[IntegrationPattern]:
        return sorted(self._patterns.values(), key=lambda item: (item.category, item.difficulty, item.pattern_id))

    def get(self, pattern_id: str) -> IntegrationPattern:
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise NotFoundError("Integration pattern not found")
        return pattern


registry = IntegrationPatternRegistry()
