from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import BadRequestError
from app.flow_builder.validator import validate_builder
from app.integration_bus import repository as bus_repository
from app.integration_flows import repository as flow_repository
from app.integration_flows import service as integration_flows_service
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master import service as master_service
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.schemas import CompileDraftResponse, CompiledRunTestRequest, InputContract, InputParseRequest
from app.integration_patterns.schemas import (
    RequestPrintCreateResponse,
    RequestPrintPatternRequest,
    RequestPrintPreviewResponse,
    RequestPrintRunTestRequest,
    RequestPrintRunTestResponse,
    RequestPrintTestPrintRequest,
    RequestPrintTestPrintResponse,
)
from app.packages_training.mock_printer import print_label
from app.printing.models import PrintPrinter
from app.test_console.models import SavedTestCase
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import render_template

DEFAULT_SAMPLE = {
    "operation": "print_labels",
    "printer": "LINE-1-ZEBRA",
    "job_key": "ORDER-123",
    "labels": [
        {"sequence_no": 1, "sku": "ABC-123", "title": "Плата ABC", "code": "010464615169738421ABC", "qty": 1},
        {"sequence_no": 2, "sku": "XYZ-777", "title": "Модуль XYZ", "code": "010464615169738421XYZ", "qty": 1},
    ],
}

DEFAULT_ZPL = """^XA
^CI28
^FO30,30^A0N,30,30^FD{{label.title}}^FS
^FO30,70^A0N,24,24^FDSKU: {{label.sku}}^FS
^FO30,110^BXN,5,200^FD{{label.code}}^FS
^FO30,300^A0N,24,24^FD#{{label.sequence_no}} / {{request.body.job_key}}^FS
^XZ"""

PLACEHOLDER_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")


async def preview_pattern(session: AsyncSession, request: RequestPrintPatternRequest) -> RequestPrintPreviewResponse:
    contract = _contract(request)
    sample = _sample_body(contract)
    input_validation = master_service.validate_input_contract(contract)
    builder_json = _builder_json(request, contract)
    builder_validation = validate_builder(builder_json)

    selected_printer, printer_errors = _selected_printer(sample, request)
    labels, label_errors = _labels(sample, request)
    printer_info, printer_warnings = await _printer_info(session, selected_printer) if selected_printer else (None, [])
    rendered_first = ""
    rendered_all = ""
    zpl_errors: list[str] = []
    if labels:
        rendered, zpl_errors = _render_labels(request.zpl.template or DEFAULT_ZPL, sample, labels, request.labels.item_as)
        if rendered:
            rendered_first = rendered[0]
            rendered_all = "\n".join(rendered)
    response_to_caller = _response_preview(request, selected_printer or "", len(labels), dry_run=request.print_mode.mode == "dry_run")

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *printer_errors,
            *label_errors,
            *_printer_required_errors(selected_printer, printer_info),
            *zpl_errors,
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("errors", [])],
        ]
    )
    warnings = _dedupe(
        [
            *printer_warnings,
            *([] if request.print_mode.mode == "dry_run" else ["Test print / print all отправляет ZPL на принтер при реальном запуске. В saved test case используйте dry-run."]),
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("warnings", [])],
        ]
    )

    return RequestPrintPreviewResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        endpoint={"method": "POST", "url": master_service.endpoint_url(contract.slug)},
        incoming_request=sample,
        selected_printer=printer_info or ({"name": selected_printer, "status": "not_found"} if selected_printer else None),
        labels_count=len(labels),
        rendered_zpl_first_label=rendered_first,
        rendered_zpl_all_labels=rendered_all,
        print_action=request.print_mode.mode,
        response_to_caller=response_to_caller,
        human_steps=[
            "Получен запрос на печать",
            "Выбран принтер",
            "Сформированы ZPL-этикетки",
            "Создано задание печати",
            "ZPL отправлен на принтер" if request.print_mode.mode != "dry_run" else "Dry-run: ZPL не отправляется на принтер",
            "Статус печати возвращён вызывающей системе",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "printer_selection": request.printer_selection.model_dump(mode="json"),
            "labels": request.labels.model_dump(mode="json"),
            "zpl": request.zpl.model_dump(mode="json"),
            "print_mode": request.print_mode.model_dump(mode="json"),
            "response": request.response.model_dump(mode="json"),
            "builder_json": builder_json,
            "builder_validation": builder_validation,
        },
    )


