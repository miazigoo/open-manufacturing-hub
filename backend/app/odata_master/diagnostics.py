from __future__ import annotations

from typing import Any


def artifact_checklist(builder_json: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for step in builder_json.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_type = str(step.get("type") or "")
        artifacts, notes = _artifacts_for_step(step_type, step)
        if not artifacts:
            continue
        items.append(
            {
                "step_id": str(step.get("id") or step_type),
                "step_name": str(step.get("name") or step.get("id") or step_type),
                "step_type": step_type,
                "artifacts": artifacts,
                "notes": notes,
            }
        )
    return items


def run_next_actions(*, timeline_url: str | None) -> list[str]:
    if timeline_url:
        return [
            "Откройте Timeline и проверьте статусы шагов.",
            "Откройте request/response artifacts у каждого OData step.",
            "Если target вернул ошибку, откройте outgoing_request.json, incoming_response.json и external_error.json.",
            "После исправления данных используйте Replay или Dry Run из Timeline.",
        ]
    return [
        "Preview не создает событие в Timeline.",
        "Сохраните интеграцию и запустите тест, чтобы получить event_id и artifacts.",
        "Сравните preview request/response с ожидаемым контрактом внешней системы.",
    ]


def _artifacts_for_step(step_type: str, step: dict[str, Any]) -> tuple[list[str], list[str]]:
    if step_type == "read_variable":
        return ["read_variable_result.json"], ["Показывает, какой path был прочитан из входящего request."]
    if step_type == "odata_query":
        return (
            ["odata_query_request.json", "odata_query_response.json", "odata_query_result.json"],
            ["Проверяйте connection, resource, query и количество найденных строк."],
        )
    if step_type == "foreach":
        return (
            ["foreach_input.json", "foreach_<n>_odata_request.json", "foreach_<n>_odata_response.json", "foreach_result.json"],
            ["Для каждой строки массива создается отдельная пара request/response artifacts."],
        )
    if step_type == "build_json":
        return (
            ["json_builder_template.json", "json_builder_result.json"],
            ["Проверяйте, что массивы по placeholder вставились как JSON, а не как строка."],
        )
    if step_type == "call_endpoint":
        return (
            ["outgoing_request.json", "incoming_response.json", "external_error.json"],
            ["external_error.json появляется только при ошибке целевой системы."],
        )
    if step_type in {"return_response", "build_xml_response"}:
        artifacts = ["return_response.json"]
        if str(step.get("response_body_type") or "").lower() == "xml" or step.get("body_template") is not None:
            artifacts = ["xml_response_template.xml", "return_response.json", "xml_response_rendered.xml"]
        return artifacts, ["Показывает финальный ответ, который OMH вернул вызывающему."]
    return [], []
