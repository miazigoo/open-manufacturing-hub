from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.onboarding import service
from app.onboarding.schemas import OnboardingActionRequest, OnboardingExampleRunResponse, OnboardingStateRead, OnboardingStateResponse

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/state", response_model=OnboardingStateResponse)
async def onboarding_state(session: AsyncSession = Depends(get_session)):
    return await service.state(session)


@router.post("/complete", response_model=OnboardingStateRead)
async def complete(payload: OnboardingActionRequest, session: AsyncSession = Depends(get_session)):
    result = await service.complete(session, payload.key, payload.metadata_json)
    await session.commit()
    return result


@router.post("/skip", response_model=OnboardingStateRead)
async def skip(payload: OnboardingActionRequest, session: AsyncSession = Depends(get_session)):
    result = await service.skip(session, payload.key, payload.metadata_json)
    await session.commit()
    return result


@router.post("/reset", response_model=OnboardingStateResponse)
async def reset(payload: OnboardingActionRequest | None = None, session: AsyncSession = Depends(get_session)):
    result = await service.reset(session, payload.key if payload else None)
    await session.commit()
    return result


@router.post("/examples/{example_id}/run", response_model=OnboardingExampleRunResponse)
async def run_example(example_id: str, session: AsyncSession = Depends(get_session)):
    result = await service.run_example(session, example_id)
    await session.commit()
    return result