async def create_pattern(session: AsyncSession, request: RequestPrintPatternRequest) -> RequestPrintCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
    draft = await master_service.save_draft(session, contract, parse_result)
    builder_json = preview.advanced.get("builder_json")
    if not isinstance(builder_json, dict):
        raise BadRequestError("Preview не вернул builder_json для сохранения. Повторите preview и create.")
    flow = await integration_flows_service.create_flow(session, _flow_payload(contract, builder_json, request, enabled=False))
    test_case = await _test_case_for_flow(session, flow)
    if flow.endpoint_id is None or flow.route_id is None:
        raise BadRequestError("Compiled integration was created without endpoint or route. Transaction rolled back.")
    return RequestPrintCreateResponse(draft_id=draft.id, compile=_compile_response(flow, test_case), preview=preview)


async def run_test(session: AsyncSession, request: RequestPrintRunTestRequest) -> RequestPrintRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return RequestPrintRunTestResponse(**result.model_dump())


async def test_print(session: AsyncSession, request: RequestPrintTestPrintRequest) -> RequestPrintTestPrintResponse:
    preview = await preview_pattern(session, request)
    if not preview.valid:
        return RequestPrintTestPrintResponse(preview=preview, print_result={"success": False, "errors": preview.errors})
    sample = _sample_body(_contract(request))
    labels, _ = _labels(sample, request)
    selected_printer, _ = _selected_printer(sample, request)
    rendered, _ = _render_labels(request.zpl.template or DEFAULT_ZPL, sample, labels, request.labels.item_as)
    target = await _print_target(session, selected_printer or "")
    if target is None:
        return RequestPrintTestPrintResponse(preview=preview, print_result={"success": False, "error_code": "PRINT_PRINTER_NOT_FOUND", "error_message": f"Принтер {selected_printer} не найден."})
    dry_run = request.dry_run or request.print_mode.mode == "dry_run"
    if target.get("kind") == "training_mock":
        status_code, body = print_label({"printer": selected_printer, "zpl": "\n".join(rendered[: request.limit]), "labels_count": min(request.limit, len(rendered)), "dry_run": dry_run})
        return RequestPrintTestPrintResponse(preview=preview, print_result={"success": status_code < 400 and body.get("success") is not False, "status_code": status_code, "body": body})

    from app.printing import service as printing_service
    from app.printing.schemas import PrintBatchRequest, PrintJobCreate, PrintJobLineCreate

    printer = target["printer"]
    job_key = f"{sample.get('job_key') or request.slug}-test-print"
    lines = [PrintJobLineCreate(sequence_no=_sequence_no(item, index), code=str(item.get("code")), zpl=rendered[index]) for index, item in enumerate(labels)]
    job = await printing_service.create_job(
        session,
        PrintJobCreate(
            job_key=job_key,
            printer_id=printer.id,
            source_system="Pattern test print",
            source_document_id=str(sample.get("job_key") or job_key),
            source_document_name="request_print test print",
            label_settings_json={"pattern": "request_print", "test_print": True},
            lines=lines,
        ),
    )
    batch = await printing_service.send_batch(session, job.id, PrintBatchRequest(limit=request.limit, dry_run=dry_run))
    return RequestPrintTestPrintResponse(
        preview=preview,
        print_result={
            "success": batch.failed == 0,
            "job_id": str(batch.job.id),
            "status": batch.job.status.value if hasattr(batch.job.status, "value") else str(batch.job.status),
            "processed": batch.processed,
            "sent": batch.sent,
            "failed": batch.failed,
            "dry_run": batch.dry_run,
        },
    )


def _contract(request: RequestPrintPatternRequest) -> InputContract:
    slug = request.slug.strip()
    contract = request.input_contract
    sample = contract.sample if contract.sample not in (None, "") else DEFAULT_SAMPLE
    if isinstance(sample, str):
        try:
            sample = json.loads(sample)
        except json.JSONDecodeError:
            sample = DEFAULT_SAMPLE
    fields = list(contract.fields)
    if not fields:
        try:
            parsed = master_service.parse_contract_input(InputParseRequest(input_mode="json", sample=sample, scenario_key="onec_print_request"))
            fields = parsed.fields
        except BadRequestError:
            fields = []
    operation_key = contract.operation_key
    if operation_key.type == "field" and not operation_key.field_path:
        operation_key = operation_key.model_copy(update={"field_path": "request.body.operation", "value": "print_labels"})
    business_key = contract.business_key
    if not business_key.path:
        business_key = business_key.model_copy(update={"path": "request.body.job_key"})
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": slug,
            "input_mode": "json",
            "source_system": contract.source_system or "onec",
            "scenario_key": contract.scenario_key or "onec_print_request",
            "sample": sample,
            "fields": fields,
            "operation_key": operation_key,
            "business_key": business_key,
            "endpoint_url": master_service.endpoint_url(slug),
        }
    )


