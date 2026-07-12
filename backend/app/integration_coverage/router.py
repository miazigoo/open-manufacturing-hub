from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.integration_coverage import service
from app.integration_coverage.schemas import IntegrationCoverageItem, IntegrationCoverageReportResponse, IntegrationCoverageResponse, IntegrationCoverageSummary

router = APIRouter(prefix="/api/integration-coverage", tags=["integration-coverage"])


@router.get("", response_model=IntegrationCoverageResponse)
async def list_coverage(session: AsyncSession = Depends(get_session)):
    return await service.list_coverage(session)


@router.get("/summary", response_model=IntegrationCoverageSummary)
async def coverage_summary(session: AsyncSession = Depends(get_session)):
    return await service.get_summary(session)


@router.get("/report", response_model=IntegrationCoverageReportResponse)
async def coverage_report(session: AsyncSession = Depends(get_session)):
    response = await service.list_coverage(session)
    return IntegrationCoverageReportResponse(markdown=service.build_report(response.items))


@router.get("/{requirement_id}", response_model=IntegrationCoverageItem)
async def get_requirement(requirement_id: str, session: AsyncSession = Depends(get_session)):
    return await service.get_requirement(session, requirement_id)
