from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.core.errors import NotFoundError
from app.docs_portal import service
from app.docs_portal.schemas import DocsIndexRead, DocsPackageRead, DocsPageRead, DocsPdfExportStatus

router = APIRouter(prefix="/api/docs", tags=["docs"])


@router.get("/index", response_model=DocsIndexRead)
async def docs_index(lang: str = Query("ru", min_length=2, max_length=8)):
    return service.docs_index(lang)


@router.get("/packages", response_model=list[DocsPackageRead])
async def docs_packages(lang: str = Query("ru", min_length=2, max_length=8)):
    return service.docs_packages(lang)


@router.get("/pages/{page_id}", response_model=DocsPageRead)
async def docs_page(page_id: str, lang: str = Query("ru", min_length=2, max_length=8)):
    page = service.docs_page(page_id, lang)
    if page is None:
        raise NotFoundError("Documentation page not found")
    return page


@router.get("/export-pdf", response_model=DocsPdfExportStatus)
async def docs_export_pdf(lang: str = Query("ru", min_length=2, max_length=8), package_id: str | None = Query(None, alias="package")):
    normalized, _ = service.normalize_language(lang)
    payload = DocsPdfExportStatus(
        error="DOCS_PDF_EXPORT_NOT_IMPLEMENTED",
        message="PDF export is part of the documentation portal contract and will be implemented after HTML documentation stabilizes.",
        language=normalized,
        package_id=package_id,
    )
    return JSONResponse(status_code=501, content=payload.model_dump())
