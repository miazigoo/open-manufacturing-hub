from __future__ import annotations

from fastapi import APIRouter

from app.business_objects.schemas import BusinessObjectSchema
from app.business_objects.service import get_business_object, list_business_objects

router = APIRouter(prefix="/api/business-objects", tags=["business-objects"])


@router.get("", response_model=list[BusinessObjectSchema])
async def list_objects() -> list[BusinessObjectSchema]:
    return list_business_objects()


@router.get("/{object_type}", response_model=BusinessObjectSchema)
async def get_object(object_type: str) -> BusinessObjectSchema:
    return get_business_object(object_type)
