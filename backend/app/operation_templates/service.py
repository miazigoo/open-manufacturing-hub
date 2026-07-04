from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.operation_templates import repository
from app.operation_templates.models import OperationTemplate
from app.operation_templates.presets import OPERATION_TEMPLATE_PRESETS
from app.operation_templates.schemas import OperationTemplateCreate, OperationTemplatePatch


async def create_template(session: AsyncSession, request: OperationTemplateCreate) -> OperationTemplate:
    _validate_template(request.request_template_json)
    template = OperationTemplate(**request.model_dump())
    session.add(template)
    await session.flush()
    return template


async def patch_template(session: AsyncSession, template_id: UUID, request: OperationTemplatePatch) -> OperationTemplate:
    template = await get_template_or_404(session, template_id)
    data = request.model_dump(exclude_unset=True)
    if "request_template_json" in data:
        _validate_template(data["request_template_json"])
    for key, value in data.items():
        setattr(template, key, value)
    await session.flush()
    return template


async def get_template_or_404(session: AsyncSession, template_id: UUID) -> OperationTemplate:
    template = await repository.get_template(session, template_id)
    if template is None:
        raise NotFoundError("Operation template not found")
    return template


async def install_presets(session: AsyncSession) -> list[OperationTemplate]:
    installed: list[OperationTemplate] = []
    for preset in OPERATION_TEMPLATE_PRESETS:
        existing = await repository.get_by_name(session, preset["name"])
        if existing is None:
            existing = OperationTemplate(enabled=True, **preset)
            session.add(existing)
            await session.flush()
        else:
            for key, value in preset.items():
                setattr(existing, key, value)
            existing.enabled = True
            await session.flush()
        installed.append(existing)
    return installed


def _validate_template(template: dict) -> None:
    if not isinstance(template, dict):
        raise BadRequestError("request_template_json must be an object")
