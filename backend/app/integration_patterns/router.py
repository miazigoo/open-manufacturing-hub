from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.database import get_session
from app.integration_patterns import certification, poll_odata_send_target, request_multiple_odata_response, request_odata_object_foreach_send_endpoint, request_odata_response, request_odata_send_endpoint, request_print, source_web_api_writeback_onec, wms_fact_to_onec, xml_odata_xml_response, xml_raw_bridge
from app.integration_patterns import service
from app.integration_patterns.schemas import (
    IntegrationPattern,
    PatternCertification,
    PatternCertificationListResponse,
    PatternRecommendRequest,
    PatternRecommendResponse,
    PatternStartRequest,
    PatternStartResponse,
    PollODataSendTargetCreateResponse,
    PollODataSendTargetPatternRequest,
    PollODataSendTargetPreviewResponse,
    PollODataSendTargetRunTestRequest,
    PollODataSendTargetRunTestResponse,
    RequestMultipleODataResponseCreateResponse,
    RequestMultipleODataResponsePatternRequest,
    RequestMultipleODataResponsePreviewResponse,
    RequestMultipleODataResponseRunTestRequest,
    RequestMultipleODataResponseRunTestResponse,
    RequestODataResponseCreateResponse,
    RequestODataResponsePatternRequest,
    RequestODataResponsePreviewResponse,
    RequestODataResponseRunTestRequest,
    RequestODataResponseRunTestResponse,
    RequestODataObjectForeachSendEndpointCreateResponse,
    RequestODataObjectForeachSendEndpointPatternRequest,
    RequestODataObjectForeachSendEndpointPreviewResponse,
    RequestODataObjectForeachSendEndpointRunTestRequest,
    RequestODataObjectForeachSendEndpointRunTestResponse,
    RequestODataSendEndpointCreateResponse,
    RequestODataSendEndpointPatternRequest,
    RequestODataSendEndpointPreviewResponse,
    RequestODataSendEndpointRunTestRequest,
    RequestODataSendEndpointRunTestResponse,
    RequestPrintCreateResponse,
    RequestPrintPatternRequest,
    RequestPrintPreviewResponse,
    RequestPrintRunTestRequest,
    RequestPrintRunTestResponse,
    RequestPrintTestPrintRequest,
    RequestPrintTestPrintResponse,
    SourceWebApiWritebackOneCCreateResponse,
    SourceWebApiWritebackOneCPatternRequest,
    SourceWebApiWritebackOneCPreviewResponse,
    SourceWebApiWritebackOneCRunTestRequest,
    SourceWebApiWritebackOneCRunTestResponse,
    WmsFactToOneCCreateResponse,
    WmsFactToOneCPatternRequest,
    WmsFactToOneCPreviewResponse,
    WmsFactToOneCRunTestRequest,
    WmsFactToOneCRunTestResponse,
    XmlODataXmlResponseCreateResponse,
    XmlODataXmlResponsePatternRequest,
    XmlODataXmlResponsePreviewResponse,
    XmlODataXmlResponseRunTestRequest,
    XmlODataXmlResponseRunTestResponse,
    XmlRawBridgeCreateResponse,
    XmlRawBridgePatternRequest,
    XmlRawBridgePreviewResponse,
    XmlRawBridgeRunTestRequest,
    XmlRawBridgeRunTestResponse,
)

router = APIRouter(prefix="/api/integration-patterns", tags=["integration-patterns"])


@router.get("", response_model=list[IntegrationPattern])
async def list_patterns():
    return service.list_patterns()


@router.get("/certification", response_model=PatternCertificationListResponse)
async def list_pattern_certifications():
    return certification.list_certifications()


@router.get("/{pattern_id}/certification", response_model=PatternCertification)
async def get_pattern_certification(pattern_id: str):
    return certification.get_certification(pattern_id)


@router.post("/{pattern_id}/certification/check", response_model=PatternCertification)
async def check_pattern_certification(pattern_id: str):
    return certification.check_certification(pattern_id)


@router.get("/{pattern_id}", response_model=IntegrationPattern)
async def get_pattern(pattern_id: str):
    return service.get_pattern(pattern_id)


