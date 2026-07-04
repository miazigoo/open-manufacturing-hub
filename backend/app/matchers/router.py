from __future__ import annotations

from fastapi import APIRouter

from app.matchers.engine import evaluate_matcher_group
from app.matchers.schemas import MatcherTestRequest, MatcherTestResponse

router = APIRouter(prefix="/api/matchers", tags=["matchers"])


@router.post("/test", response_model=MatcherTestResponse)
async def test_matcher(request: MatcherTestRequest):
    payload = request.payload if isinstance(request.payload, dict) else {"payload": request.payload}
    text = request.text or (request.payload if isinstance(request.payload, str) else None)
    xml = text if request.input_mode == "xml" else None
    result = evaluate_matcher_group(
        request.matcher_group.model_dump() if hasattr(request.matcher_group, "model_dump") else request.matcher_group,
        {"body": payload, "text": text, "xml": xml, "headers": request.headers, "query": request.query},
    )
    return result
