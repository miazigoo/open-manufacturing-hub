from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import BadRequestError
from app.events.schemas import EventRunRead
from app.onec_workbench import repository, service
from app.onec_workbench.schemas import IntegrationMessageRead, ODataLookupTestRequest, ODataLookupTestResponse, WorkbenchInstallResponse, XmlInboundJsonRequest, XmlInboundResponse

router = APIRouter(tags=["1c-workbench"])


@router.post("/api/onec/xml/inbound", response_model=XmlInboundResponse)
async def receive_xml(request: Request, session: AsyncSession = Depends(get_session)):
    payload = await _inbound_payload(request)
    message, event = await service.receive_xml(session, payload)
    await session.commit()
    return {"message_id": message.id, "event_id": event.id, "status": message.status, "timeline_url": f"/events/{event.id}"}


@router.get("/api/onec/xml/messages", response_model=list[IntegrationMessageRead])
async def list_messages(session: AsyncSession = Depends(get_session)):
    return await repository.list_messages(session)


@router.get("/api/onec/xml/messages/{message_id}", response_model=IntegrationMessageRead)
async def get_message(message_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_message_or_404(session, message_id)


@router.post("/api/onec/xml/messages/{message_id}/replay", response_model=EventRunRead)
async def replay_message(message_id: UUID, session: AsyncSession = Depends(get_session)):
    run = await service.replay_message(session, message_id)
    await session.commit()
    return run


@router.post("/api/onec/lookup/test", response_model=ODataLookupTestResponse)
async def test_lookup(request: ODataLookupTestRequest, session: AsyncSession = Depends(get_session)):
    return await service.test_odata_lookup(session, request)


@router.post("/api/onec-workbench/install-xml-bridge", response_model=WorkbenchInstallResponse)
async def install_xml_bridge(session: AsyncSession = Depends(get_session)):
    workflow = await service.ensure_xml_bridge_workflow(session)
    await session.commit()
    return {"workflow_id": workflow.id, "workflow_name": workflow.name, "installed": True}


@router.post("/api/onec-workbench/install-inn-lookup-demo", response_model=WorkbenchInstallResponse)
async def install_inn_lookup_demo(session: AsyncSession = Depends(get_session)):
    workflow = await service.install_inn_lookup_demo(session)
    await session.commit()
    return {"workflow_id": workflow.id, "workflow_name": workflow.name, "installed": True}


@router.post("/api/onec-workbench/install-print-pipeline", response_model=WorkbenchInstallResponse)
async def install_print_pipeline(session: AsyncSession = Depends(get_session)):
    workflow = await service.install_print_pipeline(session)
    await session.commit()
    return {"workflow_id": workflow.id, "workflow_name": workflow.name, "installed": True}


async def _inbound_payload(request: Request) -> XmlInboundJsonRequest:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type in {"application/json", "text/json"}:
        return XmlInboundJsonRequest.model_validate(await request.json())
    if content_type == "multipart/form-data":
        form = await request.form()
        upload = form.get("file")
        xml = await upload.read() if hasattr(upload, "read") else None
        if isinstance(xml, bytes):
            xml_text = xml.decode("utf-8")
        else:
            xml_text = str(form.get("xml") or "")
        return XmlInboundJsonRequest(
            source_system=str(form.get("source_system") or "1C XML"),
            target_system=str(form.get("target_system")) if form.get("target_system") else None,
            message_type=str(form.get("message_type") or "XML_FILE"),
            correlation_id=str(form.get("correlation_id")) if form.get("correlation_id") else None,
            xml=xml_text,
        )
    if content_type not in {"application/xml", "text/xml", "application/octet-stream", ""}:
        raise BadRequestError(f"Unsupported XML inbound content type: {content_type}")
    xml_text = (await request.body()).decode("utf-8")
    meta = service.xml_metadata_from_headers(request.headers)
    return XmlInboundJsonRequest(xml=xml_text, **meta)