@router.post("/recommend", response_model=PatternRecommendResponse)
async def recommend_patterns(payload: PatternRecommendRequest):
    return service.recommend_patterns(payload)


@router.post("/start", response_model=PatternStartResponse)
async def start_pattern(payload: PatternStartRequest):
    return service.start_pattern(payload.pattern_id)


@router.post("/poll-odata-send-target/preview", response_model=PollODataSendTargetPreviewResponse)
async def preview_poll_odata_send_target_pattern(payload: PollODataSendTargetPatternRequest, session: AsyncSession = Depends(get_session)):
    return await poll_odata_send_target.preview_pattern(session, payload)


@router.post("/poll-odata-send-target/create", response_model=PollODataSendTargetCreateResponse)
async def create_poll_odata_send_target_pattern(payload: PollODataSendTargetPatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await poll_odata_send_target.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.poll_odata_send_target.created",
        category="integration_patterns",
        object_type="polling_job",
        object_id=result.polling_job_id,
        object_name=payload.job.slug,
        summary=f"Poll OData -> Send Target pattern created {payload.job.slug}",
        details={
            "pattern_id": "poll_odata_send_target",
            "polling_job_id": str(result.polling_job_id),
            "integration_flow_id": str(result.integration_flow_id) if result.integration_flow_id else None,
            "enabled": result.enabled,
        },
    )
    await session.commit()
    return result


@router.post("/poll-odata-send-target/run-test", response_model=PollODataSendTargetRunTestResponse)
async def run_poll_odata_send_target_pattern_test(payload: PollODataSendTargetRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await poll_odata_send_target.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.poll_odata_send_target.test_run",
        category="integration_patterns",
        object_type="polling_job",
        object_id=payload.polling_job_id,
        object_name=str(payload.polling_job_id or (payload.pattern.job.slug if payload.pattern else "unsaved")),
        summary="Poll OData -> Send Target test run",
        details={"pattern_id": "poll_odata_send_target", "dry_run": payload.dry_run, "update_cursor": payload.update_cursor, "success": result.success},
    )
    await session.commit()
    return result


@router.post("/request-odata-response/preview", response_model=RequestODataResponsePreviewResponse)
async def preview_request_odata_response_pattern(payload: RequestODataResponsePatternRequest, session: AsyncSession = Depends(get_session)):
    return await request_odata_response.preview_pattern(session, payload)


