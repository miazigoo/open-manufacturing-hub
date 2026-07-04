from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.workflows import service
from app.workflows.schemas import WorkflowCreate, WorkflowDryRunRead, WorkflowDryRunRequest, WorkflowPatch, WorkflowRead, WorkflowValidationRead

router = APIRouter(tags=["workflows"])


@router.get("/api/workflows", response_model=list[WorkflowRead])
async def list_workflows(session: AsyncSession = Depends(get_session)):
    return await service.list_workflows(session)


@router.post("/api/workflows", response_model=WorkflowRead)
async def create_workflow(payload: WorkflowCreate, http_request: Request, session: AsyncSession = Depends(get_session)):
    workflow = await service.create_workflow(session, payload)
    await audit_service.record_change(session, request=http_request, action="workflow.created", category="workflows", object_type="workflow", object_id=workflow.id, object_name=workflow.name, before=None, after=audit_service.snapshot_model(workflow), summary=f"Workflow {workflow.name} created")
    await session.commit()
    return workflow


@router.get("/api/workflows/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(workflow_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_workflow_or_404(session, workflow_id)


@router.patch("/api/workflows/{workflow_id}", response_model=WorkflowRead)
async def patch_workflow(workflow_id: UUID, payload: WorkflowPatch, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_workflow_or_404(session, workflow_id)
    before = audit_service.snapshot_model(existing)
    workflow = await service.patch_workflow(session, workflow_id, payload)
    await audit_service.record_change(session, request=http_request, action="workflow.updated", category="workflows", object_type="workflow", object_id=workflow.id, object_name=workflow.name, before=before, after=audit_service.snapshot_model(workflow), summary=f"Workflow {workflow.name} updated")
    await session.commit()
    return workflow


@router.delete("/api/workflows/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    workflow = await service.get_workflow_or_404(session, workflow_id)
    before = audit_service.snapshot_model(workflow)
    await audit_service.record_change(session, request=http_request, action="workflow.deleted", category="workflows", object_type="workflow", object_id=workflow.id, object_name=workflow.name, before=before, after=None, summary=f"Workflow {workflow.name} deleted")
    await session.delete(workflow)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/workflows/{workflow_id}/enable", response_model=WorkflowRead)
async def enable_workflow(workflow_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_workflow_or_404(session, workflow_id)
    before = audit_service.snapshot_model(existing)
    workflow = await service.set_enabled(session, workflow_id, True)
    await audit_service.record_change(session, request=http_request, action="workflow.enabled", category="workflows", object_type="workflow", object_id=workflow.id, object_name=workflow.name, before=before, after=audit_service.snapshot_model(workflow), summary=f"Workflow {workflow.name} enabled")
    await session.commit()
    return workflow


@router.post("/api/workflows/{workflow_id}/disable", response_model=WorkflowRead)
async def disable_workflow(workflow_id: UUID, http_request: Request, session: AsyncSession = Depends(get_session)):
    existing = await service.get_workflow_or_404(session, workflow_id)
    before = audit_service.snapshot_model(existing)
    workflow = await service.set_enabled(session, workflow_id, False)
    await audit_service.record_change(session, request=http_request, action="workflow.disabled", category="workflows", object_type="workflow", object_id=workflow.id, object_name=workflow.name, before=before, after=audit_service.snapshot_model(workflow), summary=f"Workflow {workflow.name} disabled")
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


@router.post("/api/workflows/{workflow_id}/validate", response_model=WorkflowValidationRead)
async def validate_workflow(workflow_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.validate_workflow(session, workflow_id)
