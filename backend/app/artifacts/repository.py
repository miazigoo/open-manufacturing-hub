from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact


async def get_artifact(session: AsyncSession, artifact_id: UUID) -> Artifact | None:
    return await session.get(Artifact, artifact_id)


async def list_artifacts_for_run(session: AsyncSession, run_id: UUID) -> list[Artifact]:
    result = await session.execute(select(Artifact).where(Artifact.run_id == run_id))
    return list(result.scalars().all())
