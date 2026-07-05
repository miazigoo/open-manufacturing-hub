from __future__ import annotations

from typing import Any

from app.packages_training.presets import BASE_BODY, PRINT_BODY, XML_BODY

TRAINING_EXAMPLES: dict[str, dict[str, Any]] = {
    "training.onec.find_contractor_by_inn": {
        "title": {"ru": "Найти контрагента по ИНН", "en": "Find contractor by INN", "zh": "按 INN 查找客户"},
        "description": {"ru": "Проверяет Training OData ERP и фильтр ИНН eq '7707083893'.", "en": "Checks Training OData ERP and the INN eq filter.", "zh": "检查 Training OData ERP 和 INN eq 过滤器。"},
        "endpoint_slug": "training-onec-two-odata-dnp",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": BASE_BODY,
        "expected": {"status": "success", "lookup": "contractor"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.onec.find_product_by_article": {
        "title": {"ru": "Найти номенклатуру по артикулу", "en": "Find product by article", "zh": "按货号查找商品"},
        "description": {"ru": "Показывает OData-фильтр Артикул eq 'A-100' и выбор только нужных JSON-полей.", "en": "Shows an OData Article filter and field selection.", "zh": "展示按货号过滤和字段选择。"},
        "endpoint_slug": "training-onec-two-odata-dnp",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": BASE_BODY,
        "expected": {"status": "success", "lookup": "product"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.onec.post_two_odata_to_dnp": {
        "title": {"ru": "1C POST -> две OData выборки -> JSON -> DNP", "en": "1C POST -> two OData lookups -> JSON -> DNP", "zh": "1C POST -> 两次 OData 查询 -> JSON -> DNP"},
        "description": {"ru": "Главный учебный сценарий: из 1С приходят ключи, OMH ищет контрагента/товар и отправляет DNP JSON.", "en": "Golden training scenario with two OData lookups and target JSON.", "zh": "包含两次 OData 查询和目标 JSON 的核心训练场景。"},
        "endpoint_slug": "training-onec-two-odata-dnp",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": BASE_BODY,
        "expected": {"status": "success", "lookups": 2, "target": "Training DNP API"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.onec.xml_raw_bridge": {
        "title": {"ru": "1C XML raw bridge", "en": "1C XML raw bridge", "zh": "1C XML 原样桥接"},
        "description": {"ru": "Показывает, как принять XML от 1С и сохранить тело без преобразования.", "en": "Shows how to accept raw 1C XML without mutation.", "zh": "展示如何接收未修改的 1C XML。"},
        "endpoint_slug": "training-onec-xml-raw-bridge",
        "method": "POST",
        "input_mode": "xml",
        "headers": {"Content-Type": "application/xml", "X-OMH-Source": "training-docs"},
        "body_text": XML_BODY,
        "expected": {"status": "forwarded"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.onec.print_label": {
        "title": {"ru": "1C отправляет этикетку на принтер", "en": "1C sends a label to printer", "zh": "1C 向打印机发送标签"},
        "description": {"ru": "Исполняемый пример печати через Training Printer.", "en": "Executable mock print example.", "zh": "可执行的模拟打印示例。"},
        "endpoint_slug": "training-onec-printer",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": PRINT_BODY,
        "expected": {"status": "printed"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.errors.contractor_not_found": {
        "title": {"ru": "Ошибка: контрагент не найден", "en": "Error: contractor not found", "zh": "错误：未找到客户"},
        "description": {"ru": "Негативный пример: обязательная OData-выборка возвращает пусто.", "en": "Negative example: required OData lookup is empty.", "zh": "负面示例：必需的 OData 查询为空。"},
        "endpoint_slug": "training-error-contractor-not-found",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": {**BASE_BODY, "inn": "9999999999"},
        "expected": {"status": "failed", "error": "ODATA_RESULT_EMPTY"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.errors.dnp_rejected": {
        "title": {"ru": "Ошибка: DNP отклонил пул", "en": "Error: DNP rejected pool", "zh": "错误：DNP 拒绝池"},
        "description": {"ru": "Негативный пример: POOL-ERROR возвращает DNP_POOL_REJECTED.", "en": "Negative example: POOL-ERROR returns DNP_POOL_REJECTED.", "zh": "负面示例：POOL-ERROR 返回 DNP_POOL_REJECTED。"},
        "endpoint_slug": "training-error-dnp-rejected",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": {**BASE_BODY, "pool_id": "POOL-ERROR"},
        "expected": {"status": "failed", "error": "DNP_POOL_REJECTED"},
        "runnable": True,
        "requires_setup": False,
    },
    "training.errors.printer_offline": {
        "title": {"ru": "Ошибка: принтер offline", "en": "Error: printer offline", "zh": "错误：打印机离线"},
        "description": {"ru": "Негативный пример: TRAINING-OFFLINE возвращает ошибку печати.", "en": "Negative example: TRAINING-OFFLINE returns a print error.", "zh": "负面示例：TRAINING-OFFLINE 返回打印错误。"},
        "endpoint_slug": "training-error-printer-offline",
        "method": "POST",
        "input_mode": "json",
        "headers": {"Content-Type": "application/json", "X-OMH-Source": "training-docs"},
        "body": {**PRINT_BODY, "printer": "TRAINING-OFFLINE"},
        "expected": {"status": "failed", "error": "TRAINING_PRINTER_OFFLINE"},
        "runnable": True,
        "requires_setup": False,
    },
}


def list_examples() -> list[dict[str, Any]]:
    return [{"id": example_id, **example} for example_id, example in sorted(TRAINING_EXAMPLES.items())]


def get_example(example_id: str) -> dict[str, Any] | None:
    example = TRAINING_EXAMPLES.get(example_id)
    return {"id": example_id, **example} if example else None

