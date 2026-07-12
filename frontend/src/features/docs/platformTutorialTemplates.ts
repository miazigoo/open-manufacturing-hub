const requiredTutorialHeadings = [
  'Что решает этот сценарий',
  'Когда использовать',
  'Что нужно заранее',
  'Схема обмена',
  'Входящий пример',
  'Подключения',
  'Операции',
  'Контракты и сопоставления',
  'Настройка по шагам',
  'Предпросмотр',
  'Тест',
  'Timeline и artifacts',
  'Частые ошибки',
  'Что делать дальше',
];

type TutorialTemplate = {
  solves: string;
  when: string[];
  before: string[];
  diagram: string[];
  inputTitle: string;
  inputLanguage: string;
  input: string[];
  curl: string[];
  pseudo1c?: string[];
  expectedLanguage?: string;
  expected: string[];
  connections: string[];
  operations: string[];
  contracts: string[];
  steps: string[];
  preview: string[];
  test: string[];
  timeline: string[];
  artifacts: string[];
  errors: string[];
  next: string[];
  training: string;
};

const tutorials: Record<string, TutorialTemplate> = {
  'external-service-lookup-contractor': {
    solves: 'Внешний сайт или сервис спрашивает OMH о контрагенте по ИНН. OMH не открывает 1С наружу, а принимает безопасный HTTP-запрос, делает OData lookup в 1С и возвращает caller-у компактный JSON или XML.',
    when: ['Caller ждёт синхронный ответ.', 'Нужно закрыть прямой доступ к 1С OData.', 'Достаточно одного lookup по ИНН или другому бизнес-ключу.', 'Нужно видеть в Timeline, какой фильтр ушёл в 1С и что вернулось.'],
    before: ['Профиль `1C OData` в Connection Center.', 'Операция чтения не нужна: мастер сам выполняет OData query.', 'Права OData-пользователя на справочник контрагентов.', 'Понимание точного поля ИНН в вашей конфигурации 1С.'],
    diagram: ['External API / site', '  -> OMH endpoint `/api/bus/in/lookup-contractor`', '  -> 1C OData `Catalog_Контрагенты`', '  -> Response Builder', '  -> JSON/XML response to caller'],
    inputTitle: 'JSON request от внешнего сервиса',
    inputLanguage: 'json',
    input: ['{', '  "operation": "lookup_contractor",', '  "inn": "7707083893"', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/lookup-contractor \\', '  -H "Content-Type: application/json" \\', '  -d \'{"operation":"lookup_contractor","inn":"7707083893"}\''],
    expected: ['{', '  "success": true,', '  "contractor_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",', '  "contractor_name": "ООО Ромашка",', '  "inn": "7707083893"', '}'],
    connections: ['`1C OData`: `OData ERP` или `Training OData ERP`.', '`Training mock`: учебный OData-профиль, если реальной 1С нет.', '`Inbound auth`: static token на endpoint, если сценарий не учебный.'],
    operations: ['OData query к `Catalog_Контрагенты`.', 'Response Builder: JSON/XML/raw response.', 'Saved Test Case: payload с ИНН и ожидаемым ответом.'],
    contracts: ['Input contract: `operation`, `inn`.', 'Output contract: `success`, `contractor_uuid`, `contractor_name`, `inn`, optional `kpp`.', 'Mapping: `contractor.Ref_Key -> contractor_uuid`, `contractor.Description -> contractor_name`.'],
    steps: ['Откройте Scenario Router и выберите сценарий “Внешний сервис спрашивает данные из 1С”.', 'Откройте мастер Request -> OData -> Response.', 'Вставьте JSON sample.', 'Выберите Connection `1C OData`.', 'Настройте resource, filter, `$select`, `$top=1`, `save_as=contractor`.', 'Настройте response body.', 'Сохраните integration disabled by default.', 'Запустите saved test case.'],
    preview: ['Rendered filter должен быть `ИНН eq \'7707083893\'`.', 'Preview показывает найденного контрагента или controlled business error.', 'Response preview не должен содержать password/token или полный OData raw body.'],
    test: ['Сначала dry-run в мастере.', 'Затем curl из этой инструкции.', 'После теста откройте событие по `operation=lookup_contractor` или trace id.'],
    timeline: ['`incoming.request` - исходный JSON.', '`route.match` - выбран endpoint и matcher.', '`odata.contractor.request` - resource, filter, select.', '`odata.contractor.response` - оригинальный ответ 1С.', '`response.rendered` - JSON/XML, который получил caller.'],
    artifacts: ['`incoming.request.json`', '`odata_query_request.json`', '`odata_query_response.json`', '`response_body.json` или `response_body.xml`'],
    errors: ['`ODATA_RESULT_EMPTY`: контрагент не найден, проверьте ИНН и поле OData.', '`ODATA_AUTH_FAILED`: логин/пароль профиля 1С неверны.', '`VARIABLE_NOT_FOUND contractor.Ref_Key`: save_as или `$select` не совпадают с response template.', '`DUPLICATE_ENDPOINT_SLUG`: endpoint уже занят.'],
    next: ['Добавьте второй lookup, если ответу нужен договор, адрес или контакт.', 'Для production включите endpoint только после успешного saved test case.', 'Если caller должен получать XML, переключите Response Builder на XML и повторите тест.'],
    training: 'Попробовать на учебном стенде: `training.onec.lookup_contractor_by_inn`.',
  },
  'request-odata-send-endpoint': {
    solves: '1С, сайт или API присылает ключ заказа. OMH ищет объект в 1С OData, собирает target payload и отправляет его во внешний REST endpoint, сохраняя исходный запрос, OData ответ, payload и response target-системы.',
    when: ['Caller не ждёт данных из 1С как конечный ответ, а хочет передать enriched payload дальше.', 'Нужно проверить OData lookup до отправки во внешний API.', 'Внешний API требует стабильный JSON/XML contract.', 'Ошибки target-системы должны сохраняться в Timeline.'],
    before: ['Профиль `1C OData` для чтения заказа.', 'Профиль `REST API` или operation в Operation Catalog для внешнего endpoint.', 'Data Contract внешнего API, если он уже известен.', 'Тестовый заказ в 1С и mock endpoint для обучения.'],
    diagram: ['1C / site / API', '  -> OMH endpoint `/api/bus/in/send-order-to-site`', '  -> 1C OData order lookup', '  -> Mapping Center / Payload Builder', '  -> REST API operation', '  -> caller response'],
    inputTitle: 'JSON request от 1С или API',
    inputLanguage: 'json',
    input: ['{', '  "operation": "send_order_to_site",', '  "order_number": "260666/6938",', '  "site_code": "B2B"', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/send-order-to-site \\', '  -H "Content-Type: application/json" \\', '  -d \'{"operation":"send_order_to_site","order_number":"260666/6938","site_code":"B2B"}\''],
    pseudo1c: ['Соединение = Новый HTTPСоединение("omh-server", 8000);', 'Запрос = Новый HTTPЗапрос("/api/bus/in/send-order-to-site");', 'Запрос.Заголовки.Вставить("Content-Type", "application/json");', 'Запрос.УстановитьТелоИзСтроки(ТелоJSON, КодировкаТекста.UTF8);', 'Ответ = Соединение.ОтправитьДляОбработки(Запрос);'],
    expected: ['{', '  "success": true,', '  "external_id": "TRAIN-ORDER-001",', '  "status": "accepted"', '}'],
    connections: ['`1C OData`: чтение заказа.', '`REST API`: сайт, DnP, WMS или mock endpoint.', '`Training External API`: безопасный учебный target.'],
    operations: ['`get_order_by_number`: OData query, `save_as=order`.', '`send_order_to_site`: REST operation with success condition.', '`extract_external_id`: optional extractor из response target.'],
    contracts: ['Input contract: `operation`, `order_number`, `site_code`.', 'Request contract target API: `source`, `site_code`, `order.uuid`, `order.number`, `order.date`.', 'Mapping: `order.Ref_Key -> order.uuid`, `request.body.site_code -> site_code`.'],
    steps: ['В Scenario Router выберите “1С отправляет данные во внешний API”.', 'Откройте Request -> OData -> Send Endpoint wizard.', 'Вставьте incoming sample.', 'Выберите OData connection и настройте lookup заказа.', 'Выберите REST operation или manual target URL.', 'Соберите payload через Mapping Center или raw JSON template.', 'Выберите response mode: proxy, fixed success или accepted event.', 'Сохраните disabled integration и saved test case.'],
    preview: ['Проверьте `Target payload`: поля из `order` должны быть заполнены.', 'Проверьте `Final URL`: base URL + operation path.', 'Dry-run не должен отправлять реальный запрос, только показать request preview.'],
    test: ['Dry-run: route + OData + payload без target send.', 'Real send: только на mock/staging endpoint.', 'Для ошибки target используйте `order_number=ERROR-500`, если работает training mock.'],
    timeline: ['`incoming.request`', '`odata.order.request`', '`odata.order.response`', '`mapping.preview` или `payload_builder_result`', '`target.request`', '`target.response`', '`caller.response`'],
    artifacts: ['`incoming.request.json`', '`odata_query_response.json`', '`target_payload.json`', '`outgoing_request.json`', '`incoming_response.json`', '`external.error.json`'],
    errors: ['`ODATA_RESULT_EMPTY`: заказ не найден.', '`MAPPING_SOURCE_NOT_FOUND`: mapping ссылается на отсутствующее поле.', '`TARGET_HTTP_500`: внешний API вернул ошибку, смотрите `target.response`.', '`TIMEOUT`: target недоступен из backend-сети.'],
    next: ['Если внешний API возвращает external_id, добавьте writeback в 1С отдельным сценарием.', 'После production smoke включите integration вручную.', 'Добавьте Operation Catalog preset, чтобы другие мастера переиспользовали target endpoint.'],
    training: 'Попробовать на учебном стенде: `training.onec.request_odata_send_endpoint`.',
  },
  'dnp-chz-code-pool-sync': {
    solves: 'DnP присылает номер заказа производства. OMH находит заказ в 1С, читает табличную часть, по каждой продукции запрашивает регистр кодов Честного знака и отправляет итоговый пул во внешний DnP endpoint.',
    when: ['Внешняя система не хранит коды, а запрашивает их из 1С по заказу.', 'Нужен foreach OData по строкам документа.', 'Нужно сохранить массив кодов как JSON array, а не строку.', 'Нужна трассировка заказа, продукции, каждого foreach-запроса и target send.'],
    before: ['Профиль `1C CHZ OData ERP`.', 'Профиль или операция `DNP API`.', 'Доступ к документу `ЗаказНаПроизводство` и регистру кодов.', 'Контракт `dnp_chz_codes_import_request` и mapping `mapping_dnp_chz_codes_import`.'],
    diagram: ['DnP', '  -> OMH endpoint `/api/bus/in/dnp-sinc-pull-codes`', '  -> OData order', '  -> OData tabular part `Продукция`', '  -> foreach OData code pool register', '  -> Mapping Center target payload', '  -> DnP API'],
    inputTitle: 'JSON request от DnP',
    inputLanguage: 'json',
    input: ['{', '  "operation": "dnp_sinc_pull_codes",', '  "sinc": "dnp_sinc_pull_codes",', '  "order_id": 10271,', '  "order_name": "26-0666/6938",', '  "Number": "260666/6938"', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/dnp-sinc-pull-codes \\', '  -H "Content-Type: application/json" \\', '  -d \'{"operation":"dnp_sinc_pull_codes","sinc":"dnp_sinc_pull_codes","order_id":10271,"order_name":"26-0666/6938","Number":"260666/6938"}\''],
    expected: ['{', '  "ok": true,', '  "sent_to": "DNP",', '  "codes_count": 2', '}'],
    connections: ['`1C CHZ OData ERP`: чтение заказа, продукции и регистра кодов.', '`DNP API`: target endpoint импорта кодов.', '`Training DNP API`: mock для dry-run/real test без production DnP.'],
    operations: ['`find_production_order`: OData query by `Number`.', '`read_order_products`: object/tabular part query.', '`read_marking_codes`: foreach OData query by product.', '`dnp_import_chz_codes`: REST operation.'],
    contracts: ['Input contract: `sinc`, `order_id`, `order_name`, `Number`.', 'Data contract: `payload.rows` array required, `payload.order_id`, `payload.order_name`, `payload.onec_order_number`.', 'Dynamic object keys: `payload.order_numbers_by_basis[order.Ref_Key] = order.Number`.', 'Raw JSON fallback разрешён только если contract ещё не описан.'],
    steps: ['Откройте Scenario Router и выберите “DnP запрашивает пул кодов ЧЗ”.', 'В мастере вставьте incoming DnP JSON.', 'Настройте OData order lookup.', 'Настройте чтение табличной части `Продукция`.', 'Настройте foreach OData по `products[]`.', 'В payload step выберите mapping `DNP — импорт кодов ЧЗ`.', 'Выберите operation `dnp_import_chz_codes`.', 'Сохраните disabled integration и запустите saved test case.'],
    preview: ['Preview должен показать `order`, `products[]`, `codes[]`, rendered dynamic object keys и target payload.', '`payload.rows` должен быть array.', '`$top` для foreach не должен превышать safety limit.'],
    test: ['Dry-run проверяет все OData steps и payload.', 'Real send разрешайте только на Training DNP или staging.', 'После test проверьте count codes и response DnP.'],
    timeline: ['`incoming.request`', '`odata.find_order.request/response`', '`odata.products.request/response`', '`foreach.codes.request[]/response[]`', '`mapping.dnp_payload`', '`target.dnp.request/response`'],
    artifacts: ['`incoming.request.json`', '`odata_order_response.json`', '`odata_products_response.json`', '`foreach_codes_merged.json`', '`target_payload.json`', '`target_response.json`'],
    errors: ['`ORDER_NOT_FOUND`: номер заказа не найден в 1С.', '`ODATA_TABULAR_PART_EMPTY`: у заказа нет продукции.', '`FOREACH_EMPTY_RESULT`: коды не найдены по продукции.', '`MAPPING_TYPE_MISMATCH`: `payload.rows` стал string вместо array.', '`DNP_REJECTED`: DnP вернул 4xx/5xx.'],
    next: ['Зафиксируйте Operation Catalog preset для DNP API.', 'Добавьте production smoke на один известный заказ.', 'Перед включением проверьте, что endpoint disabled by default был включён осознанно.'],
    training: 'Попробовать на учебном стенде: `training.dnp.chz_code_pool_sync`.',
  },
  'onec-sends-chz-code-pool-file': {
    solves: '1С уже сформировала полный пул кодов ЧЗ и отправляет его в OMH. OMH сохраняет файл в локальный архив, optional копирует его в SMB/laser directory и optional отправляет тот же пул во внешний API.',
    when: ['Коды уже готовы на стороне 1С.', 'Нужно сохранить файл без потери GS-разделителей.', 'Нужен журнал экспортов и retry optional-действий.', 'Нужна SMB/laser копия или внешний forward.'],
    before: ['Настройки CHZ Code Pool Workbench.', 'Local outbox directory на сервере OMH.', 'SMB share, если нужна копия для лазера.', 'REST operation для DnP/внешнего forward, если включён forward.'],
    diagram: ['1C', '  -> `/api/marking-code-pools/onec/export-file`', '  -> local outbox archive', '  -> optional SMB/laser copy', '  -> optional external forward', '  -> export journal'],
    inputTitle: 'JSON export request от 1С',
    inputLanguage: 'json',
    input: ['{', '  "source_system": "1C ERP",', '  "source_document_id": "AEAE-000137",', '  "source_document_name": "Заказ на эмиссию AEAE-000137",', '  "order_number": "260703/5442",', '  "full_codes_base64": ["MDEwNDY0NjE1MTY5NzE4NjIx..."],', '  "actions_override": {', '    "local_outbox": true,', '    "laser_file": false,', '    "external_forward": true', '  }', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/marking-code-pools/onec/export-file \\', '  -H "Content-Type: application/json" \\', '  -d @chz-pool-export.json'],
    pseudo1c: ['Соединение = Новый HTTPСоединение("omh-server", 8000);', 'Запрос = Новый HTTPЗапрос("/api/marking-code-pools/onec/export-file");', 'Запрос.Заголовки.Вставить("Content-Type", "application/json");', 'Запрос.УстановитьТелоИзСтроки(СтрокаJSON, КодировкаТекста.UTF8);', 'Ответ = Соединение.ОтправитьДляОбработки(Запрос);'],
    expected: ['{', '  "success": true,', '  "status": "local_file_saved",', '  "export_id": "export-uuid",', '  "file_name": "KM_260703-5442___2_pcs.txt",', '  "warnings": []', '}'],
    connections: ['Local directory profile для архива.', 'SMB profile для laser copy.', 'REST API operation для optional external forward.', 'Secrets Store для SMB/API credentials.'],
    operations: ['`save_local_outbox`: обязательное локальное сохранение.', '`copy_to_laser_smb`: optional SMB copy.', '`external_forward`: optional REST forward.', '`retry-forward` и `retry-laser-copy`: повтор optional-действий из журнала.'],
    contracts: ['Input contract: `order_number`, `full_codes_base64[]` или legacy `codes[]` + `gs_marker`.', 'Output contract: `success`, `status`, `export_id`, `file_name`, `warnings`.', 'Mapping: обычно не нужен, потому что workbench принимает готовый file payload.'],
    steps: ['Откройте `/marking-code-pools`.', 'Проверьте настройки локального архива.', 'При необходимости включите SMB/laser copy.', 'При необходимости выберите external forward operation.', 'Сделайте preview export.', 'Отправьте test payload из 1С или curl.', 'Откройте журнал экспортов.', 'Повторите optional-действие через retry, если оно упало.'],
    preview: ['Preview должен показать количество кодов, имя файла, selected actions и warnings.', 'Preview не должен писать файл.', 'Проверьте, что base64 декодируется без потери GS.'],
    test: ['Сначала `/preview` endpoint или UI preview.', 'Затем export с `actions_override` только на local outbox.', 'SMB и external forward включайте отдельно.'],
    timeline: ['Workbench journal заменяет обычный event Timeline.', '`local_outbox` показывает путь и имя файла.', '`laser_file` показывает SMB result.', '`external_forward` показывает status/body target API.'],
    artifacts: ['`export_file.txt`', '`export_metadata.json`', '`laser_copy.result.json`', '`external_forward.request.json`', '`external_forward.response.json`'],
    errors: ['`Duplicate code`: повтор в пуле.', '`Full marking code is not valid Base64`: 1С неверно закодировала полный код.', '`Cannot write export file`: нет прав на local outbox.', '`SMB host down`: share недоступна.', '`External forward rejected request`: target API вернул 4xx/5xx.'],
    next: ['Добавьте мониторинг журнала экспортов.', 'Перенесите raw tokens в Secrets Store.', 'Проверьте retry на тестовом export before production.'],
    training: 'Попробовать на учебном стенде: `training.chz.code_pool_file_export`.',
  },
  'wms-shipment-fact-to-onec': {
    solves: 'WMS отправляет факт отгрузки, а OMH приводит его к контракту 1С HTTP service, optional ищет заказ по OData и передаёт факт в 1С с полной диагностикой target response.',
    when: ['WMS является источником события.', '1С должна создать или обновить факт операции.', 'Нужно сохранить исходный WMS JSON и оригинальный ответ 1С.', 'Нужен optional OData lookup заказа перед writeback.'],
    before: ['Профиль `1C HTTP Service`.', 'Optional профиль `1C OData` для поиска заказа.', 'Контракт факта отгрузки в 1С.', 'Training WMS payload или реальный sample от WMS.'],
    diagram: ['WMS / API', '  -> OMH endpoint `/api/bus/in/wms-shipment-fact`', '  -> optional 1C OData order lookup', '  -> Mapping Center WMS fact -> 1C payload', '  -> 1C HTTP Service operation', '  -> response to WMS'],
    inputTitle: 'JSON request от WMS',
    inputLanguage: 'json',
    input: ['{', '  "operation": "shipment_fact",', '  "wms_shipment_id": "WMS-SHIP-123",', '  "order_number": "260666/6938",', '  "status": "shipped",', '  "warehouse_code": "MAIN",', '  "shipped_at": "2026-07-04T14:30:00",', '  "items": [', '    { "sku": "ABC-123", "qty": 10, "barcode": "04646151697384" }', '  ]', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/wms-shipment-fact \\', '  -H "Content-Type: application/json" \\', '  -d @wms-shipment-fact.json'],
    expected: ['{', '  "success": true,', '  "wms_shipment_id": "WMS-SHIP-123",', '  "order_number": "260666/6938",', '  "onec_response": { "status": "accepted" }', '}'],
    connections: ['`1C HTTP Service`: endpoint `/shipment-facts`.', '`1C OData`: optional lookup заказа.', '`Training 1C HTTP Service`: mock для обучения.'],
    operations: ['`find_order_by_number`: optional OData query.', '`onec_accept_wms_shipment_fact`: HTTP operation to 1C.', '`normalize_response`: response to WMS.'],
    contracts: ['Input contract: `wms_shipment_id`, `order_number`, `status`, `items[]`.', 'Data contract 1С: `payload.order_ref_key`, `payload.wms_shipment_id`, `payload.items[]`.', 'Mapping: `request.body.items -> payload.items` как array.'],
    steps: ['В Scenario Router выберите “WMS отправляет факт отгрузки в 1С”.', 'Откройте WMS -> 1C wizard.', 'Вставьте WMS JSON sample.', 'Настройте optional OData lookup заказа.', 'Выберите 1C HTTP Service operation.', 'Проверьте payload mapping.', 'Сохраните disabled integration.', 'Запустите saved test case.'],
    preview: ['Preview должен показать `onec_payload`.', '`items` должен остаться массивом.', 'Если lookup включён, `order.Ref_Key` должен быть доступен.'],
    test: ['Dry-run проверяет mapping и optional OData.', 'Real test вызывайте только training/staging HTTP service.', 'Для business error используйте sample с несуществующим order_number.'],
    timeline: ['`incoming.request`', '`odata.order.request/response` если lookup включён', '`payload_builder_result`', '`target.1c.request`', '`target.1c.response`', '`caller.response`'],
    artifacts: ['`incoming.request.json`', '`odata_query_response.json`', '`onec_payload.json`', '`outgoing_request.json`', '`incoming_response.json`'],
    errors: ['`В запросе WMS нет массива items`: WMS прислал другой contract.', '`ORDER_NOT_FOUND`: заказ не найден по OData.', '`1C_HTTP_500`: 1С вернула ошибку обработчика.', '`OBJECT_LOCKED`: документ заблокирован в 1С.', '`MAPPING_REQUIRED_FIELD_MISSING`: обязательное поле payload не собрано.'],
    next: ['Добавьте Operation Catalog preset для `/shipment-facts`.', 'Согласуйте retry policy с WMS, чтобы не задвоить факт.', 'Перед production enable прогоните негативный test с business error.'],
    training: 'Попробовать на учебном стенде: `training.wms.shipment_fact_to_onec`.',
  },
  'xml-raw-forwarding': {
    solves: 'OMH принимает XML и пересылает его в целевую 1С или внешний сервис без изменения тела. Сценарий нужен, когда byte/text-level изменение XML недопустимо для legacy обмена.',
    when: ['Target требует ровно тот XML, который прислал caller.', 'Не нужно собирать новый XML или менять namespace.', 'Нужно доказать, что XML не был изменён.', 'Нужны hash artifacts и оригинальный target response.'],
    before: ['Профиль `1C HTTP Service` или REST target для XML.', 'Sample XML от источника.', 'Решение, требовать ли valid XML.', 'Понимание Content-Type target-сервиса.'],
    diagram: ['1C / legacy system', '  -> OMH endpoint `/api/bus/in/onec-xml-raw-bridge`', '  -> raw XML policy + hash check', '  -> target 1C HTTP Service', '  -> target response to caller'],
    inputTitle: 'XML request',
    inputLanguage: 'xml',
    input: ['<Документ>', '  <Тип>УПД</Тип>', '  <Номер>123</Номер>', '  <ИНН>7707083893</ИНН>', '  <Дата>2026-07-04</Дата>', '</Документ>'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/onec-xml-raw-bridge \\', '  -H "Content-Type: application/xml; charset=utf-8" \\', '  --data-binary @document.xml'],
    pseudo1c: ['Соединение = Новый HTTPСоединение("omh-server", 8000);', 'Запрос = Новый HTTPЗапрос("/api/bus/in/onec-xml-raw-bridge");', 'Запрос.Заголовки.Вставить("Content-Type", "application/xml; charset=utf-8");', 'Запрос.УстановитьТелоИзСтроки(XMLСтрока, КодировкаТекста.UTF8);', 'Ответ = Соединение.ОтправитьДляОбработки(Запрос);'],
    expectedLanguage: 'xml',
    expected: ['<Response>', '  <Success>true</Success>', '  <Message>XML accepted</Message>', '</Response>'],
    connections: ['`1C HTTP Service`: принимающая 1С.', '`REST API`: внешний XML endpoint.', '`Training 1C HTTP Service`: mock receive XML.'],
    operations: ['`raw_xml_forward`: сохраняет тело как есть.', '`hash_check`: считает SHA256 before/after.', '`target_xml_post`: отправляет XML с нужным Content-Type.'],
    contracts: ['Input contract: raw XML body.', 'Data contract target: raw XML, без field mapping.', 'Mapping Center обычно не используется, чтобы не изменить XML.'],
    steps: ['Откройте XML Raw Bridge wizard.', 'Вставьте XML sample.', 'Выберите policy “Переслать XML без изменений”.', 'Включите hash verification.', 'Выберите target operation.', 'Настройте caller response: target response или fixed success.', 'Сохраните disabled integration.', 'Запустите saved test case.'],
    preview: ['Preview показывает original SHA256 и forwarded SHA256.', '`unchanged=true` обязателен для raw forwarding.', 'Проверьте Content-Type target request.'],
    test: ['Используйте `--data-binary`, чтобы curl не менял тело XML.', 'Сначала training target, затем staging 1С.', 'Проверьте hash artifacts.'],
    timeline: ['`incoming.request.xml`', '`raw_xml_original`', '`raw_xml_forwarded`', '`xml_hashes`', '`target.request`', '`target.response`'],
    artifacts: ['`raw_xml_original.xml`', '`raw_xml_forwarded.xml`', '`xml_hashes.json`', '`target_request.json`', '`target_response.json`'],
    errors: ['`XML_PARSE_FAILED`: XML невалиден, а validation включён.', '`XML_HASH_MISMATCH`: между input и forward появился transform.', '`TARGET_UNSUPPORTED_MEDIA_TYPE`: неверный Content-Type.', '`TARGET_HTTP_500`: принимающая 1С вернула ошибку.'],
    next: ['Если нужно извлечь поля из XML, используйте XML -> OData -> XML response.', 'Если нужна подпись/canonical XML, заведите отдельный production pattern.', 'Для production храните sample XML и hash evidence в тест-кейсе.'],
    training: 'Попробовать на учебном стенде: `training.onec.xml_raw_bridge`.',
  },
  'xml-input-odata-xml-response': {
    solves: 'Caller присылает XML с бизнес-ключом. OMH извлекает значения из XML, выполняет OData lookup в 1С и синхронно возвращает XML-ответ.',
    when: ['Источник или caller работает только с XML.', 'Нужно прочитать данные из 1С OData.', 'Caller ждёт синхронный XML response.', 'Нужно видеть XML extraction, OData request и rendered XML response в Timeline.'],
    before: ['Профиль `1C OData`.', 'Sample XML с реальными тегами.', 'XML paths для обязательных полей.', 'Response XML template.'],
    diagram: ['1C / external XML caller', '  -> OMH endpoint `/api/bus/in/xml-lookup-order`', '  -> XML extract', '  -> 1C OData order lookup', '  -> XML response builder', '  -> XML response to caller'],
    inputTitle: 'XML request',
    inputLanguage: 'xml',
    input: ['<Request>', '  <Operation>lookup_order</Operation>', '  <Number>260666/6938</Number>', '  <Format>xml</Format>', '</Request>'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/xml-lookup-order \\', '  -H "Content-Type: application/xml; charset=utf-8" \\', '  --data-binary @lookup-order.xml'],
    pseudo1c: ['Соединение = Новый HTTPСоединение("omh-server", 8000);', 'Запрос = Новый HTTPЗапрос("/api/bus/in/xml-lookup-order");', 'Запрос.Заголовки.Вставить("Content-Type", "application/xml; charset=utf-8");', 'Запрос.УстановитьТелоИзСтроки(XMLЗапрос, КодировкаТекста.UTF8);', 'Ответ = Соединение.ОтправитьДляОбработки(Запрос);'],
    expectedLanguage: 'xml',
    expected: ['<Response>', '  <Success>true</Success>', '  <Order>', '    <UUID>66666666-6666-6666-6666-666666666666</UUID>', '    <Number>260666/6938</Number>', '  </Order>', '</Response>'],
    connections: ['`1C OData`: поиск заказа.', '`Training OData ERP`: учебный lookup.', '`Inbound auth`: static token при production доступе.'],
    operations: ['`xml_extract`: извлечь `operation`, `order_number`, `format`.', '`odata_lookup_order`: OData query.', '`xml_response_builder`: собрать XML response.'],
    contracts: ['Input contract: raw XML + extracted variables.', 'Output contract: XML response with `Success`, `Order.UUID`, `Order.Number`.', 'Mapping: `order.Ref_Key -> /Response/Order/UUID`.'],
    steps: ['Откройте XML -> OData -> XML response wizard.', 'Вставьте XML sample.', 'Выберите XML paths `/Request/Operation` и `/Request/Number`.', 'Настройте OData query по extracted `order_number`.', 'Соберите XML response template.', 'Проверьте preview.', 'Сохраните disabled integration.', 'Запустите saved test case.'],
    preview: ['XML extract должен показать `order_number=260666/6938`.', 'Rendered OData filter должен использовать extracted variable.', 'Rendered XML должен быть well-formed.'],
    test: ['Curl с `--data-binary`.', 'Training example для успешного заказа.', 'Negative test: пустой `<Number/>` или неизвестный номер.'],
    timeline: ['`raw_xml_input`', '`xml_extracted_fields`', '`odata.order.request`', '`odata.order.response`', '`response_template`', '`rendered_response`'],
    artifacts: ['`raw_xml_input.xml`', '`xml_extracted_fields.json`', '`odata_query_request.json`', '`odata_query_response.json`', '`response_template.xml`', '`rendered_response.xml`'],
    errors: ['`XML_PARSE_FAILED`: XML невалиден.', '`XML_PATH_MISSING`: `/Request/Number` не найден.', '`ODATA_RESULT_EMPTY`: заказ не найден.', '`XML_RENDER_FAILED`: response template невалиден.'],
    next: ['Если XML нужно переслать без изменений, используйте XML Raw Bridge.', 'Если нужен JSON response, переключите Response Builder.', 'Добавьте troubleshooting ссылку для XML parse errors в проектную документацию.'],
    training: 'Попробовать на учебном стенде: `training.onec.xml_lookup_order_response`.',
  },
  'onec-print-labels': {
    solves: '1С отправляет JSON с labels[]. OMH выбирает принтер, строит ZPL для каждой строки, создаёт print job и возвращает normalized print status.',
    when: ['1С должна печатать этикетки через централизованный OMH endpoint.', 'Нужно видеть rendered ZPL и printer response.', 'Нужно безопасно делать dry-run/test print.', 'Принтеры должны быть описаны как reusable profiles.'],
    before: ['Printer profile в Connection Center.', 'ZPL template или базовый шаблон из wizard.', 'Sample JSON с `labels[]`.', 'Training Printer для учебного теста.'],
    diagram: ['1C', '  -> OMH endpoint `/api/bus/in/print-labels`', '  -> printer selection', '  -> labels[] validation', '  -> ZPL rendering', '  -> Printer connector', '  -> print status to caller'],
    inputTitle: 'JSON request от 1С',
    inputLanguage: 'json',
    input: ['{', '  "operation": "print_labels",', '  "printer": "LINE-1-ZEBRA",', '  "job_key": "ORDER-123",', '  "labels": [', '    {', '      "sequence_no": 1,', '      "sku": "ABC-123",', '      "title": "Плата ABC",', '      "code": "010464615169738421ABC",', '      "qty": 1', '    }', '  ]', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/bus/in/print-labels \\', '  -H "Content-Type: application/json" \\', '  -d @print-labels.json'],
    pseudo1c: ['Соединение = Новый HTTPСоединение("omh-server", 8000);', 'Запрос = Новый HTTPЗапрос("/api/bus/in/print-labels");', 'Запрос.Заголовки.Вставить("Content-Type", "application/json");', 'Запрос.УстановитьТелоИзСтроки(JSONЭтикетки, КодировкаТекста.UTF8);', 'Ответ = Соединение.ОтправитьДляОбработки(Запрос);'],
    expected: ['{', '  "success": true,', '  "print_job_id": "TRAIN-PRINT-001",', '  "labels_count": 1,', '  "printer": "LINE-1-ZEBRA",', '  "status": "sent"', '}'],
    connections: ['`Printer`: Zebra/raw TCP or Training Printer.', '`Training Printer`: safe mock.', '`Inbound auth`: static token for production.'],
    operations: ['`select_printer`: from request/fixed/rule.', '`validate_labels`: check labels array and required fields.', '`render_zpl`: render one/all labels.', '`send_print_job`: dry-run, test print or print all.'],
    contracts: ['Input contract: `printer`, `job_key`, `labels[].code`.', 'Output contract: `success`, `print_job_id`, `labels_count`, `printer`, `status`.', 'Mapping: `label.code`, `label.title`, `request.body.job_key` into ZPL template.'],
    steps: ['Откройте Request -> Printer wizard.', 'Вставьте JSON sample.', 'Выберите printer selection mode.', 'Проверьте labels[] path.', 'Настройте ZPL template.', 'Выберите print mode: dry-run/test print/print all.', 'Настройте response to caller.', 'Сохраните disabled integration и saved test case.'],
    preview: ['Preview показывает selected printer, first label variables и rendered ZPL.', 'Если printer не найден, исправьте profile или path.', 'Dry-run не отправляет ZPL на физический принтер.'],
    test: ['Dry-run всегда первый.', 'Test print только после подтверждения.', 'Не делайте replay, пока не ясно, получил ли принтер задание.'],
    timeline: ['`incoming_print_request`', '`selected_printer`', '`zpl_template`', '`rendered_zpl_first_label`', '`printer_request`', '`printer_response`'],
    artifacts: ['`incoming_print_request.json`', '`selected_printer.json`', '`zpl_template.zpl`', '`rendered_zpl_first_label.zpl`', '`printer_request.json`', '`printer_response.json`'],
    errors: ['`LABELS_ARRAY_MISSING`: нет `labels[]`.', '`LABEL_FIELD_MISSING`: нет `labels[0].code`.', '`PRINTER_NOT_FOUND`: profile/path не совпали.', '`PRINTER_OFFLINE`: TCP/сеть/принтер недоступны.', '`ZPL_RENDER_FAILED`: template использует неизвестное поле.'],
    next: ['Добавьте training test для offline printer.', 'Согласуйте duplicate guard, чтобы replay не печатал дубликаты.', 'Для production закрепите printer profiles и ZPL templates в change history.'],
    training: 'Попробовать на учебном стенде: `training.print.labels`.',
  },
  'poll-odata-send-target': {
    solves: 'OMH сам по расписанию читает новые или изменённые записи из 1С OData, собирает payload и отправляет его во внешний API/WMS, сохраняя cursor и run history.',
    when: ['1С не может или не должна сама отправлять POST.', 'Нужно регулярно отдавать изменения во внешний сервис.', 'Нужен cursor/watermark и контроль first run.', 'Нужно видеть run history без ручного входящего request.'],
    before: ['Профиль `1C OData`.', 'Профиль/operation target REST API.', 'Правило cursor: дата, last value или no cursor first run.', 'Training OData и WMS mock для обучения.'],
    diagram: ['OMH Scheduler', '  -> 1C OData query with cursor', '  -> Payload Builder', '  -> REST API/WMS target', '  -> cursor update', '  -> Polling run history'],
    inputTitle: 'Polling не имеет входящего HTTP request',
    inputLanguage: 'json',
    input: ['{', '  "manual_run": true,', '  "cursor": {', '    "last_success_at": "2026-01-01T00:00:00"', '  }', '}'],
    curl: ['curl -X POST http://omh-server:8000/api/polling-jobs/<job-id>/run-now \\', '  -H "Content-Type: application/json" \\', '  -d \'{"dry_run":true,"update_cursor":false}\''],
    expected: ['{', '  "success": true,', '  "rows_read": 3,', '  "target_sent": false,', '  "dry_run": true,', '  "cursor_updated": false', '}'],
    connections: ['`1C OData`: source query.', '`REST API`: target endpoint.', '`Training OData ERP` и `Training WMS API`: учебный path.'],
    operations: ['`poll_orders`: OData query with cursor.', '`build_target_payload`: array payload preserving `orders[]`.', '`send_orders_to_wms`: REST operation.', '`update_cursor`: after success only.'],
    contracts: ['Source contract: rows from OData query.', 'Target contract: `payload.orders[]`, `cursor_from`, `count`.', 'Mapping: `orders -> payload.orders` as array.'],
    steps: ['Откройте Scenario Router и выберите “OMH сам читает OData по расписанию”.', 'Откройте Poll OData -> Send Target wizard.', 'Настройте schedule и first run strategy.', 'Выберите OData connection/resource/filter/select.', 'Настройте payload.', 'Выберите target operation.', 'Запустите manual dry-run.', 'Сохраните job disabled or paused until production enable.'],
    preview: ['Preview показывает rendered filter с cursor.', 'Если first run strategy `no_cursor_filter`, проверьте `$top`.', '`orders` должен быть array в target payload.'],
    test: ['Manual dry-run без target send.', 'Manual real send на training/staging endpoint.', 'Cursor update включайте только после проверки target response.'],
    timeline: ['`polling.run.started`', '`odata.query.request`', '`odata.query.response`', '`payload_builder_result`', '`target.request/response`', '`cursor.update`'],
    artifacts: ['`polling_run.json`', '`odata_query_request.json`', '`odata_query_response.json`', '`target_payload.json`', '`target_response.json`', '`cursor_update.json`'],
    errors: ['`ODATA_AUTH_FAILED`: источник 1С недоступен.', '`EMPTY_RESULT`: не ошибка, если empty behavior = success.', '`CURSOR_RENDER_FAILED`: filter использует пустой cursor без first run strategy.', '`TARGET_HTTP_500`: cursor не обновляется.', '`TIMEOUT`: target API недоступен.'],
    next: ['Настройте alert на failed polling run.', 'Проверьте, что cursor обновляется только после success.', 'Перед production включите расписание и сохраните первый successful run как evidence.'],
    training: 'Попробовать на учебном стенде: `training.polling.odata_orders_to_wms`.',
  },
};

function section(title: string, lines: string[]) {
  return [`## ${title}`, ...lines, ''].join('\n');
}

function list(items: string[]) {
  return items.map((item) => `- ${item}`);
}

function numbered(items: string[]) {
  return items.map((item, index) => `${index + 1}. ${item}`);
}

function fence(language: string, lines: string[]) {
  return [`\`\`\`${language}`, ...lines, '\`\`\`'];
}

function renderTutorial(template: TutorialTemplate) {
  const resultLanguage = template.expectedLanguage ?? 'json';
  const lines = [
    '---',
    '',
    '<!-- OMH_PLATFORM_TUTORIAL_TEMPLATE_V1 -->',
    '',
    section(requiredTutorialHeadings[0], [template.solves]),
    section(requiredTutorialHeadings[1], list(template.when)),
    section(requiredTutorialHeadings[2], list(template.before)),
    section(requiredTutorialHeadings[3], fence('text', template.diagram)),
    section(requiredTutorialHeadings[4], [template.inputTitle, '', ...fence(template.inputLanguage, template.input), '', 'Curl пример:', '', ...fence('bash', template.curl), ...(template.pseudo1c ? ['', '1C псевдокод:', '', ...fence('1c', template.pseudo1c)] : []), '', 'Ожидаемый ответ:', '', ...fence(resultLanguage, template.expected)]),
    section(requiredTutorialHeadings[5], list(template.connections)),
    section(requiredTutorialHeadings[6], list(template.operations)),
    section(requiredTutorialHeadings[7], list(template.contracts)),
    section(requiredTutorialHeadings[8], numbered(template.steps)),
    section(requiredTutorialHeadings[9], list(template.preview)),
    section(requiredTutorialHeadings[10], list(template.test)),
    section(requiredTutorialHeadings[11], [...list(template.timeline), '', 'Artifacts:', ...list(template.artifacts)]),
    section(requiredTutorialHeadings[12], list(template.errors)),
    section(requiredTutorialHeadings[13], [...list(template.next), '', template.training]),
  ];
  return lines.join('\n').trim();
}

export function applyPlatformTutorialTemplate(sectionId: string, slug: string, markdown: string) {
  if (sectionId !== 'recipes') return markdown;
  const template = tutorials[slug];
  if (!template || markdown.includes('OMH_PLATFORM_TUTORIAL_TEMPLATE_V1')) return markdown;
  return `${markdown.trim()}\n\n${renderTutorial(template)}`;
}

export const platformTutorialSlugs = Object.keys(tutorials);
export const platformTutorialRequiredHeadings = requiredTutorialHeadings;
