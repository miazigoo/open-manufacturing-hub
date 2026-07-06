from __future__ import annotations

from fastapi import APIRouter

from app.xml_toolkit import service
from app.xml_toolkit.schemas import (
    XmlExtractRequest,
    XmlExtractResponse,
    XmlParseRequest,
    XmlParseResponse,
    XmlRawForwardPreviewRequest,
    XmlRawForwardPreviewResponse,
    XmlRenderRequest,
    XmlRenderResponse,
)

router = APIRouter(prefix="/api/xml-toolkit", tags=["xml-toolkit"])


@router.post("/parse", response_model=XmlParseResponse)
async def parse_xml(request: XmlParseRequest):
    return service.parse(request.xml)


@router.post("/extract", response_model=XmlExtractResponse)
async def extract_xml(request: XmlExtractRequest):
    return service.extract(request.xml, request.fields)


@router.post("/render", response_model=XmlRenderResponse)
async def render_xml(request: XmlRenderRequest):
    return service.render(request.template, request.variables, validate_xml=request.validate_xml)


@router.post("/raw-forward-preview", response_model=XmlRawForwardPreviewResponse)
async def raw_forward_preview(request: XmlRawForwardPreviewRequest):
    return service.raw_forward_preview(request.xml, request.forwarded_xml)

