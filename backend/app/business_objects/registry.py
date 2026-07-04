from __future__ import annotations

from app.business_objects.presets import BUSINESS_OBJECT_PRESETS
from app.business_objects.schemas import BusinessObjectSchema
from app.core.errors import NotFoundError


class BusinessObjectRegistry:
    def __init__(self) -> None:
        self._schemas = {item["object_type"]: BusinessObjectSchema(**item) for item in BUSINESS_OBJECT_PRESETS}

    def list(self) -> list[BusinessObjectSchema]:
        return sorted(self._schemas.values(), key=lambda item: item.object_type)

    def get(self, object_type: str) -> BusinessObjectSchema:
        item = self._schemas.get(object_type)
        if item is None:
            normalized = {key.lower(): key for key in self._schemas}
            real_key = normalized.get(object_type.lower())
            item = self._schemas.get(real_key) if real_key else None
        if item is None:
            raise NotFoundError(f"Business object {object_type} not found")
        return item

    def exists(self, object_type: str) -> bool:
        try:
            self.get(object_type)
            return True
        except NotFoundError:
            return False


registry = BusinessObjectRegistry()
