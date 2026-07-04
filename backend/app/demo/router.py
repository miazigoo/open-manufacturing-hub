from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.errors import BadRequestError, NotFoundError
from scripts.seed_demo import seed_demo

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/seed")
async def seed(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    if settings.app_env == "production" and not settings.allow_demo_seed_in_production:
        raise BadRequestError("DEMO_SEED_DISABLED_IN_PRODUCTION")
    if settings.app_env != "development" and settings.app_env != "production":
        raise NotFoundError("Demo seed endpoint is disabled")
    result = await seed_demo(session)
    await session.commit()
    return result
