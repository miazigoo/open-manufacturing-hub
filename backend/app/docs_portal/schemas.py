from __future__ import annotations

from pydantic import BaseModel, Field


class DocsPageSummary(BaseModel):
    id: str
    package_id: str
    section_id: str
    slug: str
    title: str
    description: str
    route: str
    updated_at: str


class DocsSectionRead(BaseModel):
    id: str
    package_id: str
    title: str
    description: str
    pages: list[DocsPageSummary] = Field(default_factory=list)


class DocsPackageRead(BaseModel):
    id: str
    title: str
    description: str
    route: str
    sections: list[DocsSectionRead] = Field(default_factory=list)


class DocsIndexRead(BaseModel):
    language: str
    fallback_language: str | None = None
    packages: list[DocsPackageRead] = Field(default_factory=list)


class DocsPageRead(DocsPageSummary):
    markdown: str
    translation_status: str = "complete"


class DocsPdfExportStatus(BaseModel):
    error: str
    message: str
    language: str
    package_id: str | None = None
    planned: bool = True