def _sample_body(contract: InputContract) -> dict[str, Any]:
    sample = contract.sample
    if isinstance(sample, str):
        try:
            sample = json.loads(sample)
        except json.JSONDecodeError:
            return dict(DEFAULT_SAMPLE)
    return sample if isinstance(sample, dict) else dict(DEFAULT_SAMPLE)


def _scope(sample: dict[str, Any], variables: dict[str, Any] | None = None) -> dict[str, Any]:
    values = variables or {}
    return {"request": {"body": sample}, "variables": values, **values}


def _selected_printer(sample: dict[str, Any], request: RequestPrintPatternRequest) -> tuple[str | None, list[str]]:
    selection = request.printer_selection
    if selection.mode == "rule_based":
        return None, ["Выбор принтера по правилу / складу будет добавлен позже."]
    if selection.mode == "fixed":
        name = selection.fixed_printer_name.strip()
        return name or None, [] if name else ["Выберите fixed printer."]
    try:
        value = resolve_path(_scope(sample), selection.path or "request.body.printer")
    except PathResolutionError:
        return None, ["Принтер не найден в request.body.printer."]
    name = str(value or "").strip()
    return name or None, [] if name else ["Принтер не выбран в request.body.printer."]


def _labels(sample: dict[str, Any], request: RequestPrintPatternRequest) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        value = resolve_path(_scope(sample), request.labels.path or "request.body.labels")
    except PathResolutionError:
        return [], ["В запросе нет массива labels[]."]
    if not isinstance(value, list):
        return [], ["В запросе нет массива labels[]."]
    if not value:
        return [], ["Массив labels пустой."]
    labels = [item for item in value if isinstance(item, dict)]
    if len(labels) != len(value):
        return labels, ["Каждая строка labels[] должна быть JSON object."]
    errors: list[str] = []
    for index, item in enumerate(labels):
        for field in request.labels.required_fields or ["code"]:
            key = _label_key(field)
            if item.get(key) in (None, ""):
                if key == "code":
                    errors.append(f"В labels[{index}] нет поля code. Нечего печатать в DataMatrix.")
                else:
                    errors.append(f"В labels[{index}] нет обязательного поля {key}.")
    return labels, errors


def _label_key(field: str) -> str:
    return str(field).removeprefix("label.").strip()


async def _printer_info(session: AsyncSession, selected_printer: str | None) -> tuple[dict[str, Any] | None, list[str]]:
    if not selected_printer:
        return None, []
    target = await _print_target(session, selected_printer)
    if target is None:
        names = await _available_printer_names(session)
        if not names:
            return None, ["Нет настроенных принтеров. Создайте Printer connector или установите Printer Package."]
        return None, []
    if target.get("kind") == "training_mock":
        connector = target["connector"]
        return {"name": selected_printer, "type": "training_mock", "connector_name": connector.name, "enabled": connector.enabled}, []
    printer = target["printer"]
    return {"id": str(printer.id), "name": printer.name, "type": "print_printer", "enabled": printer.enabled, "dpi": printer.dpi}, []


async def _print_target(session: AsyncSession, selected_printer: str) -> dict[str, Any] | None:
    if not selected_printer:
        return None
    printer_result = await session.execute(select(PrintPrinter).where(PrintPrinter.name == selected_printer))
    printer = printer_result.scalar_one_or_none()
    if printer is not None:
        return {"kind": "print_printer", "printer": printer}
    connector_result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == selected_printer))
    connector = connector_result.scalar_one_or_none()
    if connector is not None and (connector.config_json or {}).get("training_mock_printer"):
        return {"kind": "training_mock", "connector": connector}
    training_result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == "Training Printer"))
    training = training_result.scalar_one_or_none()
    if training is not None and (training.config_json or {}).get("training_mock_printer"):
        return {"kind": "training_mock", "connector": training}
    return None


