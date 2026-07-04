from __future__ import annotations

from fastapi import APIRouter

from app.transforms.engine import engine
from app.transforms.registry import registry
from app.transforms.schemas import TransformDefinition, TransformTestRequest, TransformTestResponse

router = APIRouter(prefix="/api/transforms", tags=["transforms"])


@router.get("", response_model=list[TransformDefinition])
async def list_transforms() -> list[TransformDefinition]:
    return registry.list()


@router.post("/test", response_model=TransformTestResponse)
async def test_transform(request: TransformTestRequest) -> TransformTestResponse:
    result = engine.apply_chain(request.value, request.chain, request.context)
    return TransformTestResponse(success=result.success, result=result.value, error_code=result.error_code, error_message=result.error_message, trace=result.trace)
