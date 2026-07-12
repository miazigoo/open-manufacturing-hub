from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.data_contracts.models import DataContract
from app.data_contracts.schemas import DataContractCreate
from app.data_contracts.service import read_contract, upsert_contract
from app.mapping_center.models import MappingProfile
from app.mapping_center.presets import CONTRACT_PRESETS, MAPPING_PRESETS
from app.mapping_center.renderer import render_mapping
from app.mapping_center.schemas import (
    InstallMappingPresetsResponse,
    MappingPresetsResponse,
    MappingPreviewRequest,
    MappingProfileCreate,
    MappingProfilePatch,
    MappingProfileRead,
    MappingRenderResponse,
    MappingValidateRequest,
    MappingValidationResponse,
)
from app.mapping_center.validator import normalize_mapping_data, validate_mapping, validate_profile_data
from app.operation_catalog.models import OperationProfile


async def list_mappings(session: AsyncSession, *, operation_profile_id: UUID | None = None, target_contract_id: UUID | None = None) -> list[MappingProfileRead]:
    stmt = select(MappingProfile).order_by(MappingProfile.name.asc())
    if operation_profile_id:
        stmt = stmt.where(MappingProfile.operation_profile_id == operation_profile_id)
    if target_contract_id:
        stmt = stmt.where(MappingProfile.target_contract_id == target_contract_id)
    rows = list((await session.execute(stmt)).scalars().all())
    return await _read_many(session, rows)


async def get_mapping_row(session: AsyncSession, mapping_id: UUID) -> MappingProfile | None:
    return await session.get(MappingProfile, mapping_id)


async def get_mapping_or_404(session: AsyncSession, mapping_id: UUID) -> MappingProfile:
    row = await get_mapping_row(session, mapping_id)
    if row is None:
        raise NotFoundError("Mapping profile not found")
    return row


async def get_mapping(session: AsyncSession, mapping_id: UUID) -> MappingProfileRead:
    return (await _read_many(session, [await get_mapping_or_404(session, mapping_id)]))[0]


async def get_mapping_by_code(session: AsyncSession, code: str) -> MappingProfile | None:
    result = await session.execute(select(MappingProfile).where(MappingProfile.code == code))
    return result.scalar_one_or_none()


async def create_mapping(session: AsyncSession, payload: MappingProfileCreate) -> MappingProfileRead:
    data = normalize_mapping_data(payload.model_dump())
    validate_profile_data(data)
    await _validate_refs(session, data)
    row = MappingProfile(**data)
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise BadRequestError("Mapping profile с таким code уже существует.") from exc
    return (await _read_many(session, [row]))[0]


async def patch_mapping(session: AsyncSession, mapping_id: UUID, payload: MappingProfilePatch) -> MappingProfileRead:
    row = await get_mapping_or_404(session, mapping_id)
    data = normalize_mapping_data(payload.model_dump(exclude_unset=True))
    validate_profile_data(data, partial=True)
    await _validate_refs(session, data)
    for key, value in data.items():
        setattr(row, key, value)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise BadRequestError("Mapping profile с таким code уже существует.") from exc
    return (await _read_many(session, [row]))[0]


async def delete_mapping(session: AsyncSession, mapping_id: UUID) -> None:
    row = await get_mapping_or_404(session, mapping_id)
    await session.delete(row)
    await session.flush()


async def preview_mapping(session: AsyncSession, payload: MappingPreviewRequest) -> MappingRenderResponse:
    mapping_json, source_context, contract = await _resolve_runtime_inputs(session, payload.mapping_profile_id, payload.mapping_json, payload.source_context_json, payload.target_contract_id)
    return render_mapping(mapping_json, source_context, contract.schema_json if contract else None)


async def validate_mapping_request(session: AsyncSession, payload: MappingValidateRequest) -> MappingValidationResponse:
    mapping_json, source_context, contract = await _resolve_runtime_inputs(session, payload.mapping_profile_id, payload.mapping_json, payload.source_context_json, payload.target_contract_id)
    return validate_mapping(mapping_json, source_context, contract.schema_json if contract else None)


async def presets() -> MappingPresetsResponse:
    return MappingPresetsResponse(contracts=CONTRACT_PRESETS, mappings=MAPPING_PRESETS)


