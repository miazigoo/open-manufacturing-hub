from __future__ import annotations

import hashlib
from typing import Any

from app.xml_toolkit.parser import parse_xml
from app.xml_toolkit.paths import extract_fields
from app.xml_toolkit.renderer import XmlTemplateError, render_xml_template
from app.xml_toolkit.schemas import (
    XmlExtractField,
    XmlExtractResponse,
    XmlParseResponse,
    XmlRawForwardPreviewResponse,
    XmlRenderResponse,
)


def parse(raw_xml: str) -> XmlParseResponse:
    return parse_xml(raw_xml)


def extract(raw_xml: str, fields: list[XmlExtractField]) -> XmlExtractResponse:
    parsed = parse(raw_xml)
    values, errors = extract_fields(raw_xml, [field.model_dump() for field in fields]) if parsed.success else ({}, [{"code": "XML_PARSE_FAILED", "message": "; ".join(parsed.errors)}])
    return XmlExtractResponse(success=not errors and parsed.success, values=values, errors=errors, parsed=parsed)


def render(template: str, variables: dict[str, Any], *, validate_xml: bool = True) -> XmlRenderResponse:
    try:
        return XmlRenderResponse(success=True, rendered=render_xml_template(template, variables, validate_xml=validate_xml), errors=[])
    except XmlTemplateError as exc:
        return XmlRenderResponse(success=False, rendered=None, errors=[str(exc)])


def raw_forward_preview(raw_xml: str, forwarded_xml: str | None = None) -> XmlRawForwardPreviewResponse:
    forwarded = forwarded_xml if forwarded_xml is not None else raw_xml
    input_sha = _sha(raw_xml)
    forwarded_sha = _sha(forwarded)
    return XmlRawForwardPreviewResponse(input_sha256=input_sha, forwarded_sha256=forwarded_sha, forwarded_unchanged=input_sha == forwarded_sha, size_bytes=len(raw_xml.encode("utf-8")))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
