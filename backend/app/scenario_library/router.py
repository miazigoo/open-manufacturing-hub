from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.integration_flows import service as flow_service
from app.scenario_library import service
from app.scenario_library.schemas import ScenarioInstallRequest, ScenarioInstallResponse, ScenarioPreview, ScenarioRead

router = APIRouter(prefix="/api/scenario-library", tags=["scenario-library"])


@router.get("", response_model=list[ScenarioRead])
async def list_scenarios():
    return service.list_scenarios()


@router.post("/marking-pool-to-internal-service/install")
async def install_marking_pool_flow(session: AsyncSession = Depends(get_session)):
    flow = await flow_service.install_marking_pool_preset(session)
    await session.commit()
    return await flow_service._read_flow(flow)


@router.post("/onec-post-two-odata-to-endpoint/install")
async def install_two_odata_to_endpoint_flow(session: AsyncSession = Depends(get_session)):
    flow = await flow_service.install_two_odata_to_endpoint_preset(session)
    await session.commit()
    return await flow_service._read_flow(flow)


@router.post("/{scenario_code}/preview", response_model=ScenarioPreview)
async def preview_scenario(scenario_code: str):
    return service.preview_scenario(scenario_code)


@router.post("/{scenario_code}/install", response_model=ScenarioInstallResponse)
async def install_scenario(scenario_code: str, request: ScenarioInstallRequest | None = None, session: AsyncSession = Depends(get_session)):
    result = await service.install_scenario(session, scenario_code, request or ScenarioInstallRequest())
    await session.commit()
    return result