async def _available_printer_names(session: AsyncSession) -> list[str]:
    printer_result = await session.execute(select(PrintPrinter.name).order_by(PrintPrinter.name))
    connector_result = await session.execute(select(ConnectorInstance).order_by(ConnectorInstance.name))
    connectors = [item.name for item in connector_result.scalars().all() if (item.config_json or {}).get("training_mock_printer")]
    return [*printer_result.scalars().all(), *connectors]


def _printer_required_errors(selected_printer: str | None, printer_info: dict[str, Any] | None) -> list[str]:
    if selected_printer and printer_info is None:
        return [f"Принтер {selected_printer} не найден. Проверьте Printer connector или поле request.body.printer."]
    return []


def _render_labels(template: str, sample: dict[str, Any], labels: list[dict[str, Any]], item_as: str) -> tuple[list[str], list[str]]:
    rendered: list[str] = []
    errors: list[str] = []
    for index, label in enumerate(labels):
        scope = _scope(sample, {item_as: label, "label": label, "labels": {"items": labels, "length": len(labels)}, "label_index": index})
        try:
            zpl = str(render_template(template, scope))
        except PathResolutionError as exc:
            errors.append(_friendly_missing_variable(exc.path, item_as))
            continue
        if "^XA" not in zpl or "^XZ" not in zpl:
            errors.append(f"ZPL для labels[{index}] должен содержать ^XA и ^XZ.")
        rendered.append(zpl)
    return rendered, _dedupe(errors)


def _friendly_missing_variable(path: str, item_as: str) -> str:
    if path.startswith(f"{item_as}.") or path.startswith("label."):
        return f"В ZPL-шаблоне используется {path}, но такого поля нет в labels[0]."
    return f"В ZPL-шаблоне используется {path}, но такая переменная не создана."


def _response_preview(request: RequestPrintPatternRequest, selected_printer: str, labels_count: int, *, dry_run: bool) -> Any:
    if request.response.type == "accepted_event":
        return {"accepted": True, "event_id": "preview-event-001", "run_id": "preview-run-001"}
    raw = {"success": True, "job_id": "PRINT-PREVIEW-001", "status": "dry_run" if dry_run else "sent"}
    if request.response.type == "raw_printer_response":
        return raw
    return {"success": True, "print_job_id": raw["job_id"], "labels_count": labels_count, "printer": selected_printer, "status": raw["status"]}


def _builder_json(request: RequestPrintPatternRequest, contract: InputContract) -> dict[str, Any]:
    return {
        "version": 1,
        "source": {
            "generated_by": "request_print_pattern",
            "pattern_id": "request_print",
            "input_mode": "json",
            "sample": contract.sample,
            "operation_key": contract.operation_key.model_dump(mode="json"),
            "business_key": contract.business_key.model_dump(mode="json"),
            "human_labels": [
                "Получен запрос на печать",
                "Выбран принтер",
                "Сформированы ZPL-этикетки",
                "Создано задание печати",
                "ZPL отправлен на принтер",
                "Статус печати возвращён вызывающей системе",
            ],
        },
        "steps": [
            {
                "id": "print_labels",
                "type": "print_labels",
                "name": "Сформированы и отправлены ZPL-этикетки",
                "printer_selection": request.printer_selection.model_dump(mode="json"),
                "labels": request.labels.model_dump(mode="json"),
                "zpl_template": request.zpl.template or DEFAULT_ZPL,
                "print_mode": request.print_mode.mode,
                "save_as": "print_status",
            },
            _return_response_step(request),
        ],
    }


def _return_response_step(request: RequestPrintPatternRequest) -> dict[str, Any]:
    if request.response.type == "accepted_event":
        return {"id": "return_print_status", "type": "return_response", "name": "Статус печати возвращён вызывающей системе", "status_code": 202, "body": {"accepted": True, "event_id": "{{context.event_id}}", "run_id": "{{context.run_id}}"}, "headers": {"Content-Type": "application/json"}, "response_body_type": "json"}
    body: Any = "{{printer_response}}" if request.response.type == "raw_printer_response" else "{{print_status}}"
    return {"id": "return_print_status", "type": "return_response", "name": "Статус печати возвращён вызывающей системе", "status_code": request.response.status_code, "body": body, "headers": request.response.headers, "response_body_type": "json"}


