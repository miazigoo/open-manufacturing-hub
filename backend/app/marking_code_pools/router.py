from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.marking_code_pools.models import MarkingCodePoolExport
from app.marking_code_pools.schemas import MarkingCodePoolExportRead, MarkingCodePoolExportResponse, OneCMarkingCodePoolExportRequest
from app.marking_code_pools import service

router = APIRouter(prefix="/api/marking-code-pools", tags=["marking-code-pools"])


@router.post("/onec/export-file", response_model=MarkingCodePoolExportResponse)
async def export_onec_pool_to_file(request: OneCMarkingCodePoolExportRequest, session: AsyncSession = Depends(get_session)):
    record, dnp_forward = await service.export_onec_pool_to_file(session, request)
    await session.commit()
    actions = (record.metadata_json or {}).get("actions", {})
    message = f"Accepted {record.total_codes} marking codes as {record.file_name}; status={record.status}"
    if dnp_forward is not None:
        message += "; DnP accepted the pool"
    return MarkingCodePoolExportResponse(export=record, message=message, actions=actions, dnp_forward=dnp_forward)


@router.get("/exports", response_model=list[MarkingCodePoolExportRead])
async def list_exports(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MarkingCodePoolExport).order_by(MarkingCodePoolExport.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/exports/{export_id}", response_model=MarkingCodePoolExportRead)
async def get_export(export_id: UUID, session: AsyncSession = Depends(get_session)):
    record = await session.get(MarkingCodePoolExport, export_id)
    if record is None:
        raise NotFoundError("Marking code pool export not found")
    return record
