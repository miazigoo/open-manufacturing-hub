from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.mappings.engine import MappingEngine
from app.mappings.models import MappingDefinition, MappingVersion
from app.mappings.presets import MAPPING_PRESETS
from app.mappings.schemas import MappingCloneRequest, MappingCreate, MappingPatch, MappingVersionCreate

engine = MappingEngine()


async def list_mappings(session: AsyncSession) -> list[MappingDefinition]:
    result = await session.execute(select(MappingDefinition).order_by(MappingDefinition.name.asc()))
    return list(result.scalars().unique())


async def get_mapping(session: AsyncSession, mapping_id: UUID) -> MappingDefinition | None:
    return await session.get(MappingDefinition, mapping_id)


async def get_mapping_or_404(session: AsyncSession, mapping_id: UUID) -> MappingDefinition:
    mapping = await get_mapping(session, mapping_id)
    if mapping is None:
        raise NotFoundError("Mapping not found")
    return mapping


async def get_version_or_404(session: AsyncSession, mapping_id: UUID, version: int) -> MappingVersion:
    result = await session.execute(select(MappingVersion).where(MappingVersion.mapping_id == mapping_id, MappingVersion.version == version))
    mapping_version = result.scalar_one_or_none()
    if mapping_version is None:
        raise NotFoundError("Mapping version not found")
    return mapping_version


async def get_version_by_id_or_404(session: AsyncSession, version_id: UUID) -> MappingVersion:
    version = await session.get(MappingVersion, version_id)
    if version is None:
        raise NotFoundError("Mapping version not found")
    return version


async def get_latest_version_by_mapping_name(session: AsyncSession, name: str) -> MappingVersion | None:
    result = await session.execute(
        select(MappingVersion)
        .join(MappingDefinition, MappingDefinition.id == MappingVersion.mapping_id)
        .where(MappingDefinition.name == name)
        .order_by(MappingVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_mapping(session: AsyncSession, request: MappingCreate) -> MappingDefinition:
    validation = engine.validate(request.initial_version.rules_json)
    if not validation["valid"]:
        raise BadRequestError("; ".join(validation["errors"]))
    mapping = MappingDefinition(
        name=request.name,
        description=request.description,
        source_entity=request.source_entity,
        target_entity=request.target_entity,
    )
    session.add(mapping)
    await session.flush()
    session.add(
        MappingVersion(
            mapping_id=mapping.id,
            version=1,
            rules_json=request.initial_version.rules_json,
            source_schema_json=request.initial_version.source_schema_json,
            target_schema_json=request.initial_version.target_schema_json,
            notes=request.initial_version.notes,
        )
    )
    await session.flush()
    await session.refresh(mapping)
    return mapping


async def patch_mapping(session: AsyncSession, mapping_id: UUID, request: MappingPatch) -> MappingDefinition:
    mapping = await get_mapping_or_404(session, mapping_id)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(mapping, key, value)
    await session.flush()
    return mapping


async def create_version(session: AsyncSession, mapping_id: UUID, request: MappingVersionCreate) -> MappingVersion:
    mapping = await get_mapping_or_404(session, mapping_id)
    validation = engine.validate(request.rules_json)
    if not validation["valid"]:
        raise BadRequestError("; ".join(validation["errors"]))
    next_version = max([version.version for version in mapping.versions] or [0]) + 1
    version = MappingVersion(
        mapping_id=mapping.id,
        version=next_version,
        rules_json=request.rules_json,
        source_schema_json=request.source_schema_json,
        target_schema_json=request.target_schema_json,
        notes=request.notes,
    )
    session.add(version)
    await session.flush()
    return version


async def clone_version(session: AsyncSession, mapping_id: UUID, version: int, request: MappingCloneRequest) -> MappingVersion:
    source = await get_version_or_404(session, mapping_id, version)
    return await create_version(
        session,
        mapping_id,
        MappingVersionCreate(
            rules_json=source.rules_json,
            source_schema_json=source.source_schema_json,
            target_schema_json=source.target_schema_json,
            notes=request.notes or f"Cloned from v{version}",
        ),
    )


async def validate_mapping(rules_json: list[dict], sample_payload: dict | None = None) -> dict:
    return engine.validate(rules_json, sample_payload)


async def execute_version(session: AsyncSession, mapping_id: UUID, version: int, payload: dict) -> dict:
    mapping_version = await get_version_or_404(session, mapping_id, version)
    return engine.apply(payload, mapping_version.rules_json)


async def diff_versions(session: AsyncSession, mapping_id: UUID, left_version: int, right_version: int) -> dict:
    left = await get_version_or_404(session, mapping_id, left_version)
    right = await get_version_or_404(session, mapping_id, right_version)
    left_rules = {_stable_rule_key(rule): rule for rule in left.rules_json}
    right_rules = {_stable_rule_key(rule): rule for rule in right.rules_json}
    added = [right_rules[key] for key in sorted(right_rules.keys() - left_rules.keys())]
    removed = [left_rules[key] for key in sorted(left_rules.keys() - right_rules.keys())]
    changed = [
        {"rule": key, "from": left_rules[key], "to": right_rules[key]}
        for key in sorted(left_rules.keys() & right_rules.keys())
        if left_rules[key] != right_rules[key]
    ]
    return {"mapping_id": mapping_id, "left_version": left_version, "right_version": right_version, "added": added, "removed": removed, "changed": changed}


def _stable_rule_key(rule: dict) -> str:
    if isinstance(rule.get("target"), str):
        return rule["target"]
    return json.dumps(rule, sort_keys=True, separators=(",", ":"))


async def install_preset(session: AsyncSession, preset_name: str) -> MappingDefinition:
    preset = next((item for item in MAPPING_PRESETS if item["name"] == preset_name), None)
    if preset is None:
        raise NotFoundError("Mapping preset not found")
    existing = (await session.execute(select(MappingDefinition).where(MappingDefinition.name == preset["name"]))).scalar_one_or_none()
    if existing is not None:
        return existing
    return await create_mapping(
        session,
        MappingCreate(
            name=preset["name"],
            description=preset.get("description"),
            source_entity=preset.get("source_entity"),
            target_entity=preset.get("target_entity"),
            initial_version=MappingVersionCreate(
                rules_json=preset["rules_json"],
                source_schema_json=preset.get("source_schema_json", {}),
                target_schema_json=preset.get("target_schema_json", {}),
                notes="Installed preset",
            ),
        ),
    )


async def install_all_presets(session: AsyncSession) -> list[MappingDefinition]:
    installed = [] 
    for preset in MAPPING_PRESETS:
        installed.append(await install_preset(session, preset["name"]))
    return installed
