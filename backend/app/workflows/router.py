from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.workflows import service
from app.workflows.schemas import WorkflowCreate, WorkflowDryRunRead, WorkflowDryRunRequest, WorkflowPatch, WorkflowRead

router = APIRouter(tags=["workflows"])


@router.get("/api/workflows", response_model=list[WorkflowRead])
async def list_workflows(session: AsyncSession = Depends(get_session)):
    return await service.list_workflows(session)


@router.post("/api/workflows", response_model=WorkflowRead)
async def create_workflow(request: WorkflowCreate, session: AsyncSession = Depends(get_session)):
    workflow = await service.create_workflow(session, request)
    await session.commit()
    return workflow


@router.get("/api/workflows/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(workflow_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_workflow_or_404(session, workflow_id)


@router.patch("/api/workflows/{workflow_id}", response_model=WorkflowRead)
async def patch_workflow(workflow_id: UUID, request: WorkflowPatch, session: AsyncSession = Depends(get_session)):
    workflow = await service.patch_workflow(session, workflow_id, request)
    await session.commit()
    return workflow


@router.delete("/api/workflows/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: UUID, session: AsyncSession = Depends(get_session)):
    workflow = await service.get_workflow_or_404(session, workflow_id)
    await session.delete(workflow)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/workflows/{workflow_id}/enable", response_model=WorkflowRead)
async def enable_workflow(workflow_id: UUID, session: AsyncSession = Depends(get_session)):
    workflow = await service.set_enabled(session, workflow_id, True)
    await session.commit()
    return workflow


@router.post("/api/workflows/{workflow_id}/disable", response_model=WorkflowRead)
async def disable_workflow(workflow_id: UUID, session: AsyncSession = Depends(get_session)):
    workflow = await service.set_enabled(session, workflow_id, False)
    await session.commit()
    return workflow


@router.post("/api/workflows/{workflow_id}/dry-run", response_model=WorkflowDryRunRead)
async def dry_run_workflow(workflow_id: UUID, request: WorkflowDryRunRequest, session: AsyncSession = Depends(get_session)):
    workflow, run = await service.dry_run_workflow(session, workflow_id, request)
    await session.commit()
    return {"workflow_id": workflow.id, "workflow_name": workflow.name, "status": run.status, "run": run}


@router.post("/api/workflows/{workflow_id}/test", response_model=WorkflowDryRunRead)
async def test_workflow(workflow_id: UUID, request: WorkflowDryRunRequest, session: AsyncSession = Depends(get_session)):
    workflow, run = await service.dry_run_workflow(session, workflow_id, request)
    await session.commit()
    return {"workflow_id": workflow.id, "workflow_name": workflow.name, "status": run.status, "run": run}