async def install_presets(session: AsyncSession) -> InstallMappingPresetsResponse:
    contract_rows: dict[str, DataContract] = {}
    for preset in CONTRACT_PRESETS:
        payload = DataContractCreate(**{key: value for key, value in preset.items() if key in DataContractCreate.model_fields})
        row = await upsert_contract(session, payload)
        contract_rows[row.code] = row

    operation_rows = await _operation_by_code(session)
    linked_operations: list[str] = []
    for preset in CONTRACT_PRESETS:
        op_code = preset.get("operation_profile_code")
        contract = contract_rows.get(str(preset["code"]))
        operation = operation_rows.get(str(op_code)) if op_code else None
        if contract and operation and operation.request_contract_id != contract.id:
            operation.request_contract_id = contract.id
            linked_operations.append(operation.code)

    mapping_rows: list[MappingProfile] = []
    for preset in MAPPING_PRESETS:
        contract = contract_rows.get(str(preset.get("target_contract_code")))
        operation = operation_rows.get(str(preset.get("operation_profile_code"))) if preset.get("operation_profile_code") else None
        data = {
            "name": preset["name"],
            "code": preset["code"],
            "description": preset.get("description"),
            "source_context_json": preset.get("source_context_json"),
            "target_contract_id": contract.id if contract else None,
            "operation_profile_id": operation.id if operation else None,
            "mapping_json": preset["mapping_json"],
            "package_id": preset.get("package_id"),
        }
        validate_profile_data(data)
        existing = await get_mapping_by_code(session, data["code"])
        if existing is None:
            existing = MappingProfile(**data)
            session.add(existing)
        else:
            for key, value in data.items():
                setattr(existing, key, value)
        mapping_rows.append(existing)
    await session.flush()
    return InstallMappingPresetsResponse(
        contracts=[read_contract(row) for row in contract_rows.values()],
        mappings=await _read_many(session, mapping_rows),
        linked_operations=sorted(set(linked_operations)),
    )


async def _resolve_runtime_inputs(
    session: AsyncSession,
    mapping_profile_id: UUID | None,
    mapping_json: dict | None,
    source_context_json: dict | None,
    target_contract_id: UUID | None,
) -> tuple[dict, dict, DataContract | None]:
    profile: MappingProfile | None = None
    if mapping_profile_id:
        profile = await get_mapping_or_404(session, mapping_profile_id)
    resolved_mapping = mapping_json or (profile.mapping_json if profile else None)
    if not isinstance(resolved_mapping, dict):
        raise BadRequestError("Укажите mapping_profile_id или mapping_json.")
    resolved_source = source_context_json if source_context_json is not None else (profile.source_context_json if profile else None) or {}
    if not isinstance(resolved_source, dict):
        raise BadRequestError("source_context_json должен быть JSON object.")
    contract_id = target_contract_id or (profile.target_contract_id if profile else None)
    contract = await session.get(DataContract, contract_id) if contract_id else None
    if contract_id and contract is None:
        raise NotFoundError("Target data contract not found")
    return resolved_mapping, resolved_source, contract


async def _validate_refs(session: AsyncSession, data: dict) -> None:
    contract_id = data.get("target_contract_id")
    if contract_id and await session.get(DataContract, contract_id) is None:
        raise BadRequestError("target_contract_id ссылается на несуществующий Data Contract.")
    operation_id = data.get("operation_profile_id")
    if operation_id and await session.get(OperationProfile, operation_id) is None:
        raise BadRequestError("operation_profile_id ссылается на несуществующий Operation Profile.")


async def _read_many(session: AsyncSession, rows: list[MappingProfile]) -> list[MappingProfileRead]:
    contract_ids = {row.target_contract_id for row in rows if row.target_contract_id}
    operation_ids = {row.operation_profile_id for row in rows if row.operation_profile_id}
    contracts: dict[UUID, DataContract] = {}
    operations: dict[UUID, OperationProfile] = {}
    if contract_ids:
        contracts = {row.id: row for row in (await session.execute(select(DataContract).where(DataContract.id.in_(contract_ids)))).scalars().all()}
    if operation_ids:
        operations = {row.id: row for row in (await session.execute(select(OperationProfile).where(OperationProfile.id.in_(operation_ids)))).scalars().all()}
    return [_read(row, contracts.get(row.target_contract_id), operations.get(row.operation_profile_id)) for row in rows]


def _read(row: MappingProfile, contract: DataContract | None, operation: OperationProfile | None) -> MappingProfileRead:
    return MappingProfileRead(
        id=row.id,
        name=row.name,
        code=row.code,
        source_context_json=row.source_context_json,
        target_contract_id=row.target_contract_id,
        operation_profile_id=row.operation_profile_id,
        mapping_json=row.mapping_json,
        description=row.description,
        package_id=row.package_id,
        target_contract_name=contract.name if contract else None,
        target_contract_code=contract.code if contract else None,
        operation_profile_name=operation.name if operation else None,
        operation_profile_code=operation.code if operation else None,
        status="ready" if contract and row.mapping_json else "draft",
        used_by=_used_by(row, operation),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _used_by(row: MappingProfile, operation: OperationProfile | None) -> list[str]:
    used: list[str] = []
    code = operation.code if operation else ""
    tags = set(operation.tags_json or []) if operation else set()
    if code == "dnp_import_chz_codes" or "dnp" in tags or "chz" in tags:
        used.append("Request -> OData -> Foreach OData -> Send Endpoint")
        used.append("CHZ Code Pool Workbench")
    if code == "onec_write_order_external_id":
        used.append("Source -> Web API -> Write Back to 1C")
    if code == "onec_accept_wms_shipment_fact":
        used.append("WMS -> 1C")
    if not used and row.code == "mapping_website_order_import":
        used.append("Request -> OData -> Send Endpoint")
    return used


async def _operation_by_code(session: AsyncSession) -> dict[str, OperationProfile]:
    rows = list((await session.execute(select(OperationProfile))).scalars().all())
    return {row.code: row for row in rows}
