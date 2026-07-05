from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.docs_examples import service
from app.docs_examples.schemas import DocsExampleRead, DocsExampleRunResponse
from app.core.errors import NotFoundError

router = APIRouter(prefix="/api/docs/examples", tags=["docs-examples"])


@router.get("", response_model=list[DocsExampleRead])
async def list_examples():
    return service.list_examples()


@router.get("/{example_id}", response_model=DocsExampleRead)
async def get_example(example_id: str):
    example = service.get_example(example_id)
    if example is None:
        raise NotFoundError("Documentation example not found")
    return example


@router.post("/{example_id}/run", response_model=DocsExampleRunResponse)
async def run_example(example_id: str, session: AsyncSession = Depends(get_session)):
    result = await service.run_example(session, example_id)
    await session.commit()
    return result
