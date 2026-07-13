# Integration Requirements Coverage Report

Generated from `backend/app/integration_coverage/registry.py`.

## Summary

- Total requirements: 12
- Ready: 7
- Partial: 4
- Planned: 0
- Missing docs: 1
- Missing wizard: 0
- Average readiness: 90%

## Matrix

| Requirement ID | Requirement | Status | Score | Pattern | Wizard | Docs | Training | Troubleshooting | E2E | Gaps |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `external_api_asks_1c_by_inn` | Внешний API спрашивает контрагента по ИНН | `ready` | 100 | `request_odata_response` | /master?pattern=request_odata_response | /docs/onec/recipes/external-service-lookup-contractor | training.onec.find_contractor_by_inn | /docs/onec/odata-course/empty-result-debugging<br>/docs/onec/troubleshooting/odata-empty-result | `ready` | - |
| `external_api_asks_1c_order_xml_response` | Внешний сервис спрашивает заказ из 1С | `ready` | 100 | `request_multiple_odata_response` | /master?pattern=request_multiple_odata_response | /docs/onec/recipes/request-odata-xml-response | training.onec.lookup_order_products_xml | /docs/onec/troubleshooting/odata-step-failed<br>/docs/onec/troubleshooting/json-builder-variable-missing | `ready` | - |
| `onec_sends_order_to_website_api` | 1С отправляет заказ во внешний API | `ready` | 100 | `request_odata_send_endpoint` | /master?pattern=request_odata_send_endpoint | /docs/onec/recipes/request-odata-send-endpoint | training.onec.post_two_odata_to_dnp | /docs/onec/troubleshooting/target-api-returned-error<br>/docs/onec/troubleshooting/json-builder-variable-missing | `ready` | - |
| `dnp_chz_code_pool_sync` | DnP запрашивает пул кодов Честного знака из 1С | `partial` | 92 | `request_odata_object_foreach_send_endpoint` | /master?pattern=request_odata_object_foreach_send_endpoint | /docs/onec/recipes/dnp-chz-code-pool-sync | training.onec.post_two_odata_to_dnp | /docs/onec/troubleshooting/odata-step-failed<br>/docs/onec/troubleshooting/target-api-returned-error | `ready` | Training example покрывает две OData выборки, но не весь production foreach-регистр кодов ЧЗ.<br>Нет полноценного training example. Status: partial. |
| `onec_sends_chz_code_pool_file` | 1С отправляет пул кодов Честного знака файлом | `partial` | 78 | `request_save_file_optional_forward` | /marking-code-pools | /docs/onec/recipes/onec-sends-chz-code-pool-file | - | /docs/onec/troubleshooting/by-scenario | `ready` | Нужен training sandbox example с base64-кодами и mock forward endpoint.<br>Нет полноценного training example. Status: missing_training.<br>Troubleshooting не полностью привязан к сценарию. Status: partial. |
| `onec_xml_raw_bridge` | 1С отправляет XML в другую 1С без изменения | `ready` | 100 | `xml_raw_bridge` | /master?pattern=xml_raw_bridge | /docs/onec/scenarios/xml-raw-forward<br>/docs/onec/recipes/xml-raw-forwarding | training.onec.xml_raw_bridge | /docs/onec/troubleshooting/xml-parse-error | `ready` | - |
| `xml_input_odata_xml_response` | XML request -> 1С OData -> XML response | `ready` | 100 | `xml_odata_xml_response` | /master?pattern=xml_odata_xml_response | /docs/onec/scenarios/xml-inn-lookup<br>/docs/onec/recipes/xml-input-odata-xml-response | training.onec.xml_lookup_order_response | /docs/onec/troubleshooting/xml-parse-error<br>/docs/onec/troubleshooting/odata-empty-result | `ready` | - |
| `wms_shipment_fact_to_onec` | WMS отправляет складской факт в 1С | `ready` | 100 | `wms_fact_to_onec` | /master?pattern=wms_fact_to_onec | /docs/onec/scenarios/wms-api-to-1c<br>/docs/onec/recipes/wms-shipment-fact-to-onec | training.wms.shipment_fact_to_onec | /docs/onec/troubleshooting/by-scenario<br>/docs/onec/troubleshooting/target-api-returned-error | `ready` | - |
| `onec_site_writeback` | 1С -> сайт -> запись ответа обратно в 1С | `partial` | 85 | `source_web_api_writeback_onec` | /master?pattern=source_web_api_writeback_onec | /docs/onec/recipes/onec-site-writeback | - | /docs/onec/troubleshooting/target-api-returned-error<br>/docs/onec/troubleshooting/json-builder-variable-missing | `ready` | Нужен dedicated training example для site writeback с mock site + mock 1C HTTP service.<br>Нет полноценного training example. Status: missing_training. |
| `onec_print_request` | 1С отправляет данные на печать | `ready` | 100 | `request_print` | /master?pattern=request_print | /docs/onec/recipes/onec-print-labels<br>/docs/onec/scenarios/onec-to-printer<br>/docs/printer/printer/overview | training.print.labels | /docs/onec/troubleshooting/printer-unavailable<br>/docs/onec/troubleshooting/print-job-not-printed | `ready` | - |
| `poll_odata_send_target` | OMH периодически читает OData и отправляет изменения | `partial` | 92 | `poll_odata_send_target` | /master?pattern=poll_odata_send_target | /docs/onec/recipes/poll-odata-send-target<br>/docs/onec/scenarios/odata-polling-to-target<br>/docs/core/start/integration-patterns | training.polling.odata_orders_to_wms | /docs/onec/troubleshooting/by-scenario<br>/docs/onec/troubleshooting/event-stuck-in-queue | `ready` | Manual run и run history готовы; interval scheduler loop остаётся существующим/planned MVP, без distributed locks/retry/DLQ.<br>Troubleshooting не полностью привязан к сценарию. Status: partial. |
| `request_validate_rules_route_targets` | Request -> validation/rules -> разные targets | `missing_docs` | 28 | `request_response` | /integration-designer | /docs/core/start/integration-patterns<br>/docs/onec/troubleshooting/business-rule-stopped-flow | - | /docs/onec/troubleshooting/business-rule-stopped-flow<br>/docs/onec/troubleshooting/by-scenario | `missing` | Нужен отдельный product recipe для validation/rules routing и coverage-driven стартового сценария.<br>Мастер/workbench не полностью готов. Status: partial.<br>Документация не полностью закрывает сценарий. Status: missing_docs.<br>Нет полноценного training example. Status: missing_training.<br>Нет полного E2E/pytest покрытия сценария. Status: missing. |

## Gate Rules

- `ready` requires wizard/workbench, docs, training, troubleshooting and E2E links.
- `planned` requirements may be visible as `Скоро`, but must not start from `/integration-start`.
- `missing_docs` rows are allowed only when the gap is explicit in this report.
