from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class XmlPathItem(BaseModel):
    path: str
    value_preview: str | None = None
    type: Literal["element", "text", "attribute"] = "text"
    repeated: bool = False


class XmlParseRequest(BaseModel):
    xml: str = Field(min_length=1)


class XmlParseResponse(BaseModel):
    success: bool
    valid: bool
    root: str | None = None
    root_name: str | None = None
    encoding_detected: str | None = None
    namespaces: dict[str, str] = Field(default_factory=dict)
    paths: list[XmlPathItem] = Field(default_factory=list)
    preview_tree: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    sha256: str
    size_bytes: int
    pretty_xml: str | None = None


class XmlExtractField(BaseModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    required: bool = False
    mode: Literal["first", "all"] = "first"


class XmlExtractRequest(BaseModel):
    xml: str = Field(min_length=1)
    fields: list[XmlExtractField] = Field(default_factory=list)


class XmlExtractResponse(BaseModel):
    success: bool
    values: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    parsed: XmlParseResponse | None = None


class XmlRenderRequest(BaseModel):
    template: str = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)
    validate_xml: bool = True


class XmlRenderResponse(BaseModel):
    success: bool
    rendered: str | None = None
    errors: list[str] = Field(default_factory=list)


class XmlRawForwardPreviewRequest(BaseModel):
    xml: str = Field(min_length=1)
    forwarded_xml: str | None = None


class XmlRawForwardPreviewResponse(BaseModel):
    input_sha256: str
    forwarded_sha256: str
    forwarded_unchanged: bool
    size_bytes: int

