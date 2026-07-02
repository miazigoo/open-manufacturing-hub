from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact, content_hash, content_size
from app.artifacts.repository import get_artifact
from app.core.errors import NotFoundError


async def create_artifact(
    session: AsyncSession,
    *,
    event_id: UUID,
    run_id: UUID,
    step_id: UUID | None,
    artifact_type: str,
    name: str,
    content: dict[str, Any],
) -> Artifact:
    artifact = Artifact(
        event_id=event_id,
        run_id=run_id,
        step_id=step_id,
        artifact_type=artifact_type,
        name=name,
        content_json=content,
        content_hash=content_hash(content),
        size_bytes=content_size(content),
    )
    session.add(artifact)
    await session.flush()
    return artifact


async def get_artifact_or_404(session: AsyncSession, artifact_id: UUID) -> Artifact:
    artifact = await get_artifact(session, artifact_id)
    if artifact is None:
        raise NotFoundError("Artifact not found")
    return artifact


def diff_json(left: dict[str, Any], right: dict[str, Any]) -> dict[str, dict[str, Any]]:
    added: dict[str, Any] = {}
    removed: dict[str, Any] = {}
    changed: dict[str, dict[str, Any]] = {}

    for key in sorted(right.keys() - left.keys()):
        added[key] = right[key]
    for key in sorted(left.keys() - right.keys()):
        removed[key] = left[key]
    for key in sorted(left.keys() & right.keys()):
        if left[key] != right[key]:
            changed[key] = {"from": left[key], "to": right[key]}

    return {"added": added, "removed": removed, "changed": changed}


async def diff_artifacts(session: AsyncSession, artifact_id: UUID, compare_with: UUID) -> dict[str, Any]:
    left = await get_artifact_or_404(session, artifact_id)
    right = await get_artifact_or_404(session, compare_with)
    diff = diff_json(left.content_json, right.content_json)
    return {"artifact_id": artifact_id, "compare_with": compare_with, **diff}
