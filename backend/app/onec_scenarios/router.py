from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.onec_scenarios.presets import ONEC_SCENARIO_PRESETS
from app.onec_scenarios.schemas import OneCScenarioInstallRead, OneCScenarioPresetRead
from app.onec_scenarios.service import install_sales_order_demo

router = APIRouter(tags=["1c-scenarios"])


@router.get("/api/onec-scenarios/presets", response_model=list[OneCScenarioPresetRead])
async def list_presets():
    return ONEC_SCENARIO_PRESETS


@router.post("/api/onec-scenarios/install-sales-order-demo", response_model=OneCScenarioInstallRead)
async def install_demo(session: AsyncSession = Depends(get_session)):
    result = await install_sales_order_demo(session)
    await session.commit()
    return result
