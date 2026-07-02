from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.schemas import ArtifactDiff, ArtifactRead
from app.artifacts.service import diff_artifacts, get_artifact_or_404
from app.core.database import get_session

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactRead)
async def get_artifact(artifact_id: UUID, session: AsyncSession = Depends(get_session)):
    return await get_artifact_or_404(session, artifact_id)


@router.get("/{artifact_id}/diff", response_model=ArtifactDiff)
async def diff_artifact(
    artifact_id: UUID,
    compare_with: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
):
    return await diff_artifacts(session, artifact_id, compare_with)
