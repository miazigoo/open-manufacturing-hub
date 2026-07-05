from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.packages_training import service
from app.packages_training.examples import get_example, list_examples
from app.packages_training.mock_dnp import submit_marking_pool
from app.packages_training.mock_odata import metadata_xml, query_mock_odata
from app.packages_training.mock_printer import print_label
from app.packages_training.presets import ERP_ODATA, WMS_ODATA

router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/install")
async def install_training(session: AsyncSession = Depends(get_session)):
    result = await service.install_training_sandbox(session)
    await session.commit()
    return result


@router.post("/reset")
async def reset_training(session: AsyncSession = Depends(get_session)):
    result = await service.reset_sandbox(session)
    await session.commit()
    return result


@router.get("/status")
async def training_status(session: AsyncSession = Depends(get_session)):
    return await service.status(session)


@router.get("/examples")
async def training_examples():
    return list_examples()


@router.get("/examples/{example_id}")
async def training_example(example_id: str):
    example = get_example(example_id)
    if example is None:
        raise NotFoundError("Training example not found")
    return example


@router.post("/examples/{example_id}/run")
async def run_training_example(example_id: str, session: AsyncSession = Depends(get_session)):
    result = await service.run_example(session, example_id)
    await session.commit()
    return result


@router.post("/examples/{example_id}/open-test-console")
async def open_training_example(example_id: str):
    return await service.open_test_console(example_id)


@router.get("/mock-odata/{system}/odata/standard.odata/$metadata")
async def odata_metadata(system: str):
    resources = _resources(system)
    return Response(content=metadata_xml(resources, namespace=f"Training{system.upper()}"), media_type="application/xml")


@router.get("/mock-odata/{system}/odata/standard.odata/{resource}")
async def odata_resource(
    system: str,
    resource: str,
    top: int | None = Query(default=None, alias="$top"),
    skip: int | None = Query(default=None, alias="$skip"),
    filter_: str | None = Query(default=None, alias="$filter"),
    select: str | None = Query(default=None, alias="$select"),
    orderby: str | None = Query(default=None, alias="$orderby"),
):
    params: dict[str, Any] = {}
    if top is not None:
        params["$top"] = top
    if skip is not None:
        params["$skip"] = skip
    if filter_:
        params["$filter"] = filter_
    if select:
        params["$select"] = select
    if orderby:
        params["$orderby"] = orderby
    return query_mock_odata(_resources(system), resource, params)


@router.post("/mock-dnp/marking/pools")
async def mock_dnp(payload: dict[str, Any]):
    status, body = submit_marking_pool(payload)
    return JSONResponse(status_code=status, content=body)


@router.post("/mock-printer/print")
async def mock_printer(payload: dict[str, Any]):
    status, body = print_label(payload)
    return JSONResponse(status_code=status, content=body)


def _resources(system: str) -> dict[str, list[dict[str, Any]]]:
    if system == "erp":
        return ERP_ODATA
    if system == "wms":
        return WMS_ODATA
    raise NotFoundError("Training OData system not found")

