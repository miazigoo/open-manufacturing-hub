from __future__ import annotations

from app.business_objects.registry import registry
from app.business_objects.schemas import BusinessObjectSchema


def list_business_objects() -> list[BusinessObjectSchema]:
    return registry.list()


def get_business_object(object_type: str) -> BusinessObjectSchema:
    return registry.get(object_type)
