from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.onec_scenarios.presets import ONEC_SCENARIO_PRESETS
from app.onec_scenarios.schemas import (
    InventoryResultTestRequest,
    OneCScenarioInstallRead,
    OneCScenarioPresetRead,
    ShipmentFactTestRead,
    ShipmentFactTestRequest,
    StockBalanceTestRequest,
)
from app.onec_scenarios.service import (
    create_inventory_result_test_event,
    create_shipment_fact_test_event,
    create_stock_balance_test_event,
    install_bidirectional_demo,
    install_erp_wms_integration,
    install_sales_order_demo,
)

router = APIRouter(tags=["1c-scenarios"])


@router.get("/api/onec-scenarios/presets", response_model=list[OneCScenarioPresetRead])
async def list_presets():
    return ONEC_SCENARIO_PRESETS


@router.post("/api/onec-scenarios/install-sales-order-demo", response_model=OneCScenarioInstallRead)
async def install_demo(session: AsyncSession = Depends(get_session)):
    result = await install_sales_order_demo(session)
    await session.commit()
    return result


@router.post("/api/onec-scenarios/install-bidirectional-demo", response_model=OneCScenarioInstallRead)
async def install_bidirectional(session: AsyncSession = Depends(get_session)):
    result = await install_bidirectional_demo(session)
    await session.commit()
    return result


@router.post("/api/onec-scenarios/install-erp-wms-integration", response_model=OneCScenarioInstallRead)
async def install_full_erp_wms(session: AsyncSession = Depends(get_session)):
    result = await install_erp_wms_integration(session)
    await session.commit()
    return result


@router.post("/api/onec-scenarios/test-shipment-fact", response_model=ShipmentFactTestRead)
async def test_shipment_fact(request: ShipmentFactTestRequest, session: AsyncSession = Depends(get_session)):
    result = await create_shipment_fact_test_event(session, request.model_dump())
    await session.commit()
    return result


@router.post("/api/onec-scenarios/test-stock-balance", response_model=ShipmentFactTestRead)
async def test_stock_balance(request: StockBalanceTestRequest, session: AsyncSession = Depends(get_session)):
    result = await create_stock_balance_test_event(session, request.model_dump())
    await session.commit()
    return result


@router.post("/api/onec-scenarios/test-inventory-result", response_model=ShipmentFactTestRead)
async def test_inventory_result(request: InventoryResultTestRequest, session: AsyncSession = Depends(get_session)):
    result = await create_inventory_result_test_event(session, request.model_dump())
    await session.commit()
    return result
