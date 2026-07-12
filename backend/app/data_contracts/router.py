from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.data_contracts import service
from app.data_contracts.schemas import DataContractCreate, DataContractPatch, DataContractRead

router = APIRouter(prefix="/api/data-contracts", tags=["data-contracts"])


@router.get("", response_model=list[DataContractRead])
async def list_contracts(kind: str | None = None, owner_type: str | None = None, owner_id: UUID | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_contracts(session, kind=kind, owner_type=owner_type, owner_id=owner_id)


@router.post("", response_model=DataContractRead)
async def create_contract(payload: DataContractCreate, session: AsyncSession = Depends(get_session)):
    contract = await service.create_contract(session, payload)
    await session.commit()
    return contract


@router.get("/{contract_id}", response_model=DataContractRead)
async def get_contract(contract_id: UUID, session: AsyncSession = Depends(get_session)):
    return service.read_contract(await service.get_contract_or_404(session, contract_id))


@router.patch("/{contract_id}", response_model=DataContractRead)
async def patch_contract(contract_id: UUID, payload: DataContractPatch, session: AsyncSession = Depends(get_session)):
    contract = await service.patch_contract(session, contract_id, payload)
    await session.commit()
    return contract


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(contract_id: UUID, session: AsyncSession = Depends(get_session)):
    await service.delete_contract(session, contract_id)
    await session.commit()
    return Response(status_code=204)
