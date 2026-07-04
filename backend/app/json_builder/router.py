from __future__ import annotations

from fastapi import APIRouter

from app.json_builder.engine import build_json_from_fields, build_json_from_template
from app.json_builder.schemas import JsonBuildRequest, JsonBuildResponse

router = APIRouter(prefix="/api/json-builder", tags=["json-builder"])


@router.post("/preview", response_model=JsonBuildResponse)
async def preview_json(request: JsonBuildRequest):
    result = build_json_from_template(request.template, request.scope) if request.template is not None else build_json_from_fields([item.model_dump() for item in request.fields], request.scope)
    return {"result": result}
