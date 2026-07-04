from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.test_console import repository, service
from app.test_console.schemas import SavedTestCaseCreate, SavedTestCasePatch, SavedTestCaseRead, TestConsoleSendRequest, TestConsoleSendResponse

router = APIRouter(tags=["test-console"])


@router.post("/api/test-console/send", response_model=TestConsoleSendResponse)
async def send_test(request: TestConsoleSendRequest, session: AsyncSession = Depends(get_session)):
    result = await service.send(session, request)
    await session.commit()
    return result


@router.get("/api/test-cases", response_model=list[SavedTestCaseRead])
async def list_test_cases(session: AsyncSession = Depends(get_session)):
    return await repository.list_test_cases(session)


@router.post("/api/test-cases", response_model=SavedTestCaseRead)
async def create_test_case(request: SavedTestCaseCreate, session: AsyncSession = Depends(get_session)):
    test_case = await service.create_test_case(session, request)
    await session.commit()
    return test_case


@router.get("/api/test-cases/{test_case_id}", response_model=SavedTestCaseRead)
async def get_test_case(test_case_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_test_case_or_404(session, test_case_id)


@router.patch("/api/test-cases/{test_case_id}", response_model=SavedTestCaseRead)
async def patch_test_case(test_case_id: UUID, request: SavedTestCasePatch, session: AsyncSession = Depends(get_session)):
    test_case = await service.patch_test_case(session, test_case_id, request)
    await session.commit()
    return test_case


@router.delete("/api/test-cases/{test_case_id}", status_code=204)
async def delete_test_case(test_case_id: UUID, session: AsyncSession = Depends(get_session)):
    test_case = await service.get_test_case_or_404(session, test_case_id)
    await session.delete(test_case)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/test-cases/{test_case_id}/run", response_model=TestConsoleSendResponse)
async def run_test_case(test_case_id: UUID, dry_run: bool = False, session: AsyncSession = Depends(get_session)):
    result = await service.run_test_case(session, test_case_id, dry_run=dry_run)
    await session.commit()
    return result
