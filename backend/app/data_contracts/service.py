from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.data_contracts.models import DataContract
from app.data_contracts.schemas import DataContractCreate, DataContractPatch, DataContractRead
from app.data_contracts.validator import extract_contract_fields, normalize_contract_data, validate_contract_data


async def list_contracts(session: AsyncSession, *, kind: str | None = None, owner_type: str | None = None, owner_id: UUID | None = None) -> list[DataContractRead]:
    stmt = select(DataContract).order_by(DataContract.name.asc())
    if kind:
        stmt = stmt.where(DataContract.kind == kind)
    if owner_type:
        stmt = stmt.where(DataContract.owner_type == owner_type)
    if owner_id:
        stmt = stmt.where(DataContract.owner_id == owner_id)
    rows = list((await session.execute(stmt)).scalars().all())
    return [_read(row) for row in rows]


async def get_contract_row(session: AsyncSession, contract_id: UUID) -> DataContract | None:
    return await session.get(DataContract, contract_id)


async def get_contract_or_404(session: AsyncSession, contract_id: UUID) -> DataContract:
    row = await get_contract_row(session, contract_id)
    if row is None:
        raise NotFoundError("Data contract not found")
    return row


async def get_contract_by_code(session: AsyncSession, code: str) -> DataContract | None:
    result = await session.execute(select(DataContract).where(DataContract.code == code))
    return result.scalar_one_or_none()


async def create_contract(session: AsyncSession, payload: DataContractCreate) -> DataContractRead:
    data = normalize_contract_data(payload.model_dump())
    validate_contract_data(data)
    row = DataContract(**data)
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise BadRequestError("Контракт с таким code уже существует.") from exc
    return _read(row)


async def upsert_contract(session: AsyncSession, payload: DataContractCreate) -> DataContract:
    data = normalize_contract_data(payload.model_dump())
    validate_contract_data(data)
    existing = await get_contract_by_code(session, data["code"])
    if existing is None:
        existing = DataContract(**data)
        session.add(existing)
    else:
        for key, value in data.items():
            setattr(existing, key, value)
    await session.flush()
    return existing


async def patch_contract(session: AsyncSession, contract_id: UUID, payload: DataContractPatch) -> DataContractRead:
    row = await get_contract_or_404(session, contract_id)
    data = normalize_contract_data(payload.model_dump(exclude_unset=True))
    validate_contract_data(data, partial=True)
    for key, value in data.items():
        setattr(row, key, value)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise BadRequestError("Контракт с таким code уже существует.") from exc
    return _read(row)


async def delete_contract(session: AsyncSession, contract_id: UUID) -> None:
    row = await get_contract_or_404(session, contract_id)
    await session.delete(row)
    await session.flush()


def read_contract(row: DataContract) -> DataContractRead:
    return _read(row)


def _read(row: DataContract) -> DataContractRead:
    return DataContractRead(
        id=row.id,
        name=row.name,
        code=row.code,
        kind=row.kind,  # type: ignore[arg-type]
        owner_type=row.owner_type,  # type: ignore[arg-type]
        owner_id=row.owner_id,
        description=row.description,
        schema_json=row.schema_json,
        example_json=row.example_json,
        fields=extract_contract_fields(row.schema_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
