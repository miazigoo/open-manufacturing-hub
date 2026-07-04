from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class XmlParseRequest(BaseModel):
    xml: str = Field(min_length=1)

class XmlParseResponse(BaseModel):
    valid: bool
    sha256: str
    size_bytes: int
    parsed: dict[str, Any] | None = None
    preview: str
    pretty_xml: str | None = None
    paths: list[str] = []
    error: str | None = None

class XmlDiffRequest(BaseModel):
    left_xml: str
    right_xml: str

class XmlDiffResponse(BaseModel):
    same_hash: bool
    left_sha256: str
    right_sha256: str
    forwarded_unchanged: bool
    diff_text: str
