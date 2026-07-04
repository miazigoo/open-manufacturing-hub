from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.operation_templates import repository, service
from app.operation_templates.schemas import OperationTemplateCreate, OperationTemplatePatch, OperationTemplateRead

router = APIRouter(tags=["operation-templates"])


@router.get("/api/operation-templates", response_model=list[OperationTemplateRead])
async def list_templates(session: AsyncSession = Depends(get_session)):
    return await repository.list_templates(session)


@router.post("/api/operation-templates", response_model=OperationTemplateRead)
async def create_template(request: OperationTemplateCreate, session: AsyncSession = Depends(get_session)):
    template = await service.create_template(session, request)
    await session.commit()
    return template


@router.post("/api/operation-templates/install-presets", response_model=list[OperationTemplateRead])
async def install_presets(session: AsyncSession = Depends(get_session)):
    templates = await service.install_presets(session)
    await session.commit()
    return templates


@router.get("/api/operation-templates/{template_id}", response_model=OperationTemplateRead)
async def get_template(template_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_template_or_404(session, template_id)


@router.patch("/api/operation-templates/{template_id}", response_model=OperationTemplateRead)
async def patch_template(template_id: UUID, request: OperationTemplatePatch, session: AsyncSession = Depends(get_session)):
    template = await service.patch_template(session, template_id, request)
    await session.commit()
    return template


@router.delete("/api/operation-templates/{template_id}", status_code=204)
async def delete_template(template_id: UUID, session: AsyncSession = Depends(get_session)):
    template = await service.get_template_or_404(session, template_id)
    await session.delete(template)
    await session.commit()
    return Response(status_code=204)