@router.post("/request-odata-response/create", response_model=RequestODataResponseCreateResponse)
async def create_request_odata_response_pattern(payload: RequestODataResponsePatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_odata_response.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_odata_response.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"Request -> OData -> Response pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "request_odata_response",
            "draft_id": str(result.draft_id),
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/request-odata-response/run-test", response_model=RequestODataResponseRunTestResponse)
async def run_request_odata_response_pattern_test(payload: RequestODataResponseRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_odata_response.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_odata_response.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"Request -> OData -> Response pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/request-multiple-odata-response/preview", response_model=RequestMultipleODataResponsePreviewResponse)
async def preview_request_multiple_odata_response_pattern(payload: RequestMultipleODataResponsePatternRequest, session: AsyncSession = Depends(get_session)):
    return await request_multiple_odata_response.preview_pattern(session, payload)


@router.post("/request-multiple-odata-response/create", response_model=RequestMultipleODataResponseCreateResponse)
async def create_request_multiple_odata_response_pattern(payload: RequestMultipleODataResponsePatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_multiple_odata_response.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_multiple_odata_response.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"Request -> Multiple OData -> Response pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "request_multiple_odata_response",
            "draft_id": str(result.draft_id),
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/request-multiple-odata-response/run-test", response_model=RequestMultipleODataResponseRunTestResponse)
async def run_request_multiple_odata_response_pattern_test(payload: RequestMultipleODataResponseRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_multiple_odata_response.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_multiple_odata_response.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"Request -> Multiple OData -> Response pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/request-odata-send-endpoint/preview", response_model=RequestODataSendEndpointPreviewResponse)
async def preview_request_odata_send_endpoint_pattern(payload: RequestODataSendEndpointPatternRequest, session: AsyncSession = Depends(get_session)):
    return await request_odata_send_endpoint.preview_pattern(session, payload)


@router.post("/request-odata-send-endpoint/create", response_model=RequestODataSendEndpointCreateResponse)
async def create_request_odata_send_endpoint_pattern(payload: RequestODataSendEndpointPatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_odata_send_endpoint.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_odata_send_endpoint.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"Request -> OData -> Send Endpoint pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "request_odata_send_endpoint",
            "draft_id": str(result.draft_id),
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/request-odata-send-endpoint/run-test", response_model=RequestODataSendEndpointRunTestResponse)
async def run_request_odata_send_endpoint_pattern_test(payload: RequestODataSendEndpointRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_odata_send_endpoint.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_odata_send_endpoint.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"Request -> OData -> Send Endpoint pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/request-odata-object-foreach-send-endpoint/preview", response_model=RequestODataObjectForeachSendEndpointPreviewResponse)
async def preview_request_odata_object_foreach_send_endpoint_pattern(payload: RequestODataObjectForeachSendEndpointPatternRequest, session: AsyncSession = Depends(get_session)):
    return await request_odata_object_foreach_send_endpoint.preview_pattern(session, payload)


@router.post("/request-odata-object-foreach-send-endpoint/create", response_model=RequestODataObjectForeachSendEndpointCreateResponse)
async def create_request_odata_object_foreach_send_endpoint_pattern(payload: RequestODataObjectForeachSendEndpointPatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_odata_object_foreach_send_endpoint.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_odata_object_foreach_send_endpoint.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"Request -> OData -> Object Rows -> Foreach -> Send Endpoint pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "request_odata_object_foreach_send_endpoint",
            "draft_id": str(result.draft_id),
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/request-odata-object-foreach-send-endpoint/run-test", response_model=RequestODataObjectForeachSendEndpointRunTestResponse)
async def run_request_odata_object_foreach_send_endpoint_pattern_test(payload: RequestODataObjectForeachSendEndpointRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_odata_object_foreach_send_endpoint.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_odata_object_foreach_send_endpoint.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"Request -> OData -> Object Rows -> Foreach -> Send Endpoint pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/request-print/preview", response_model=RequestPrintPreviewResponse)
async def preview_request_print_pattern(payload: RequestPrintPatternRequest, session: AsyncSession = Depends(get_session)):
    return await request_print.preview_pattern(session, payload)


@router.post("/request-print/create", response_model=RequestPrintCreateResponse)
async def create_request_print_pattern(payload: RequestPrintPatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_print.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_print.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"Request -> Printer pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "request_print",
            "draft_id": str(result.draft_id) if result.draft_id else None,
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/request-print/run-test", response_model=RequestPrintRunTestResponse)
async def run_request_print_pattern_test(payload: RequestPrintRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_print.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_print.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"Request -> Printer pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/request-print/test-print", response_model=RequestPrintTestPrintResponse)
async def test_print_request_print_pattern(payload: RequestPrintTestPrintRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await request_print.test_print(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.request_print.test_print",
        category="integration_patterns",
        object_type="integration_pattern",
        object_name=payload.slug,
        summary=f"Request -> Printer test print {payload.slug}",
        details={"dry_run": payload.dry_run, "success": result.print_result.get("success"), "limit": payload.limit},
    )
    await session.commit()
    return result


@router.post("/source-web-api-writeback-onec/preview", response_model=SourceWebApiWritebackOneCPreviewResponse)
async def preview_source_web_api_writeback_onec_pattern(payload: SourceWebApiWritebackOneCPatternRequest, session: AsyncSession = Depends(get_session)):
    return await source_web_api_writeback_onec.preview_pattern(session, payload)


@router.post("/source-web-api-writeback-onec/create", response_model=SourceWebApiWritebackOneCCreateResponse)
async def create_source_web_api_writeback_onec_pattern(payload: SourceWebApiWritebackOneCPatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await source_web_api_writeback_onec.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.source_web_api_writeback_onec.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"Source -> Web API -> Writeback 1C pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "source_web_api_writeback_onec",
            "draft_id": str(result.draft_id),
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/source-web-api-writeback-onec/run-test", response_model=SourceWebApiWritebackOneCRunTestResponse)
async def run_source_web_api_writeback_onec_pattern_test(payload: SourceWebApiWritebackOneCRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await source_web_api_writeback_onec.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.source_web_api_writeback_onec.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"Source -> Web API -> Writeback 1C pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/wms-fact-to-onec/preview", response_model=WmsFactToOneCPreviewResponse)
async def preview_wms_fact_to_onec_pattern(payload: WmsFactToOneCPatternRequest, session: AsyncSession = Depends(get_session)):
    return await wms_fact_to_onec.preview_pattern(session, payload)


@router.post("/wms-fact-to-onec/create", response_model=WmsFactToOneCCreateResponse)
async def create_wms_fact_to_onec_pattern(payload: WmsFactToOneCPatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await wms_fact_to_onec.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.wms_fact_to_onec.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"WMS fact to 1C pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "wms_fact_to_onec",
            "draft_id": str(result.draft_id),
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/wms-fact-to-onec/run-test", response_model=WmsFactToOneCRunTestResponse)
async def run_wms_fact_to_onec_pattern_test(payload: WmsFactToOneCRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await wms_fact_to_onec.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.wms_fact_to_onec.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"WMS fact to 1C pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/xml-odata-xml-response/preview", response_model=XmlODataXmlResponsePreviewResponse)
async def preview_xml_odata_xml_response_pattern(payload: XmlODataXmlResponsePatternRequest, session: AsyncSession = Depends(get_session)):
    return await xml_odata_xml_response.preview_pattern(session, payload)


@router.post("/xml-odata-xml-response/create", response_model=XmlODataXmlResponseCreateResponse)
async def create_xml_odata_xml_response_pattern(payload: XmlODataXmlResponsePatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await xml_odata_xml_response.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.xml_odata_xml_response.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"XML -> OData -> XML/JSON Response pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "xml_odata_xml_response",
            "draft_id": str(result.draft_id) if result.draft_id else None,
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/xml-odata-xml-response/run-test", response_model=XmlODataXmlResponseRunTestResponse)
async def run_xml_odata_xml_response_pattern_test(payload: XmlODataXmlResponseRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await xml_odata_xml_response.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.xml_odata_xml_response.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"XML -> OData -> XML/JSON Response pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result


@router.post("/xml-raw-bridge/preview", response_model=XmlRawBridgePreviewResponse)
async def preview_xml_raw_bridge_pattern(payload: XmlRawBridgePatternRequest, session: AsyncSession = Depends(get_session)):
    return await xml_raw_bridge.preview_pattern(session, payload)


@router.post("/xml-raw-bridge/create", response_model=XmlRawBridgeCreateResponse)
async def create_xml_raw_bridge_pattern(payload: XmlRawBridgePatternRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await xml_raw_bridge.create_pattern(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.xml_raw_bridge.created",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=result.compile.integration_flow_id,
        object_name=result.compile.endpoint.url,
        summary=f"XML Raw Bridge pattern created {result.compile.endpoint.url}",
        details={
            "pattern_id": "xml_raw_bridge",
            "draft_id": str(result.draft_id) if result.draft_id else None,
            "flow_id": str(result.compile.integration_flow_id),
            "endpoint_id": str(result.compile.endpoint_id),
            "route_id": str(result.compile.route_id),
            "saved_test_case_id": str(result.compile.saved_test_case_id) if result.compile.saved_test_case_id else None,
        },
    )
    await session.commit()
    return result


@router.post("/xml-raw-bridge/run-test", response_model=XmlRawBridgeRunTestResponse)
async def run_xml_raw_bridge_pattern_test(payload: XmlRawBridgeRunTestRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await xml_raw_bridge.run_test(session, payload)
    await audit_service.record_action(
        session,
        request=http_request,
        action="integration_pattern.xml_raw_bridge.test_run",
        category="integration_patterns",
        object_type="integration_flow",
        object_id=payload.integration_flow_id,
        summary=f"XML Raw Bridge pattern test run {payload.integration_flow_id}",
        details={"dry_run": payload.dry_run, "success": result.success, "saved_test_case_id": str(result.saved_test_case_id)},
    )
    await session.commit()
    return result