def _flow_payload(contract: InputContract, builder_json: dict[str, Any], request: RequestPrintPatternRequest, *, enabled: bool) -> IntegrationFlowCreate:
    return IntegrationFlowCreate(
        name=f"{contract.name} [{contract.slug}]",
        slug=contract.slug,
        description="Created from Request -> Printer pattern wizard.",
        enabled=enabled,
        source_type=_source_type(contract.source_system),
        target_type=IntegrationFlowTargetType.PRINTER,
        endpoint=EndpointBuilderConfig(input_mode="json", response_mode="sync_response", auth_mode="none", auth_config_json={}),
        matcher_group_json=_matcher_group(contract),
        action_json={"type": "return_response", "operation": "request_print", "business_object": contract.slug, "body_mode": "json", "response_mode": "sync_response", "comment": "Created from Request -> Printer wizard"},
        response_config_json={"response_mode": "sync_response", "pattern_id": "request_print", "business_key": contract.business_key.model_dump(mode="json"), "response": request.response.model_dump(mode="json")},
        builder_json=builder_json,
        test_payload_json=_sample_body(contract),
        test_payload_text=None,
    )


def _matcher_group(contract: InputContract) -> dict[str, Any]:
    operation_key = contract.operation_key
    if operation_key.type in {"endpoint", "none"}:
        return {"mode": "all", "rules": [{"type": "always"}]}
    rules: list[dict[str, Any]] = []
    if operation_key.field_path and operation_key.value is not None:
        rules.append({"type": "body_path_equals", "path": _relative_path(operation_key.field_path), "value": operation_key.value})
    for fallback in operation_key.fallback_paths:
        if operation_key.value is not None:
            rules.append({"type": "body_path_equals", "path": _relative_path(fallback), "value": operation_key.value})
    return {"mode": "any", "rules": rules or [{"type": "always"}]}


def _relative_path(path: str) -> str:
    return path.replace("request.body.", "", 1) if path.startswith("request.body.") else path


def _source_type(source_system: str) -> IntegrationFlowSourceType:
    mapping = {"onec": IntegrationFlowSourceType.ONEC, "1c": IntegrationFlowSourceType.ONEC, "wms": IntegrationFlowSourceType.WMS, "external_api": IntegrationFlowSourceType.EXTERNAL_API, "webhook": IntegrationFlowSourceType.WEBHOOK}
    return mapping.get((source_system or "").lower(), IntegrationFlowSourceType.ONEC)


def _compile_response(flow: IntegrationFlow, test_case: SavedTestCase | None) -> CompileDraftResponse:
    return CompileDraftResponse(
        success=True,
        integration_flow_id=flow.id,
        endpoint_id=flow.endpoint_id,  # type: ignore[arg-type]
        route_id=flow.route_id,  # type: ignore[arg-type]
        saved_test_case_id=test_case.id if test_case else None,
        enabled=flow.enabled,
        endpoint={"method": "POST", "url": master_service.endpoint_url(flow.slug)},
        curl_example=integration_flows_service.curl_example(flow.slug, "json", flow.test_payload_json),
        onec_http_example=integration_flows_service.onec_http_example(flow.slug, "json"),
        next_actions=[
            "Выполните dry run.",
            "Сделайте test print одной этикетки.",
            "Откройте Timeline и проверьте artifacts incoming_print_request.json, rendered_zpl_first_label.zpl, printer_response.json.",
            "Если всё работает, включите интеграцию.",
        ],
    )


async def _test_case_for_flow(session: AsyncSession, flow: IntegrationFlow) -> SavedTestCase | None:
    if flow.endpoint_id is None:
        return None
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.endpoint_id == flow.endpoint_id).limit(1))
    return result.scalar_one_or_none()


async def _ensure_slug_available(session: AsyncSession, slug: str) -> None:
    master_service.validate_slug(slug)
    draft_result = await session.execute(select(IntegrationMasterDraft.id).where(IntegrationMasterDraft.slug == slug).limit(1))
    if draft_result.scalar_one_or_none() is not None:
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await bus_repository.get_endpoint_by_slug(session, slug):
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await flow_repository.get_by_slug(session, slug):
        raise BadRequestError(f"Integration Flow со slug {slug} уже существует. Выберите другой slug.")


def _sequence_no(item: dict[str, Any], index: int) -> int:
    try:
        value = int(item.get("sequence_no", index + 1))
    except (TypeError, ValueError):
        return index + 1
    return value if value > 0 else index + 1


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
