from __future__ import annotations
from fastapi import APIRouter
from app.xml_tools import service
from app.xml_tools.schemas import XmlDiffRequest, XmlDiffResponse, XmlParseRequest, XmlParseResponse

router = APIRouter(prefix="/api/xml-tools", tags=["xml-tools"])

@router.post("/parse", response_model=XmlParseResponse)
async def parse_xml(request: XmlParseRequest):
    return service.parse(request.xml)

@router.post("/diff", response_model=XmlDiffResponse)
async def diff_xml(request: XmlDiffRequest):
    return service.diff(request.left_xml, request.right_xml)
