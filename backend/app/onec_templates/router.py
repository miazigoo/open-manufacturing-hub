from fastapi import APIRouter

from app.onec_templates.schemas import OneCHTTPTemplateRead
from app.onec_templates.service import http_service_template

router = APIRouter(tags=["1c-templates"])


@router.get("/api/onec-templates/http-service", response_model=OneCHTTPTemplateRead)
async def get_http_service_template():
    return http_service_template()
