from __future__ import annotations

from app.core.errors import BadRequestError
from app.integration_patterns import presets  # noqa: F401 - registers built-in patterns
from app.integration_patterns.registry import registry
from app.integration_patterns.schemas import (
    IntegrationPattern,
    PatternRecommendRequest,
    PatternRecommendResponse,
    PatternRecommendation,
    PatternStartResponse,
)


def list_patterns() -> list[IntegrationPattern]:
    return registry.list()


def get_pattern(pattern_id: str) -> IntegrationPattern:
    return registry.get(pattern_id)


def recommend_patterns(request: PatternRecommendRequest) -> PatternRecommendResponse:
    candidates: list[tuple[str, float, str]] = []
    input_mode = request.input_mode
    source_system = (request.source_system or "").lower()

    if request.needs_file_save:
        candidates.append(("request_save_file_optional_forward", 0.98, "Нужно сохранить файл и, возможно, выполнить SMB/forward."))
    if request.needs_print:
        candidates.append(("request_print", 0.96, "Финальное действие — печать: JSON labels[], ZPL template и print job status."))
    if request.needs_polling or source_system in {"omh", "omh_scheduler", "schedule", "scheduled"}:
        candidates.append(("poll_odata_send_target", 0.93, "OMH сам запускает интеграцию по расписанию."))
    if source_system == "wms" and (request.needs_writeback or request.needs_send_endpoint):
        candidates.append(("wms_fact_to_onec", 0.97, "WMS/API присылает факт операции, OMH вызывает 1С HTTP service и возвращает ответ WMS."))
    if request.needs_writeback:
        candidates.append(("source_web_api_writeback_onec", 0.93, "Нужно записать внешний результат обратно в 1С."))
    if input_mode == "xml" and request.needs_odata and request.needs_response:
        candidates.append(("xml_odata_xml_response", 0.94, "XML-вход, чтение OData и XML/синхронный ответ."))
    if input_mode == "xml" and request.needs_send_endpoint and not request.needs_odata:
        candidates.append(("xml_raw_bridge", 0.9, "XML нужно безопасно переслать без OData enrichment."))
    if request.needs_odata and request.needs_foreach and request.needs_send_endpoint:
        candidates.append(("request_odata_object_foreach_send_endpoint", 0.96, "Нужно найти документ, прочитать строки, выполнить foreach OData и отправить результат во внешний endpoint."))
    if request.needs_odata and request.needs_foreach and request.needs_response:
        candidates.append(("request_multiple_odata_response", 0.9, "Нужно прочитать документ и связанные строки, затем вернуть ответ."))
    if request.needs_odata and request.needs_send_endpoint:
        candidates.append(("request_odata_send_endpoint", 0.88, "Нужно обогатить запрос через OData и отправить результат дальше."))
    if request.needs_send_endpoint and not request.needs_odata:
        candidates.append(("request_odata_send_endpoint", 0.64, "Нужна отправка во внешний endpoint; OData enrichment можно пропустить или добавить позже."))
    if request.needs_odata and request.needs_response:
        candidates.append(("request_odata_response", 0.86, "Нужно прочитать 1С OData и вернуть ответ вызывающей системе."))
    if request.needs_response and not request.needs_odata and not request.needs_send_endpoint:
        candidates.append(("request_response", 0.74, "Нужен простой синхронный ответ без OData enrichment."))

    if not candidates:
        candidates.append(("request_response", 0.45, "Недостаточно признаков, начните с простого request/response pattern."))

    best_by_id: dict[str, tuple[float, str]] = {}
    for pattern_id, confidence, reason in candidates:
        current = best_by_id.get(pattern_id)
        if current is None or confidence > current[0]:
            best_by_id[pattern_id] = (confidence, reason)

    recommendations = [
        PatternRecommendation(
            pattern_id=pattern_id,
            confidence=round(confidence, 2),
            reason=reason,
            pattern=get_pattern(pattern_id),
        )
        for pattern_id, (confidence, reason) in best_by_id.items()
    ]
    recommendations.sort(key=lambda item: item.confidence, reverse=True)
    return PatternRecommendResponse(recommended_patterns=recommendations[:3])


def start_pattern(pattern_id: str) -> PatternStartResponse:
    pattern = get_pattern(pattern_id)
    if pattern.status != "available" or not pattern.wizard_route:
        reason = pattern.start_disabled_reason or {"ru": "Для этого паттерна мастер ещё не реализован.", "en": "This pattern does not have an implemented wizard yet."}
        raise BadRequestError(reason.get("ru") or reason.get("en") or "Pattern is not startable")
    return PatternStartResponse(
        pattern_id=pattern.pattern_id,
        wizard_route=pattern.wizard_route,
        recommended_wizard=pattern.recommended_wizard,
        wizard_label=pattern.wizard_label,
        initial_steps=pattern.initial_steps,
        explanation=pattern.description,
        examples=pattern.examples,
        package_requirements=pattern.package_requirements,
    )
