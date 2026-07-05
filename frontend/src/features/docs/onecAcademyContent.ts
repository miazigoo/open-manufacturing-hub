import type { PageSeed } from './content';

function md(value: string) {
  return value.trim();
}

function mdLines(...value: string[]) {
  return md(value.join('\n'));
}

function page(sectionId: string, slug: string, title: string, description: string, order: number, markdown: string): PageSeed {
  return { packageId: 'onec', sectionId, slug, title, description, order, markdown };
}

export const goldenScenarioPayload = `{
  "inn": "7707083893",
  "product_code": "ABC-123",
  "pool_id": "POOL-001",
  "codes": [
    "010464615169738421ABC",
    "010464615169738421DEF"
  ]
}`;

export const goldenScenarioTargetJson = `{
  "pool_id": "POOL-001",
  "contractor_uuid": "contractor-ref-key",
  "contractor_name": "ООО Ромашка",
  "product_uuid": "product-ref-key",
  "product_name": "Плата ABC",
  "codes": [
    "010464615169738421ABC",
    "010464615169738421DEF"
  ],
  "source_system": "1C"
}`;

const goldenScenarioIntro = `Golden Scenario: 1C POST -> two OData lookups -> JSON -> external endpoint.

В каждом уроке мы держим один и тот же пример: 1C отправляет INN, product_code, pool_id и marking codes. OMH принимает запрос, ищет контрагента в 1C ERP OData по INN, ищет товар в 1C ERP или WMS OData по product_code, собирает целевой JSON и отправляет его во внутренний DNP API. Так пользователь не перескакивает между разными абстрактными примерами.`;

type LessonConfig = {
  slug: string;
  order: number;
  title: string;
  description: string;
  build: string;
  why: string;
  before: string[];
  steps: string[];
  example: string;
  expected: string[];
  mistakes: string[];
  checklist: string[];
  next?: string;
};

function lesson(config: LessonConfig): PageSeed {
  const nextLink = config.next ? /^\[([^\]]+)\]\(([^)]+)\)\.$/.exec(config.next) : null;
  const nextBlock = nextLink
    ? `::next-lesson{label="${nextLink[1]}" href="${nextLink[2]}"}`
    : (config.next ?? 'Курс завершен. Дальше используйте Practical Recipes и Troubleshooting для производственных кейсов.');
  return page('academy', config.slug, config.title, config.description, config.order, md(`
# ${config.title}

::lesson-page{label="Академия интеграции 1C"}

::concept-callout{title="Golden Scenario" body="${goldenScenarioIntro.replace(/"/g, '&quot;').replace(/\n/g, ' ')}"}

## Что вы настроите
${config.build}

## Зачем это нужно
${config.why}

## Что нужно заранее
${config.before.map((item) => `- ${item}`).join('\n')}

## Пошаговая настройка
${config.steps.map((item, index) => `${index + 1}. ${item}`).join('\n')}

## Пример значений
${config.example}

## Что должно получиться
::expected-result{items="${config.expected.join('|')}"}

## Проверьте себя
::checklist{id="${config.slug}" items="${config.checklist.join('|')}"}

## Частые ошибки
::common-mistakes{items="${config.mistakes.join('|')}"}

## Следующий урок
${nextBlock}
`));
}

const defaultBefore = [
  'Пакет 1C установлен и enabled в Plugin Store.',
  'Вы открыли веб-интерфейс OMH и можете перейти в OData Connections, OData Explorer, Integration Flows, Test Console и Event Timeline.',
  'Для OData уроков опубликован OData сервис 1C и известен URL вида http://server/base/odata/standard.odata.',
];

export const academyPackAPages: PageSeed[] = [
  page('academy', 'create-odata-connection', 'Создаём OData-подключение к 1С', 'Подробный урок: создать OData ERP connection, понять поля формы, secrets и healthcheck.', 21, mdLines(
    '# Создаём OData-подключение к 1С',
    '',
    '::lesson-page{label="Пакет уроков A · Основы OData"}',
    '',
    '## Что вы настроите',
    'Вы создадите OData Connection `OData ERP`. Это сохраненное подключение к конкретной базе 1C, через которое OMH будет читать контрагентов, товары и документы.',
    '',
    '## Зачем это нужно',
    'OData connection is a saved connection to a concrete 1C base.',
    '',
    'OData Connection — это не generic Connector. Generic Connector может описывать REST API, принтер или другой внешний сервис. OData Connection всегда отвечает на вопрос: **в какую базу 1C OMH идет за данными**. В Golden Scenario OMH выбирает `OData ERP`, ищет контрагента по ИНН, потом ищет товар по артикулу.',
    '',
    '## Что нужно заранее',
    '- Пакет 1C установлен и enabled.',
    '- Администратор 1C опубликовал OData: обычно URL заканчивается на `/odata/standard.odata`.',
    '- У вас есть пользователь 1C для обмена, например `exchange_user`.',
    '- Если это production, пароль уже создан в Secrets Store.',
    '',
    '## Где нажимать',
    '1. Откройте левое меню.',
    '2. Перейдите в `Data Tools` или прямо в `OData Connections`.',
    '3. Нажмите preset `OData ERP`, если он есть.',
    '4. Если preset не подходит, заполните поля вручную.',
    '5. Нажмите `Create connection`.',
    '6. В блоке `Saved OData connections` выберите созданное подключение.',
    '7. Нажмите `Test $metadata`.',
    '',
    '[SCREENSHOT: OData Connection creation form]',
    '',
    '## Таблица полей',
    '| Поле | Пример | Что означает | Где взять |',
    '| --- | --- | --- | --- |',
    '| Name | OData ERP | Человеческое имя подключения, которое потом видно в Explorer и Flow Builder | Вы выбираете сами |',
    '| Base URL | http://1c-server/erp/odata/standard.odata | Адрес публикации 1C OData | 1C admin или web server publication |',
    '| Username | exchange_user | Пользователь 1C, от имени которого OMH читает OData | 1C admin |',
    '| Password | secret | Пароль пользователя 1C или secret reference | Secrets Store / 1C admin |',
    '| Timeout | 20 | Сколько секунд ждать ответа 1C | 20 обычно достаточно для первого теста |',
    '| Verify SSL | false | Проверять HTTPS certificate | false для локального HTTP, true для нормального HTTPS |',
    '',
    '## Пример значений',
    '```json',
    '{',
    '  "name": "OData ERP",',
    '  "base_url": "http://1c-server/erp/odata/standard.odata",',
    '  "auth": {',
    '    "type": "basic",',
    '    "username": "exchange_user",',
    '    "password": {',
    '      "$secret": "secret_1c_erp_password"',
    '    }',
    '  },',
    '  "timeout_seconds": 20,',
    '  "verify_ssl": false',
    '}',
    '```',
    '',
    'Примеры имен, которые понятны пользователю:',
    '- `OData ERP` — рабочая ERP база.',
    '- `OData WMS` — база складской системы, если она опубликована через OData.',
    '- `OData УСП` — учебная или торговая база.',
    '',
    '## Secrets',
    'Не вводите настоящий production пароль в exported configs. Создайте secret, например `secret_1c_erp_password`, и в connection используйте ссылку на него. Так config можно перенести из stage в production без раскрытия пароля.',
    '',
    'Для локального учебного стенда можно временно ввести raw password, например `123`, но в описании connection прямо пометьте, что это test-only.',
    '',
    '## Что должно получиться',
    '::expected-result{items="В списке появилась connection OData ERP|Healthcheck/Test $metadata вернул OK или понятную ошибку 1C|Connection можно выбрать в OData Explorer|Пользователь понимает, что это подключение к конкретной базе 1C, а не generic connector"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-a-create-odata-connection" items="Открыл OData Connections|Заполнил Name|Заполнил Base URL с /odata/standard.odata|Указал username|Использовал secret для production password|Нажал Create connection|Нажал Test $metadata"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Wrong base URL: указан адрес web-клиента 1C вместо OData publication|Пропущен хвост /odata/standard.odata|OData в 1C не опубликована|Неверный user/password|Пользователь 1C не имеет прав читать справочники|Создали generic Connector и не понимают, почему его неудобно выбрать в OData Explorer"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Проверить OData в OData Explorer" href="/docs/onec/academy/test-odata-explorer"}',
  )),
  page('academy', 'test-odata-explorer', 'Проверяем OData-запрос в OData Explorer', 'Подробный урок: выбрать OData ERP, загрузить resources и выполнить первый безопасный query.', 31, mdLines(
    '# Проверяем OData-запрос в OData Explorer',
    '',
    '::lesson-page{label="Пакет уроков A · Основы OData"}',
    '',
    '## Что вы настроите',
    'Вы проверите, что OMH действительно может читать данные из 1C через созданную connection `OData ERP`.',
    '',
    '## Зачем это нужно',
    'Если простой запрос `Catalog_Контрагенты?$top=5` не работает в OData Explorer, не нужно строить pipeline. Сначала чините connection, публикацию OData, права пользователя или имя ресурса.',
    '',
    '## Что нужно заранее',
    '- Создана OData Connection `OData ERP`.',
    '- `Test $metadata` возвращает OK.',
    '- В 1C есть хотя бы несколько контрагентов, доступных пользователю `exchange_user`.',
    '',
    '## Пошаговая настройка',
    '1. Откройте `OData Explorer`.',
    '2. В поле `OData connection` выберите `OData ERP`.',
    '3. Нажмите или дождитесь `Load resources` / загрузки resources из metadata.',
    '4. В поле `Resource` выберите `Catalog_Контрагенты`.',
    '5. В поле `$top` введите `5`.',
    '6. На первый тест оставьте `$filter` пустым.',
    '7. В `$select` введите `Ref_Key,Description,ИНН`.',
    '8. Нажмите `Run query`.',
    '',
    '[SCREENSHOT: OData Explorer connector selector]',
    '[SCREENSHOT: OData Explorer resources list]',
    '',
    '## Пример запроса',
    '```text',
    'Catalog_Контрагенты?$top=5',
    '```',
    '',
    'Лучше сразу ограничить поля:',
    '',
    '```text',
    'Catalog_Контрагенты?$select=Ref_Key,Description,ИНН&$top=5',
    '```',
    '',
    '## Что означает каждое поле',
    '| Поле | Что ввести | Зачем нужно |',
    '| --- | --- | --- |',
    '| OData connection | OData ERP | OMH должен знать, из какой 1C базы читать данные |',
    '| Resource | Catalog_Контрагенты | Это техническое имя справочника в OData, не заголовок формы 1C |',
    '| $top | 5 | Безопасный лимит, чтобы не читать весь справочник |',
    '| $select | Ref_Key,Description,ИНН | Вернуть только поля, которые нужны для проверки и будущего lookup |',
    '',
    '## Что должно получиться',
    '::expected-result{items="В Query result видны несколько контрагентов|У каждой строки есть Ref_Key и Description|OMH показывает request и response без скрытого ручного кода|Пользователь понимает: если это работает, OMH может читать данные из 1C"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-a-test-odata-explorer" items="Открыл OData Explorer|Выбрал OData ERP|Загрузил resources|Выбрал Catalog_Контрагенты|Поставил $top=5|Нажал Run query|Увидел несколько контрагентов"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Выбрана не та OData connection, например WMS вместо ERP|Resource введен по памяти и не совпадает с metadata|$top пустой или слишком большой|Пользователь 1C видит metadata, но не имеет прав на сам справочник|Путают Query result с уже настроенным pipeline"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Найти контрагента по ИНН" href="/docs/onec/academy/find-contractor-by-inn"}',
  )),
  page('academy', 'find-contractor-by-inn', 'Ищем контрагента по ИНН', 'Подробный урок: найти контрагента по ИНН, понять Ref_Key и подготовить lookup для pipeline.', 41, mdLines(
    '# Ищем контрагента по ИНН',
    '',
    '::lesson-page{label="Пакет уроков A · Основы OData"}',
    '',
    '## Что вы настроите',
    'Вы выполните конкретный lookup: OMH берет ИНН `7707083893`, отправляет OData filter в `Catalog_Контрагенты` и получает `Ref_Key`, `Description`, `ИНН`.',
    '',
    '## Зачем это нужно',
    'В 1C человек видит контрагента по названию и ИНН, но внутренние операции часто требуют `Ref_Key`. `Ref_Key` — это UUID, которым 1C обычно идентифицирует объект внутри базы. Именно его часто нужно передавать в следующий OData запрос, HTTP-сервис 1C или внешний API.',
    '',
    '## Что нужно заранее',
    '- Запрос `Catalog_Контрагенты?$top=5` уже работает.',
    '- Вы знаете точное имя поля ИНН в вашей 1C publication. В типовом учебном примере это `ИНН`.',
    '- В базе есть контрагент с ИНН `7707083893` или вы заменили значение на реальный ИНН из вашей базы.',
    '',
    '## Пошаговая настройка',
    '1. Откройте `OData Explorer`.',
    '2. Выберите `OData ERP`.',
    '3. Resource: `Catalog_Контрагенты`.',
    '4. В filter builder укажите Поле: `ИНН`.',
    '5. Operator: `eq`.',
    '6. Value: `7707083893`.',
    '7. Нажмите `Apply to $filter` или введите filter руками.',
    "8. `$filter`: `ИНН eq '7707083893'`.",
    '9. `$top`: `1`.',
    '10. `$select`: `Ref_Key,Description,ИНН`.',
    '11. Нажмите `Run query`.',
    '12. Если результат правильный, создайте lookup template `Find contractor by INN`.',
    '',
    '[SCREENSHOT: OData query result with Ref_Key]',
    '',
    '## Пример значений',
    '```text',
    'Resource: Catalog_Контрагенты',
    "Filter: ИНН eq '7707083893'",
    'Top: 1',
    'Select: Ref_Key,Description,ИНН',
    '```',
    '',
    'Expected response:',
    '',
    '```json',
    '{',
    '  "Ref_Key": "b19c0e6e-0000-0000-0000-000000000001",',
    '  "Description": "ООО Ромашка",',
    '  "ИНН": "7707083893"',
    '}',
    '```',
    '',
    'Lookup template для pipeline:',
    '',
    '```json',
    '{',
    '  "name": "Find contractor by INN",',
    '  "resource": "Catalog_Контрагенты",',
    "  \"filter_template\": \"ИНН eq '{inn}'\",",
    '  "extract_json": {',
    '    "contractor_uuid": "Ref_Key",',
    '    "contractor_name": "Description",',
    '    "contractor_inn": "ИНН"',
    '  }',
    '}',
    '```',
    '',
    '## Ref_Key простыми словами',
    'Ref_Key — это внутренний UUID объекта 1C.',
    '`Ref_Key` — это внутренний UUID объекта 1C. Название `ООО Ромашка` удобно человеку, но интеграции часто должны работать со стабильным ключом. Если следующий шаг создает документ в 1C или отправляет данные в API, чаще всего ему нужен именно `Ref_Key`, а не только ИНН.',
    '',
    '## Что должно получиться',
    '::expected-result{items="Query result содержит одну строку контрагента|В строке есть Ref_Key, Description и ИНН|Вы понимаете, какой field mapping сохранить для pipeline|Если строка не найдена, ошибка считается понятной бизнес-проверкой, а не поломкой OMH"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-a-find-contractor-by-inn" items="Выбрал OData ERP|Указал Catalog_Контрагенты|Ввел filter по ИНН|Поставил $top=1|Указал $select|Увидел Ref_Key|Понял зачем Ref_Key нужен дальше"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="INN содержит пробелы или невидимые символы|Неверное имя поля: в вашей базе это может быть ИНН, INN или другое metadata name|Выбран wrong catalog или wrong OData base|Контрагент находится в другой 1C базе|OData user не имеет прав видеть справочник|Ищут по Description, хотя в Golden Scenario входной ключ — INN"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Создать входную точку для POST-запроса из 1С" href="/docs/onec/academy/lesson-04-create-inbound-endpoint-for-1c-post"}',
  )),
];

export const academyPackBPages: PageSeed[] = [
  page('academy', 'create-inbound-endpoint', 'Создаём входную точку для POST-запроса из 1С', 'Создать URL, куда 1C отправляет Golden Scenario payload.', 51, mdLines(
    '# Создаём входную точку для POST-запроса из 1С',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы создадите inbound endpoint `onec-pool-to-dnp`. Это URL в OMH, куда 1C отправляет POST request с `inn`, `product_code`, `pool_id` и `codes`.',
    '',
    '## Зачем это нужно',
    'Endpoint is the URL where 1C sends request. Без endpoint у 1C нет стабильного адреса, а у OMH нет понятного контракта: какой метод, какой body type, какой response mode и нужна ли защита token.',
    '',
    '## Что нужно заранее',
    '- Пакет 1C установлен и enabled.',
    '- Вы понимаете training payload из Start in 15 minutes.',
    '- Для production решено, нужен ли static token.',
    '- Если flow уже существует, откройте его в Integration Flow Builder.',
    '',
    '## Пошаговая настройка',
    '1. Откройте `Integration Flows`.',
    '2. Нажмите `Create flow` или откройте существующий Golden Scenario flow.',
    '3. В блоке inbound/source выберите type `1C POST` или `HTTP JSON endpoint`.',
    '4. Name: `1C pool to DNP`.',
    '5. Slug: `onec-pool-to-dnp`.',
    '6. Input mode: `JSON`.',
    '7. Response mode: `accepted_event`, если 1C должна быстро получить `event_id`, а обработка может идти через очередь.',
    '8. Auth: `static token` для production или `none` только для локального учебного стенда.',
    '9. Сохраните endpoint.',
    '10. Скопируйте полный URL для 1C разработчика.',
    '',
    '[SCREENSHOT: Flow Builder inbound endpoint form]',
    '[SCREENSHOT: Endpoint URL copy action]',
    '',
    '## Таблица полей',
    '| Поле | Пример | Что означает |',
    '| --- | --- | --- |',
    '| Name | 1C pool to DNP | Человеческое имя сценария в UI |',
    '| Slug | onec-pool-to-dnp | Часть URL после `/api/bus/in/` |',
    '| Input mode | JSON | Тип тела request, который 1C отправляет в OMH |',
    '| Response mode | accepted_event | 1C быстро получает event_id, а OMH обрабатывает дальше |',
    '| Auth | static token or none | Защита endpoint от чужих запросов |',
    '',
    '## Пример значений',
    '```text',
    'POST http://omh-server:8000/api/bus/in/onec-pool-to-dnp',
    'Content-Type: application/json',
    '```',
    '',
    'Expected accepted response:',
    '',
    '```json',
    '{',
    '  "accepted": true,',
    '  "event_id": "event-uuid",',
    '  "queue_item_id": "queue-item-uuid",',
    '  "timeline_url": "/events/event-uuid"',
    '}',
    '```',
    '',
    '## 1C pseudo-code',
    '```1c',
    'Соединение = Новый HTTPСоединение("omh-server", 8000);',
    'Запрос = Новый HTTPЗапрос("/api/bus/in/onec-pool-to-dnp");',
    'Запрос.Заголовки.Вставить("Content-Type", "application/json");',
    'Запрос.Заголовки.Вставить("X-OMH-Token", "training-token");',
    'Запрос.УстановитьТелоИзСтроки(СтрокаJSON, КодировкаТекста.UTF8);',
    'Ответ = Соединение.ОтправитьДляОбработки(Запрос);',
    'Если Ответ.КодСостояния >= 300 Тогда',
    '  ВызватьИсключение "OMH endpoint returned: " + Ответ.ПолучитьТелоКакСтроку();',
    'КонецЕсли;',
    '```',
    '',
    '## Что должно получиться',
    '::expected-result{items="Endpoint появился в списке inbound routes|URL заканчивается на /api/bus/in/onec-pool-to-dnp|Test Console может выбрать этот endpoint|При accepted_event response содержит event_id и timeline_url"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-create-inbound-endpoint" items="Создал endpoint|Указал slug onec-pool-to-dnp|Выбрал JSON input mode|Выбрал accepted_event|Понял token auth|Скопировал endpoint URL"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Путать endpoint slug и flow name|Выбрать XML input mode для JSON payload|Оставить auth none в production|Ждать business response от accepted_event|Не передать Content-Type application/json из 1C"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Прочитать значения из входящего запроса" href="/docs/onec/academy/read-request-fields"}',
  )),
  page('academy', 'read-request-fields', 'Читаем значения из входящего запроса', 'Прочитать inn, product_code, pool_id и codes из request.body.', 61, mdLines(
    '# Читаем значения из входящего запроса',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы добавите read-field шаги, чтобы flow получил named values: `inn`, `product_code`, `pool_id`, `codes`.',
    '',
    '## Зачем это нужно',
    'OData query и JSON Builder не должны каждый раз разбирать сырой request. Flow сначала читает значения из `request.body`, дает им понятные имена и только потом использует их в OData filters и target JSON.',
    '',
    '## Что нужно заранее',
    '- Endpoint `onec-pool-to-dnp` создан.',
    '- В Visual Flow Builder открыт sample request.',
    '- Вы знаете, что request body является JSON object.',
    '',
    '## Входящий JSON',
    '```json',
    '{',
    '  "inn": "7707083893",',
    '  "product_code": "ABC-123",',
    '  "pool_id": "POOL-001",',
    '  "codes": ["code1", "code2"]',
    '}',
    '```',
    '',
    '## Пошаговая настройка',
    '1. Откройте `Integration Flows`.',
    '2. Откройте builder для `1C pool to DNP`.',
    '3. В sample request вставьте JSON из этого урока.',
    '4. Добавьте step `Read field` или `Extract value`.',
    '5. Path: `request.body.inn`, save as: `inn`, required: yes.',
    '6. Добавьте второй read step: `request.body.product_code`, save as: `product_code`, required: yes.',
    '7. Добавьте третий read step: `request.body.pool_id`, save as: `pool_id`, required: yes.',
    '8. Добавьте четвертый read step: `request.body.codes`, save as: `codes`, required: yes.',
    '9. Нажмите Preview и проверьте variables.',
    '',
    '[SCREENSHOT: Flow Builder read request fields]',
    '[SCREENSHOT: Preview variables after read fields]',
    '',
    '## Таблица сопоставления полей',
    '| Value | Path | Example |',
    '| --- | --- | --- |',
    '| INN | request.body.inn | 7707083893 |',
    '| Product code | request.body.product_code | ABC-123 |',
    '| Pool ID | request.body.pool_id | POOL-001 |',
    '| Codes | request.body.codes | ["code1","code2"] |',
    '',
    '## Переменные',
    '```text',
    'inn = request.body.inn',
    'product_code = request.body.product_code',
    'pool_id = request.body.pool_id',
    'codes = request.body.codes',
    '```',
    '',
    '## Что должно получиться',
    '::expected-result{items="Preview показывает inn=7707083893|Preview показывает product_code=ABC-123|codes остается массивом, а не строкой|Следующие OData steps могут использовать эти values"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-read-request-fields" items="Вставил sample JSON|Добавил inn path|Добавил product_code path|Добавил pool_id path|Добавил codes path|Проверил Preview variables"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Писать inn вместо request.body.inn|Сохранить product_code как product|Сделать codes строкой вместо array|Не включить required и получить пустой OData filter|Использовать старый sample request без pool_id"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Добавить первый OData-запрос" href="/docs/onec/academy/first-odata-query-contractor"}',
  )),
  page('academy', 'first-odata-query-contractor', 'Первая выборка OData: контрагент по ИНН', 'Настроить первый OData Query step и сохранить результат как contractor.', 71, mdLines(
    '# Первая выборка OData: контрагент по ИНН',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы добавите OData query #1: OMH берет `request.body.inn`, ищет контрагента в `Catalog_Контрагенты` и сохраняет найденную строку как `contractor`.',
    '',
    '## Зачем это нужно',
    '`Save result as` превращает ответ OData в named variable. После этого JSON Builder сможет взять `contractor.Ref_Key` и `contractor.Description`, не обращаясь снова к raw OData response.',
    '',
    '## Что нужно заранее',
    '- Создана OData Connection `OData ERP`.',
    '- В OData Explorer работает query contractor by INN.',
    '- В flow уже прочитан `inn` из `request.body.inn`.',
    '',
    '## Настройка шага',
    '```text',
    'Step type: OData Query',
    'OData connection: OData ERP',
    'Resource: Catalog_Контрагенты',
    'Filter:',
    '  Поле: ИНН',
    '  Operator: equals',
    '  Value source: request.body.inn',
    'Top: 1',
    'Save result as: contractor',
    'Required: yes',
    '```',
    '',
    '## Пошаговая настройка',
    '1. В Flow Builder нажмите `Add step`.',
    '2. Step type: `OData Query`.',
    '3. OData connection: `OData ERP`.',
    '4. Resource: `Catalog_Контрагенты`.',
    '5. Filter field: `ИНН`.',
    '6. Operator: `equals` / `eq`.',
    '7. Value source: `request.body.inn` или variable `inn`, если предыдущий read step сохранил variable.',
    '8. `$select`: `Ref_Key,Description,ИНН`.',
    '9. Top: `1`.',
    '10. Save result as: `contractor`.',
    '11. Required: `yes`.',
    '12. Нажмите Preview.',
    '',
    '[SCREENSHOT: Flow Builder first OData contractor query]',
    '[SCREENSHOT: Contractor OData preview result]',
    '',
    '## Итоговый OData-запрос',
    '```text',
    "Catalog_Контрагенты?$filter=ИНН eq '7707083893'&$top=1",
    '```',
    '',
    '## Ожидаемая переменная',
    '```json',
    '{',
    '  "contractor": {',
    '    "Ref_Key": "contractor-uuid",',
    '    "Description": "ООО Ромашка",',
    '    "ИНН": "7707083893"',
    '  }',
    '}',
    '```',
    '',
    '## Объяснение по полям',
    '| Поле | Значение | Почему важно |',
    '| --- | --- | --- |',
    '| OData connection | OData ERP | Выбирает базу 1C, где лежит справочник контрагентов |',
    '| Resource | Catalog_Контрагенты | Техническое имя справочника из metadata |',
    '| Поле | ИНН | Поле, по которому ищем контрагента |',
    '| Value source | request.body.inn | Берем ИНН из входного запроса 1C |',
    '| Top | 1 | Golden Scenario ожидает одного контрагента |',
    '| Save result as | contractor | Имя variable для следующих steps |',
    '| Required | yes | Без контрагента нельзя строить корректный target JSON |',
    '',
    '## Что должно получиться',
    '::expected-result{items="Preview показывает contractor.Ref_Key|Timeline later сохранит odata_query contractor|Если контрагент не найден, flow остановится понятной business error|JSON Builder сможет использовать contractor.Ref_Key"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-first-odata-query-contractor" items="Выбрал OData Query|Выбрал OData ERP|Указал Catalog_Контрагенты|Настроил filter by ИНН|Top=1|Save result as contractor|Required=yes|Preview показывает contractor"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Save result as пустой или назван customer, а JSON Builder ожидает contractor|Required выключен и target JSON получает null|Value source указан как product_code|$select не содержит Ref_Key|Не проверили этот filter в OData Explorer"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Добавить второй OData-запрос" href="/docs/onec/academy/second-odata-query-product"}',
  )),
  page('academy', 'second-odata-query-product', 'Вторая выборка OData: товар по артикулу', 'Настроить второй OData Query step и сохранить результат как product.', 81, mdLines(
    '# Вторая выборка OData: товар по артикулу',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы добавите OData query #2: OMH берет `request.body.product_code`, ищет товар в `Catalog_Номенклатура` и сохраняет найденную строку как `product`.',
    '',
    '## Зачем это нужно',
    'Second OData connection can be different. Например, contractor может жить в ERP, а product — в WMS или УСП. Поэтому второй OData step должен явно показывать, какую базу он использует.',
    '',
    '## Что нужно заранее',
    '- Первый OData query сохраняет `contractor`.',
    '- В flow уже есть `product_code`.',
    '- В OData Explorer проверен resource номенклатуры и field `Артикул`.',
    '',
    '## Настройка шага',
    '```text',
    'Step type: OData Query',
    'OData connection: OData ERP or OData WMS',
    'Resource: Catalog_Номенклатура',
    'Filter:',
    '  Поле: Артикул',
    '  Operator: equals',
    '  Value source: request.body.product_code',
    'Top: 1',
    'Save result as: product',
    'Required: yes',
    '```',
    '',
    '## Пошаговая настройка',
    '1. Нажмите `Add step` после contractor query.',
    '2. Step type: `OData Query`.',
    '3. OData connection: `OData ERP` или `OData WMS`, если номенклатура живет в другой базе.',
    '4. Resource: `Catalog_Номенклатура`.',
    '5. Filter field: `Артикул`.',
    '6. Operator: `equals` / `eq`.',
    '7. Value source: `request.body.product_code` или variable `product_code`.',
    '8. `$select`: `Ref_Key,Description,Артикул`.',
    '9. Top: `1`.',
    '10. Save result as: `product`.',
    '11. Required: `yes`.',
    '12. Нажмите Preview и убедитесь, что теперь есть две variables: `contractor` и `product`.',
    '',
    '[SCREENSHOT: Flow Builder second OData product query]',
    '[SCREENSHOT: Preview with contractor and product variables]',
    '',
    '## Ожидаемая переменная',
    '```json',
    '{',
    '  "product": {',
    '    "Ref_Key": "product-uuid",',
    '    "Description": "Плата ABC",',
    '    "Артикул": "ABC-123"',
    '  }',
    '}',
    '```',
    '',
    '## Объяснение по полям',
    '| Поле | Значение | Почему важно |',
    '| --- | --- | --- |',
    '| OData connection | OData ERP or OData WMS | Product может быть в другой базе, не там же где contractor |',
    '| Resource | Catalog_Номенклатура | Technical OData resource для товаров |',
    '| Поле | Артикул | Поле для поиска по product_code |',
    '| Value source | request.body.product_code | Берем article из входного request 1C |',
    '| Save result as | product | Имя variable для JSON Builder |',
    '| Required | yes | Без товара target API получит неполный payload |',
    '',
    '## Что должно получиться',
    '::expected-result{items="Preview показывает product.Ref_Key|В preview одновременно есть contractor и product|Timeline later сохранит odata_query product|JSON Builder сможет использовать product.Ref_Key и product.Description"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-second-odata-query-product" items="Добавил второй OData Query|Выбрал правильную OData connection|Указал Catalog_Номенклатура|Настроил filter by Артикул|Save result as product|Required=yes|Preview показывает product"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Случайно сохранить второй результат как contractor и перезаписать первый lookup|Искать product в ERP, хотя он лежит в WMS|Использовать field Code вместо Артикул без проверки metadata|Не включить Required|Не ограничить $select"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Собрать целевой JSON" href="/docs/onec/academy/build-target-json"}',
  )),
  page('academy', 'build-target-json', 'Собираем целевой JSON', 'Собрать target_payload из request fields, contractor и product.', 91, mdLines(
    '# Собираем целевой JSON',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы соберете `target_payload` для DNP API. В нем `pool_id` и `codes` приходят из 1C request, contractor fields приходят из первого OData query, product fields — из второго OData query.',
    '',
    '## Зачем это нужно',
    'JSON Builder фиксирует contract внешнего API. Он не должен отправлять наружу весь raw request или весь raw OData response. Он должен собрать ровно те поля, которые target API ожидает.',
    '',
    '## Что нужно заранее',
    '- Есть variables `contractor` и `product`.',
    '- Есть request fields `pool_id` и `codes`.',
    '- Известна схема target API.',
    '',
    '## Таблица сопоставления полей',
    '| Target field | Source |',
    '| --- | --- |',
    '| pool_id | request.body.pool_id |',
    '| contractor_uuid | contractor.Ref_Key |',
    '| contractor_name | contractor.Description |',
    '| product_uuid | product.Ref_Key |',
    '| product_name | product.Description |',
    '| codes | request.body.codes |',
    '| source_system | constant "1C" |',
    '',
    '## Пошаговая настройка',
    '1. Нажмите `Add step` после product query.',
    '2. Step type: `Build JSON` или `JSON Builder`.',
    '3. Save result as: `target_payload`.',
    '4. Добавьте field `pool_id` и source `request.body.pool_id`.',
    '5. Добавьте field `contractor_uuid` и source `contractor.Ref_Key`.',
    '6. Добавьте field `contractor_name` и source `contractor.Description`.',
    '7. Добавьте field `product_uuid` и source `product.Ref_Key`.',
    '8. Добавьте field `product_name` и source `product.Description`.',
    '9. Добавьте field `codes` и source `request.body.codes`. Не превращайте array в строку.',
    '10. Добавьте constant `source_system` со значением `1C`.',
    '11. Нажмите Preview.',
    '',
    '[SCREENSHOT: JSON Builder field mapping table]',
    '[SCREENSHOT: Target JSON preview]',
    '',
    '## Итоговый JSON',
    '```json',
    '{',
    '  "pool_id": "POOL-001",',
    '  "contractor_uuid": "contractor-uuid",',
    '  "contractor_name": "ООО Ромашка",',
    '  "product_uuid": "product-uuid",',
    '  "product_name": "Плата ABC",',
    '  "codes": ["code1", "code2"],',
    '  "source_system": "1C"',
    '}',
    '```',
    '',
    '## Константы, массивы и отсутствующие переменные',
    '- Constant — значение, которое не берется из request или OData. Например `source_system = "1C"`.',
    '- Array — массив должен остаться массивом. `codes` нельзя склеивать в строку `code1,code2`, если target API ожидает JSON array.',
    '- Missing variable — если `contractor.Ref_Key` не найден, Preview должен показать ошибку до отправки в target API.',
    '- Preview — обязательный шаг перед Send. Он показывает target JSON без реального вызова target API.',
    '',
    '## Что должно получиться',
    '::expected-result{items="Preview показывает target_payload|codes остается JSON array|source_system равен 1C|Если contractor/product missing, Preview показывает ошибку до target call"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-build-target-json" items="Добавил Build JSON step|Save result as target_payload|Сопоставил contractor fields|Сопоставил product fields|Передал codes как array|Добавил constant source_system|Проверил Preview"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Отправить весь contractor object вместо contractor_uuid|Потерять codes array при ручной строковой сборке|Использовать product.uuid, хотя OData вернул Ref_Key|Не проверить Preview|Не описать target contract для владельца API"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Отправить во внешний API" href="/docs/onec/academy/send-to-external-api"}',
  )),
  page('academy', 'send-to-external-api', 'Отправляем JSON во внешний API', 'Отправить target_payload во внешний DNP/API endpoint.', 101, mdLines(
    '# Отправляем JSON во внешний API',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы добавите target step: OMH отправляет `target_payload` методом POST во внешний сервис `DNP Service`.',
    '',
    '## Зачем это нужно',
    'Flow должен не только собрать JSON, но и отправить его контролируемо: с base URL, headers, token secret, timeout, target.request artifact и target.response artifact.',
    '',
    '## Что нужно заранее',
    '- Создан REST connector или target connector `DNP Service`.',
    '- Target API path известен: `/api/marking/pools`.',
    '- Secret для token создан, если API требует Authorization.',
    '- `target_payload` проходит Preview.',
    '',
    '## Настройка target',
    '```text',
    'Connector: DNP Service',
    'Method: POST',
    'Path: /api/marking/pools',
    'Body: target_payload',
    '```',
    '',
    '## Пошаговая настройка',
    '1. Нажмите `Add step` после Build JSON.',
    '2. Step type: `Call endpoint`, `REST call` или `Send to external API`.',
    '3. Connector: `DNP Service`.',
    '4. Method: `POST`.',
    '5. Path: `/api/marking/pools`.',
    '6. Headers: `Content-Type: application/json`.',
    '7. Authorization: secret reference, например `$secret:dnp.api.token`, если target API защищен.',
    '8. Body source: `target_payload`.',
    '9. Timeout: `10` или `20` seconds для первого теста.',
    '10. Save artifacts: `target.request` и `target.response`.',
    '11. Нажмите Preview, затем сохраните draft/publish.',
    '',
    '[SCREENSHOT: Target API connector selection]',
    '[SCREENSHOT: Call endpoint step settings]',
    '',
    '## Объяснение полей connector',
    '| Поле | Пример | Что означает |',
    '| --- | --- | --- |',
    '| Base URL | http://dnp.local | Корневой адрес target API |',
    '| Headers | Content-Type: application/json | Что target API ожидает получить |',
    '| Token secret | $secret:dnp.api.token | Секретный токен, не raw value в config |',
    '| Timeout | 20 | Сколько ждать target API |',
    '',
    '## Исходящий запрос',
    '```text',
    'POST http://dnp.local/api/marking/pools',
    'Content-Type: application/json',
    '```',
    '',
    'Body:',
    '',
    '```json',
    '{',
    '  "pool_id": "POOL-001",',
    '  "contractor_uuid": "contractor-uuid",',
    '  "product_uuid": "product-uuid",',
    '  "codes": ["code1", "code2"]',
    '}',
    '```',
    '',
    '## Что должно получиться',
    '::expected-result{items="Flow показывает target step after build_json|target.request artifact содержит POST /api/marking/pools|target.response artifact сохраняет status и body|Ошибки target API видны без потери оригинального текста"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-send-to-external-api" items="Создал DNP Service connector|Выбрал POST|Указал path /api/marking/pools|Body source target_payload|Настроил token secret|Настроил timeout|Включил request/response artifacts"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Хранить target token raw в flow config|Отправлять request.body вместо target_payload|Не указывать Content-Type application/json|Слишком длинный sync timeout для 1C пользователя|Не сохранять target.response artifact"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Настроить полный обмен click-by-click" href="/docs/onec/academy/full-flow-click-by-click"}',
  )),
  page('academy', 'full-flow-click-by-click', 'Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint', 'Подробный click-by-click tutorial: 1C POST, два OData lookup, JSON Builder, Call Endpoint, Dry Run, Test Console, Timeline и artifacts.', 106, mdLines(
    '# Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder · Полная ручная настройка"}',
    '',
    'Эта страница написана как рабочая инструкция для человека, который впервые открывает OMH. Не нужно заранее знать архитектуру платформы: идите сверху вниз, после каждого крупного шага проверяйте ожидаемый результат и только потом переходите дальше.',
    '',
    '::open-page{route="/onec-cockpit" label="Открыть 1C Cockpit"}',
    '::open-page{route="/integration-flows" label="Открыть Flow Builder"}',
    '::open-page{route="/test-console" label="Открыть Test Console"}',
    '',
    '## 1. Что мы собираем',
    '1С отправит в OMH ИНН, код товара, номер пула и коды маркировки.',
    'OMH найдёт контрагента в OData ERP.',
    'OMH найдёт товар в OData ERP/WMS.',
    'OMH соберёт новый JSON и отправит его во внешний DNP API.',
    '',
    'Итоговая схема:',
    '',
    '```text',
    '1C POST /api/bus/in/onec-pool-to-dnp',
    '  -> receive request',
    '  -> get_contractor: OData ERP / Catalog_Контрагенты / ИНН',
    '  -> get_product: OData ERP or OData WMS / Catalog_Номенклатура / Артикул',
    '  -> build_target_payload: JSON Builder',
    '  -> send_to_dnp: POST /api/marking/pools',
    '  -> handle_response',
    '```',
    '',
    'Что должно произойти после этого раздела: пользователь понимает не только "что нажать", но и зачем в flow появляются named variables `contractor`, `product` и `target_payload`.',
    '',
    '## 2. Source JSON от 1С',
    'Именно такой JSON будет отправлять 1С в OMH:',
    '',
    '```json',
    '{',
    '  "inn": "7707083893",',
    '  "product_code": "ABC-123",',
    '  "pool_id": "POOL-001",',
    '  "codes": [',
    '    "010464615169738421ABC",',
    '    "010464615169738421DEF"',
    '  ]',
    '}',
    '```',
    '',
    'Пояснение полей:',
    '',
    '| Поле | Что означает | Где используется |',
    '| --- | --- | --- |',
    '| `inn` | ИНН контрагента из 1С | Фильтр первого OData query |',
    '| `product_code` | Код/артикул товара | Фильтр второго OData query |',
    '| `pool_id` | Номер пула маркировки | Поле в итоговом JSON |',
    '| `codes` | Массив кодов маркировки | Передается в DNP API без преобразования в строку |',
    '',
    'Что должно произойти после этого шага: вы заранее знаете входной контракт и не настраиваете flow на абстрактных полях.',
    '',
    '## 3. Создаём endpoint',
    'Endpoint — это входной URL в OMH, куда 1С будет делать POST. В этом сценарии endpoint называется `onec-pool-to-dnp`.',
    '',
    'Пошагово:',
    '',
    '1. Open `1C Cockpit`.',
    '2. Click `Create Integration`.',
    '3. Choose `1C sends JSON to external API`.',
    '4. Endpoint slug: `onec-pool-to-dnp`.',
    '5. Input mode: `JSON`.',
    '6. Response mode: `accepted_event`.',
    '7. Save.',
    '',
    '[SCREENSHOT: 1C Cockpit create integration wizard]',
    '[SCREENSHOT: Flow Builder inbound endpoint with onec-pool-to-dnp slug]',
    '',
    'Каждое поле формы:',
    '',
    '| UI field | Что вводить | Почему это важно |',
    '| --- | --- | --- |',
    '| Integration type | `1C sends JSON to external API` | OMH подготовит flow под inbound JSON и target HTTP call |',
    '| Endpoint slug | `onec-pool-to-dnp` | Это стабильная часть URL, которую получит 1С-разработчик |',
    '| Input mode | `JSON` | OMH будет читать `request.body.inn`, а не XML/text |',
    '| Response mode | `accepted_event` | 1С быстро получает `event_id`, а сам обмен виден в Timeline |',
    '| Auth | static token для production или none для учебного стенда | Защищает endpoint от случайных POST |',
    '',
    'Endpoint URL:',
    '',
    '```text',
    'POST http://omh-server:8000/api/bus/in/onec-pool-to-dnp',
    '```',
    '',
    'Что должно произойти после создания endpoint: в Test Console можно выбрать `onec-pool-to-dnp`, а в Flow Builder появился inbound/source block с JSON input.',
    '',
    '## 4. Добавляем первый OData block: get_contractor',
    'Первый OData block ищет контрагента по ИНН. Он должен вернуть хотя бы `Ref_Key` и `Description`, потому что эти поля попадут в target JSON.',
    '',
    'Пошагово:',
    '',
    '1. Open `Flow Builder`.',
    '2. Click `Add Step`.',
    '3. Select `OData Query`.',
    '4. Set step name: `get_contractor`.',
    '5. Select OData connection: `OData ERP`.',
    '6. Resource: `Catalog_Контрагенты`.',
    '7. Filter field: `ИНН`.',
    '8. Operator: `equals`.',
    '9. Value source: `request.body.inn`.',
    '10. `$select`: `Ref_Key,Description,ИНН`.',
    '11. Top: `1`.',
    '12. Save result as: `contractor`.',
    '13. Required: `yes`.',
    '14. Click `Preview`.',
    '',
    '[SCREENSHOT: Click Add Step and choose OData Query]',
    '[SCREENSHOT: get_contractor OData block settings]',
    '',
    'Что означает каждое поле:',
    '',
    '| UI field | Значение | Объяснение |',
    '| --- | --- | --- |',
    '| Step name | `get_contractor` | Имя шага в Timeline, по нему потом понятно где ошибка |',
    '| OData connection | `OData ERP` | Конкретная база 1С, где лежит справочник контрагентов |',
    '| Resource | `Catalog_Контрагенты` | Техническое имя справочника из `$metadata` |',
    '| Filter field | `ИНН` | Поле 1С, по которому ищем |',
    '| Operator | `equals` / `eq` | Точное совпадение ИНН |',
    '| Value source | `request.body.inn` | OMH берет значение из входного JSON от 1С |',
    '| `$select` | `Ref_Key,Description,ИНН` | Возвращаем только нужные поля, не весь объект |',
    '| Top | `1` | Нам нужен один найденный контрагент |',
    '| Save result as | `contractor` | Следующие шаги будут читать `contractor.Ref_Key` |',
    '| Required | `yes` | Если контрагент не найден, flow должен остановиться понятной ошибкой |',
    '',
    'OData request preview должен выглядеть примерно так:',
    '',
    '```text',
    "Catalog_Контрагенты?$filter=ИНН eq '7707083893'&$select=Ref_Key,Description,ИНН&$top=1",
    '```',
    '',
    'Что должно произойти после Preview: вы видите объект `contractor`, внутри есть `contractor.Ref_Key`, `contractor.Description` и `contractor.ИНН`.',
    '',
    '## 5. Добавляем второй OData block: get_product',
    'Второй OData block ищет товар по `product_code`. Connection может быть той же `OData ERP`, а может быть `OData WMS`, если номенклатура хранится в другой базе.',
    '',
    'Пошагово:',
    '',
    '1. Click `Add Step` после `get_contractor`.',
    '2. Select `OData Query`.',
    '3. Step name: `get_product`.',
    '4. Connection: `OData ERP` or `OData WMS`.',
    '5. Resource: `Catalog_Номенклатура`.',
    '6. Filter field: `Артикул`.',
    '7. Operator: `equals`.',
    '8. Value source: `request.body.product_code`.',
    '9. `$select`: `Ref_Key,Description,Артикул`.',
    '10. Top: `1`.',
    '11. Save as: `product`.',
    '12. Required: `yes`.',
    '13. Click `Preview`.',
    '',
    '[SCREENSHOT: get_product OData block settings]',
    '[SCREENSHOT: Preview variables contractor and product]',
    '',
    'Каждое поле:',
    '',
    '| UI field | Значение | Объяснение |',
    '| --- | --- | --- |',
    '| Step name | `get_product` | Отдельный шаг, не перезаписывающий `contractor` |',
    '| Connection | `OData ERP` or `OData WMS` | Выбирайте базу, где реально есть номенклатура |',
    '| Resource | `Catalog_Номенклатура` | Техническое имя из OData Explorer |',
    '| Field | `Артикул` | Поле товара, соответствующее `product_code` |',
    '| Value source | `request.body.product_code` | Значение приходит из исходного POST |',
    '| Save as | `product` | JSON Builder будет читать `product.Ref_Key` |',
    '| Required | `yes` | Без товара нельзя отправлять корректный DNP request |',
    '',
    'OData request preview:',
    '',
    '```text',
    "Catalog_Номенклатура?$filter=Артикул eq 'ABC-123'&$select=Ref_Key,Description,Артикул&$top=1",
    '```',
    '',
    'Что должно произойти после Preview: в variables одновременно есть `contractor` и `product`. Если второй step сохранился как `contractor`, это ошибка: вы перезапишете результат первого поиска.',
    '',
    '## 6. Добавляем JSON Builder block',
    'JSON Builder собирает body для внешнего API. Он не должен отправлять наружу весь request 1C и весь OData response. Он берет только нужные поля.',
    '',
    'Пошагово:',
    '',
    '1. Click `Add Step` после `get_product`.',
    '2. Select `Build JSON`.',
    '3. Step name: `build_target_payload`.',
    '4. Save as: `target_payload`.',
    '5. Add field `pool_id`, source `request.body.pool_id`.',
    '6. Add field `contractor_uuid`, source `contractor.Ref_Key`.',
    '7. Add field `contractor_name`, source `contractor.Description`.',
    '8. Add field `product_uuid`, source `product.Ref_Key`.',
    '9. Add field `product_name`, source `product.Description`.',
    '10. Add field `codes`, source `request.body.codes`.',
    '11. Add field `source_system`, source type `constant`, value `"1C"`.',
    '12. Click `Preview`.',
    '',
    '[SCREENSHOT: JSON Builder full target payload mapping]',
    '',
    '| Target field | Source |',
    '| --- | --- |',
    '| `pool_id` | `request.body.pool_id` |',
    '| `contractor_uuid` | `contractor.Ref_Key` |',
    '| `contractor_name` | `contractor.Description` |',
    '| `product_uuid` | `product.Ref_Key` |',
    '| `product_name` | `product.Description` |',
    '| `codes` | `request.body.codes` |',
    '| `source_system` | constant `"1C"` |',
    '',
    'Target JSON preview:',
    '',
    '```json',
    '{',
    '  "pool_id": "POOL-001",',
    '  "contractor_uuid": "b19c0e6e-0000-0000-0000-000000000001",',
    '  "contractor_name": "ООО Ромашка",',
    '  "product_uuid": "a54c0e6e-0000-0000-0000-000000000002",',
    '  "product_name": "Плата ABC",',
    '  "codes": [',
    '    "010464615169738421ABC",',
    '    "010464615169738421DEF"',
    '  ],',
    '  "source_system": "1C"',
    '}',
    '```',
    '',
    'Что должно произойти после Preview: `codes` остался массивом, `contractor_uuid` взят из `contractor.Ref_Key`, `product_uuid` взят из `product.Ref_Key`, а лишние поля OData не попали в target payload.',
    '',
    '## 7. Добавляем Call Endpoint block',
    'Последний рабочий block отправляет `target_payload` во внешний DNP сервис.',
    '',
    'Пошагово:',
    '',
    '1. Click `Add Step` после `build_target_payload`.',
    '2. Select `Call Endpoint`.',
    '3. Step name: `send_to_dnp`.',
    '4. Connector: `DNP Service`.',
    '5. Method: `POST`.',
    '6. Path: `/api/marking/pools`.',
    '7. Headers: `Content-Type: application/json`.',
    '8. Body: `target_payload`.',
    '9. Timeout: `20` seconds.',
    '10. Save request artifact: `target.request.json`.',
    '11. Save response artifact: `target.response.json`.',
    '12. Save draft, then publish flow.',
    '',
    '[SCREENSHOT: send_to_dnp Call Endpoint block settings]',
    '',
    'Connector settings:',
    '',
    '```text',
    'Connector: DNP Service',
    'Method: POST',
    'Path: /api/marking/pools',
    'Body: target_payload',
    '```',
    '',
    'Что должно произойти после сохранения: flow показывает полный маршрут `receive -> get_contractor -> get_product -> build_target_payload -> send_to_dnp`, а target call еще не выполнялся до реального теста.',
    '',
    '## 8. Dry Run',
    'Dry Run не отправляет запрос во внешний API. Он показывает, что OMH сделал бы при реальном запуске: какой OData request построит, какой JSON соберет и какой target request подготовит.',
    '',
    'Пошагово:',
    '',
    '1. Откройте `Test Console`.',
    '2. Select endpoint `onec-pool-to-dnp`.',
    '3. Paste Source JSON from 1C.',
    '4. Click `Dry Run`.',
    '5. Open `OData request preview` для `get_contractor`.',
    '6. Open `OData request preview` для `get_product`.',
    '7. Open `JSON builder output`.',
    '8. Open `target request preview`.',
    '',
    '[SCREENSHOT: Test Console Dry Run for full flow]',
    '',
    'Ожидаемые preview:',
    '',
    '- `OData request preview` показывает resource, filter, select, top и выбранную OData connection.',
    '- `JSON builder output` показывает `target_payload` до отправки.',
    '- `target request preview` показывает `POST /api/marking/pools` и body `target_payload`.',
    '',
    'Что должно произойти после Dry Run: вы можете объяснить будущий запрос без реального вызова DNP API. Если Dry Run уже показывает пустой `contractor` или `product`, не нажимайте Send.',
    '',
    '## 9. Реальный тест через Test Console',
    'Когда Dry Run корректный, можно отправить настоящий request.',
    '',
    'Пошагово:',
    '',
    '1. В `Test Console` оставьте endpoint `onec-pool-to-dnp`.',
    '2. Убедитесь, что body совпадает с Source JSON.',
    '3. Click `Send`.',
    '4. Скопируйте `event_id` из ответа.',
    '5. Click `timeline_url` или откройте Event Timeline.',
    '6. Проверьте steps и artifacts.',
    '',
    'curl example:',
    '',
    '```bash',
    "curl -X POST 'http://omh-server:8000/api/bus/in/onec-pool-to-dnp' \\",
    "  -H 'Content-Type: application/json' \\",
    "  -H 'X-OMH-Token: training-token' \\",
    "  --data-binary '{",
    '    "inn": "7707083893",',
    '    "product_code": "ABC-123",',
    '    "pool_id": "POOL-001",',
    '    "codes": ["010464615169738421ABC", "010464615169738421DEF"]',
    "  }'",
    '```',
    '',
    'Expected response:',
    '',
    '```json',
    '{',
    '  "accepted": true,',
    '  "event_id": "event-uuid",',
    '  "timeline_url": "/events/event-uuid",',
    '  "status": "queued"',
    '}',
    '```',
    '',
    'Expected Timeline:',
    '',
    '```text',
    'receive',
    'get_contractor',
    'get_product',
    'build_target_payload',
    'send_to_dnp',
    'handle_response',
    '```',
    '',
    'Что должно произойти после Send: в Timeline видно каждый шаг, а не только общий success/fail. Если `send_to_dnp` упал, входной request и OData результаты не потеряны.',
    '',
    '## 10. Полный 1С pseudo-code',
    'Этот код показывает общий принцип. В реальной 1С замените сбор JSON на ваш объект/структуру и храните token не в открытом модуле.',
    '',
    '```1c',
    'Данные = Новый Структура;',
    'Данные.Вставить("inn", "7707083893");',
    'Данные.Вставить("product_code", "ABC-123");',
    'Данные.Вставить("pool_id", "POOL-001");',
    '',
    'Коды = Новый Массив;',
    'Коды.Добавить("010464615169738421ABC");',
    'Коды.Добавить("010464615169738421DEF");',
    'Данные.Вставить("codes", Коды);',
    '',
    'ЗаписьJSON = Новый ЗаписьJSON;',
    'ЗаписьJSON.УстановитьСтроку();',
    'ЗаписатьJSON(ЗаписьJSON, Данные);',
    'ТелоЗапроса = ЗаписьJSON.Закрыть();',
    '',
    'Соединение = Новый HTTPСоединение("omh-server", 8000);',
    'Запрос = Новый HTTPЗапрос("/api/bus/in/onec-pool-to-dnp");',
    'Запрос.Заголовки.Вставить("Content-Type", "application/json");',
    'Запрос.Заголовки.Вставить("X-OMH-Token", "training-token");',
    'Запрос.УстановитьТелоИзСтроки(ТелоЗапроса, КодировкаТекста.UTF8);',
    '',
    'Ответ = Соединение.ОтправитьДляОбработки(Запрос);',
    'ТелоОтвета = Ответ.ПолучитьТелоКакСтроку();',
    '',
    'Если Ответ.КодСостояния >= 300 Тогда',
    '  ВызватьИсключение "OMH вернул ошибку: " + ТелоОтвета;',
    'КонецЕсли;',
    '',
    'Сообщить("OMH принял событие: " + ТелоОтвета);',
    '```',
    '',
    'Что должно произойти после внедрения в 1С: пользователь 1С получает быстрый ответ `accepted`, а подробный результат разбирается в OMH Timeline.',
    '',
    '## 11. Timeline и artifacts',
    'Timeline нужен не для красоты. Это главный способ понять, что именно сделал OMH и где остановился обмен.',
    '',
    '| Timeline step | Artifact | Что смотреть |',
    '| --- | --- | --- |',
    '| `receive` | `incoming.request.json` | Исходный JSON от 1С, headers, endpoint slug |',
    '| `get_contractor` | `odata.get_contractor.request.json` | Connection `OData ERP`, resource, filter `ИНН eq ...` |',
    '| `get_contractor` | `odata.get_contractor.response.json` | Найденный `contractor.Ref_Key` или пустой массив |',
    '| `get_product` | `odata.get_product.request.json` | Connection `OData ERP/WMS`, filter `Артикул eq ...` |',
    '| `get_product` | `odata.get_product.response.json` | Найденный `product.Ref_Key` или пустой массив |',
    '| `build_target_payload` | `target_payload.json` | Ровно тот JSON, который должен уйти наружу |',
    '| `send_to_dnp` | `target.request.json` | Method, URL, headers без раскрытия secrets, body |',
    '| `send_to_dnp` | `target.response.json` | HTTP status и оригинальный ответ DNP API |',
    '| `handle_response` | `return_response.json` | Что вернулось в 1С или caller |',
    '',
    'Artifacts explanation: artifact — это сохраненный снимок данных конкретного шага. Его можно открыть позже, приложить к разбору ошибки и использовать для replay без догадок.',
    '',
    '## 12. Если что-то сломалось',
    'Не чините весь flow сразу. Найдите failed step в Timeline и откройте его artifacts.',
    '',
    '| Failed step | Где смотреть | Что обычно исправлять |',
    '| --- | --- | --- |',
    '| `get_contractor` failed | `odata.get_contractor.request.json`, `odata.get_contractor.response.json` | Неверная OData connection, поле `ИНН` называется иначе, ИНН с пробелами, нет прав 1С на `Catalog_Контрагенты` |',
    '| `get_product` failed | `odata.get_product.request.json`, OData Explorer для `Catalog_Номенклатура` | Выбрана ERP вместо WMS, поле `Артикул` называется иначе, product_code не существует |',
    '| `build_target_payload` failed | `target_payload.json` preview, JSON Builder mapping | Ошибка в source path, например `contractor.uuid` вместо `contractor.Ref_Key`, массив `codes` превращен в строку |',
    '| `send_to_dnp` failed | `target.request.json`, `target.response.json`, external error | Неверный connector `DNP Service`, неправильный path `/api/marking/pools`, 401/403 target API, timeout |',
    '',
    'Правило диагностики: если OData response пустой, сначала повторите тот же filter в OData Explorer. Если в Explorer тоже пусто, проблема не во Flow Builder, а в connection/resource/filter/data.',
    '',
    '## 13. Финальная проверка',
    'Перед тем как считать настройку готовой, проверьте:',
    '',
    '::checklist{id="full-flow-click-by-click" items="Endpoint onec-pool-to-dnp создан|Source JSON вставлен в Test Console|get_contractor использует OData ERP и request.body.inn|get_product использует правильную OData connection и request.body.product_code|JSON Builder создает target_payload|Call Endpoint отправляет target_payload в DNP Service|Dry Run показывает OData request preview|Dry Run показывает JSON builder output|Dry Run показывает target request preview|Real Send создает event_id|Timeline содержит receive, get_contractor, get_product, build_target_payload, send_to_dnp, handle_response|Artifacts каждого шага открываются"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Проверить весь интеграционный поток" href="/docs/onec/academy/test-full-flow"}',
  )),
  page('academy', 'test-full-flow', 'Проверяем весь интеграционный поток', 'Прогнать весь flow: Test Console, Dry Run, Send и Timeline.', 111, mdLines(
    '# Проверяем весь интеграционный поток',
    '',
    '::lesson-page{label="Пакет уроков B · Flow Builder"}',
    '',
    '## Что вы настроите',
    'Вы выполните end-to-end test Golden Scenario: 1C POST payload проходит read fields, two OData queries, JSON Builder, target API call и Timeline.',
    '',
    '## Зачем это нужно',
    'Настройка считается понятной только когда пользователь может сам отправить test request, увидеть target JSON preview, открыть Timeline и объяснить artifacts каждого шага.',
    '',
    '## Что нужно заранее',
    '- Endpoint создан.',
    '- Read fields настроены.',
    '- Contractor OData query настроен.',
    '- Product OData query настроен.',
    '- Build JSON настроен.',
    '- Target API step настроен.',
    '',
    '## Пошаговая настройка',
    '1. Откройте `Test Console`.',
    '2. Choose endpoint: `onec-pool-to-dnp`.',
    '3. Paste JSON из этого урока.',
    '4. Click `Dry Run`.',
    '5. Check target JSON preview.',
    '6. Если Preview корректный, click `Send`.',
    '7. Copy `event_id` или откройте `timeline_url` из response.',
    '8. Open Timeline.',
    '9. Проверьте шаги и artifacts по порядку.',
    '',
    '[SCREENSHOT: Test Console dry run Golden Scenario]',
    '[SCREENSHOT: Timeline two OData JSON endpoint flow]',
    '',
    '## Тестовый запрос',
    '```json',
    '{',
    '  "inn": "7707083893",',
    '  "product_code": "ABC-123",',
    '  "pool_id": "POOL-001",',
    '  "codes": ["code1", "code2"]',
    '}',
    '```',
    '',
    '## Что должно быть в Timeline',
    '```text',
    'receive',
    'match_route',
    'odata_query contractor',
    'odata_query product',
    'build_json',
    'call_endpoint',
    'handle_response',
    '```',
    '',
    '## Artifacts по шагам',
    '| Шаг | Artifact | Что проверить |',
    '| --- | --- | --- |',
    '| receive | incoming.request.json | Исходный JSON от 1C не потерян |',
    '| match_route | route.match.json | Выбран endpoint onec-pool-to-dnp |',
    '| odata_query contractor | odata.contractor.request.json / response.json | Filter by INN и найденный contractor.Ref_Key |',
    '| odata_query product | odata.product.request.json / response.json | Filter by article и найденный product.Ref_Key |',
    '| build_json | target_payload.json | Финальный JSON совпадает с target contract |',
    '| call_endpoint | target.request.json / target.response.json | Что ушло в DNP Service и что вернул target API |',
    '| handle_response | return_response.json | Что 1C получила в ответ: accepted event или business result |',
    '',
    '## Что должно получиться',
    '::expected-result{items="Dry Run показывает target JSON preview|Send создает event_id|Timeline содержит receive, match_route, two OData queries, build_json, call_endpoint, handle_response|Artifacts позволяют объяснить результат без чтения кода"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-b-test-full-flow" items="Открыл Test Console|Выбрал endpoint|Вставил JSON|Запустил Dry Run|Проверил target JSON preview|Нажал Send|Открыл Timeline|Проверил artifacts каждого шага"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Нажать Send без Dry Run|Проверить только HTTP response и не открыть Timeline|Не проверить target_payload artifact|Не проверить оба OData response|Делать retry, не поняв failed step"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Прочитать Timeline и артефакты" href="/docs/onec/academy/lesson-11-read-timeline-and-artifacts"}',
  )),
];

export const academyPages: PageSeed[] = [
  lesson({
    slug: 'lesson-01-what-is-omh-for-1c-users',
    order: 10,
    title: 'Урок 01 — Разбираемся, как OMH помогает пользователю 1С',
    description: 'Карта продукта для 1C пользователя: endpoint, OData connection, flow, timeline и artifact.',
    build: 'Вы соберете понятную карту: где 1C отправляет POST, где OMH читает поля, где выполняются два OData lookup, где собирается JSON и где смотреть результат.',
    why: 'Новичок должен сначала понять роли экранов. OData Connection не равен endpoint, endpoint не равен Flow, а Timeline не просто лог. Это рабочая карта внедрения.',
    before: ['Ничего создавать пока не нужно.', 'Откройте Documentation и 1C Cockpit в соседних вкладках.', 'Держите перед глазами Golden Scenario, потому что все уроки идут вокруг него.'],
    steps: [
      'Откройте 1C Cockpit и посмотрите основные плитки: OData, Flows, Test Console, Timeline.',
      'Откройте OData Connections. Запомните: здесь хранятся подключения к базам 1C, например OData ERP или OData WMS.',
      'Откройте Integration Flows. Запомните: здесь описывается бизнес-маршрут Golden Scenario.',
      'Откройте Test Console. Запомните: здесь можно отправить POST без кода 1C.',
      'Откройте Event Journal или Timeline. Запомните: здесь видно каждый шаг и каждый artifact.'
    ],
    example: `~~~text
1C POST /api/bus/in/onec-pool-to-dnp
  -> read request.body.inn
  -> OData ERP: find contractor by INN
  -> read request.body.product_code
  -> OData ERP/WMS: find product by article
  -> Build target JSON
  -> POST to DNP API
  -> Timeline + artifacts
~~~`,
    expected: [
      'Пользователь понимает, что сначала создается OData connection, затем endpoint/flow, затем тестовый запрос.',
      'Пользователь знает, что OData пароль нужен OMH для запроса в 1C, а inbound token нужен 1C для вызова OMH.',
      'Пользователь знает, что Timeline является главным местом проверки результата.'
    ],
    mistakes: [
      'Начинать с редактирования JSON flow без проверки OData connection.',
      'Искать ошибку только в браузере, не открывая Timeline.',
      'Путать входной token endpoint с логином/паролем OData.'
    ],
    checklist: ['Понял Endpoint', 'Понял OData Connection', 'Понял Integration Flow', 'Понял Timeline', 'Понял Artifact'],
    next: '[Урок 02 — Создаём OData-подключение к 1С](/docs/onec/academy/lesson-02-create-odata-connection).'
  }),
  lesson({
    slug: 'lesson-02-create-odata-connection',
    order: 20,
    title: 'Урок 02 — Создаём OData-подключение к 1С',
    description: 'Создание named OData profile для ERP, WMS или УСП.',
    build: 'Вы создадите saved connection `OData ERP training`, которую следующие уроки будут выбирать из списка, а не вводить руками каждый раз.',
    why: 'Named connection делает интеграцию предсказуемой. В flow видно, в какую базу идет lookup, кто владелец credentials и где проверять metadata.',
    before: defaultBefore,
    steps: [
      'Откройте Data Tools -> OData Connections.',
      'Нажмите Create или выберите preset OData ERP.',
      'Введите name: OData ERP training.',
      'Введите base URL: http://erp-demo/ERP/odata/standard.odata.',
      'Выберите auth type basic.',
      'Введите username: Администратор, password: 123 для учебного стенда или `$secret:onec.erp.password` для production.',
      'Сохраните connection.',
      'Нажмите Test $metadata и дождитесь HTTP 200 или понятной внешней ошибки.'
    ],
    example: `~~~json
{
  "name": "OData ERP training",
  "base_url": "http://erp-demo/ERP/odata/standard.odata",
  "auth_type": "basic",
  "username": "Администратор",
  "password": "123",
  "default_top": 50,
  "max_pages": 5
}
~~~`,
    expected: [
      'В списке OData Connections появился `OData ERP training`.',
      'Metadata test показывает success или точную ошибку 1C.',
      'Connection доступен в OData Explorer и Flow Builder.'
    ],
    mistakes: [
      'Указывать URL базы без `/odata/standard.odata`.',
      'Создавать raw Connector вместо OData Connection для каждого flow.',
      'Оставлять пароль `123` в production вместо Secrets Store.'
    ],
    checklist: ['Создал OData connection', 'Проверил base URL', 'Проверил $metadata', 'Понял где хранить пароль'],
    next: '[Урок 03 — Проверяем OData-запрос в OData Explorer](/docs/onec/academy/lesson-03-test-odata-in-odata-explorer).'
  }),
  lesson({
    slug: 'lesson-03-test-odata-in-odata-explorer',
    order: 30,
    title: 'Урок 03 — Проверяем OData-запрос в OData Explorer',
    description: 'Проверка resource, filter, select и sample response до настройки flow.',
    build: 'Вы выполните первый запрос к `Catalog_Контрагенты` и сохраните точные поля, которые потом нужны для contractor lookup.',
    why: 'Flow не должен быть местом угадывания имен ресурсов. Сначала пользователь проверяет запрос в Explorer и только потом переносит его в builder.',
    before: ['Пройден урок 02.', 'Есть OData connection `OData ERP training`.', 'Пользователь 1C имеет права читать справочник контрагентов.'],
    steps: [
      'Откройте OData Explorer.',
      'Выберите connection `OData ERP training`.',
      'Загрузите resources из metadata.',
      'Найдите resource контрагентов, например `Catalog_Контрагенты`.',
      'Введите filter: `ИНН eq \'7707083893\'`.',
      'Введите select: `Ref_Key,Description,ИНН`.',
      'Поставьте top: 1.',
      'Нажмите Run query.',
      'Сохраните lookup template `Find contractor by INN`, если результат корректный.'
    ],
    example: `~~~text
Connection: OData ERP training
Resource: Catalog_Контрагенты
$filter: ИНН eq '7707083893'
$select: Ref_Key,Description,ИНН
$top: 1
~~~`,
    expected: [
      'Explorer показывает запрос и ответ OData.',
      'В ответе есть `Ref_Key`, `Description`, `ИНН`.',
      'Пользователь понимает, какие поля переносить в первый OData lookup.'
    ],
    mistakes: [
      'Писать человекочитаемое имя справочника вместо technical OData resource.',
      'Забывать кавычки вокруг строкового ИНН.',
      'Делать широкий запрос без `$top` и `$select`.'
    ],
    checklist: ['Выбрал connection', 'Нашел resource', 'Проверил filter', 'Проверил select', 'Сохранил lookup idea'],
    next: '[Урок 04 — Создаём входную точку для POST-запроса из 1С](/docs/onec/academy/lesson-04-create-inbound-endpoint-for-1c-post).'
  }),
  lesson({
    slug: 'lesson-04-create-inbound-endpoint-for-1c-post',
    order: 40,
    title: 'Урок 04 — Создаём входную точку для POST-запроса из 1С',
    description: 'Создание входной точки, куда 1C отправит Golden Scenario payload.',
    build: 'Вы создадите endpoint `/api/bus/in/onec-pool-to-dnp` с JSON input и optional static token.',
    why: 'Endpoint фиксирует контракт между 1C и OMH: URL, method, headers, content type и поведение при ошибке auth.',
    before: ['Пройден урок 01.', 'Вы знаете, какой JSON 1C будет отправлять.', 'Решено, нужен ли inbound token для учебного стенда.'],
    steps: [
      'Откройте Integration Bus или Integration Flows.',
      'Создайте inbound endpoint с slug `onec-pool-to-dnp`.',
      'Выберите method POST.',
      'Выберите input mode JSON.',
      'Включите static token для production-like проверки.',
      'Скопируйте endpoint URL для 1C разработчика.',
      'Сохраните контракт headers: Content-Type и X-OMH-Token.'
    ],
    example: `~~~bash
curl -X POST http://localhost:8000/api/bus/in/onec-pool-to-dnp \\
  -H 'Content-Type: application/json' \\
  -H 'X-OMH-Token: training-token' \\
  -d '${goldenScenarioPayload.replace(/'/g, "'\\''")}'
~~~`,
    expected: [
      'Endpoint виден в списке routes или flow inputs.',
      'Без token возвращается понятная auth ошибка, если token включен.',
      'С token создается event или тестовый accepted response.'
    ],
    mistakes: [
      'Передавать OData username/password во входном JSON.',
      'Использовать GET для payload с marking codes.',
      'Не документировать \`X-OMH-Token\` для разработчика 1C.'
    ],
    checklist: ['Создал endpoint', 'Скопировал URL', 'Проверил headers', 'Понял token auth'],
    next: '[Урок 05 — Читаем значения из входящего запроса](/docs/onec/academy/lesson-05-read-values-from-incoming-request).'
  }),
  lesson({
    slug: 'lesson-05-read-values-from-incoming-request',
    order: 50,
    title: 'Урок 05 — Читаем значения из входящего запроса',
    description: 'Извлечение INN, product_code, pool_id и codes из входного JSON.',
    build: 'Вы настроите первые шаги flow: прочитать поля из \`request.body\` и сохранить их как понятные variables.',
    why: 'Следующие OData lookup не должны читать сырой JSON руками. Им нужны named variables: \`inn\`, \`product_code\`, `pool_id`, `codes`.',
    before: ['Создан endpoint из урока 04.', 'Есть sample payload Golden Scenario.', 'Открыт Visual Flow Builder.'],
    steps: [
      'Откройте flow builder для `onec-pool-to-dnp`.',
      'Вставьте sample request Golden Scenario.',
      'Добавьте Read field `request.body.inn`, save as \`inn\`.',
      'Добавьте Read field `request.body.product_code`, save as \`product_code\`.',
      'Добавьте Read field `request.body.pool_id`, save as `pool_id`.',
      'Добавьте Read field `request.body.codes`, save as `codes`.',
      'Включите required для \`inn\`, \`product_code\` и `pool_id`.'
    ],
    example: `~~~json
${goldenScenarioPayload}
~~~

Variables after read:

~~~json
{
  "inn": "7707083893",
  "product_code": "ABC-123",
  "pool_id": "POOL-001",
  "codes": ["010464615169738421ABC", "010464615169738421DEF"]
}
~~~`,
    expected: [
      'Preview показывает variables без undefined/null.',
      'Если удалить \`inn\`, flow останавливается понятной validation error.',
      'Эти variables доступны следующим OData steps.'
    ],
    mistakes: [
      'Писать path `body.inn` вместо `request.body.inn`, если builder ожидает полный path.',
      'Не включать required и потом отправлять пустой lookup.',
      'Сохранять `codes` как строку, хотя target JSON ожидает массив.'
    ],
    checklist: ['Добавил inn', 'Добавил product_code', 'Добавил pool_id', 'Добавил codes', 'Проверил Preview'],
    next: '[Урок 06 — Первая выборка OData: ищем контрагента по ИНН](/docs/onec/academy/lesson-06-first-odata-lookup-contractor-by-inn).'
  }),
  lesson({
    slug: 'lesson-06-first-odata-lookup-contractor-by-inn',
    order: 60,
    title: 'Урок 06 — Первая выборка OData: ищем контрагента по ИНН',
    description: 'Первый lookup Golden Scenario: найти контрагента в 1C ERP по ИНН.',
    build: 'Вы добавите OData step, который берет variable \`inn\`, ищет контрагента и сохраняет результат как `contractor`.',
    why: 'DNP API не должен получать только ИНН, если ему нужен UUID/Ref_Key контрагента. OMH дочитывает данные из 1C и сохраняет artifact запроса.',
    before: ['Пройден урок 05.', 'В OData Explorer проверен filter для `Catalog_Контрагенты`.', 'В flow есть variable \`inn\`.'],
    steps: [
      'Добавьте step OData lookup.',
      'Выберите connection `OData ERP training`.',
      'Укажите resource `Catalog_Контрагенты`.',
      'Укажите filter field `ИНН`, operator `eq`, value `{{variables.inn}}`.',
      'Укажите select `Ref_Key,Description,ИНН`.',
      'Поставьте top 1.',
      'Save as: `contractor`.',
      'Включите Required result.'
    ],
    example: `~~~json
{
  "connection": "OData ERP training",
  "resource": "Catalog_Контрагенты",
  "filter": "ИНН eq '{{variables.inn}}'",
  "select": ["Ref_Key", "Description", "ИНН"],
  "top": 1,
  "save_as": "contractor",
  "required": true
}
~~~`,
    expected: [
      'Preview показывает `contractor.Ref_Key` и `contractor.Description`.',
      'Timeline сохраняет OData request и response artifacts.',
      'Если контрагент не найден, flow останавливается до target API.'
    ],
    mistakes: [
      'Не ставить Required result и отправлять target JSON с пустым contractor_uuid.',
      'Использовать \`product_code\` вместо \`inn\` в filter.',
      'Писать filter вручную иначе, чем он прошел в OData Explorer.'
    ],
    checklist: ['Выбрал connection', 'Настроил resource', 'Настроил filter by INN', 'Сохранил as contractor', 'Включил Required'],
    next: '[Урок 07 — Вторая выборка OData: ищем товар по артикулу](/docs/onec/academy/lesson-07-second-odata-lookup-product-by-article).'
  }),
  lesson({
    slug: 'lesson-07-second-odata-lookup-product-by-article',
    order: 70,
    title: 'Урок 07 — Вторая выборка OData: ищем товар по артикулу',
    description: 'Второй lookup Golden Scenario: найти товар по product_code.',
    build: 'Вы добавите второй OData lookup, который ищет номенклатуру в ERP или WMS и сохраняет результат как `product`.',
    why: 'Один flow может использовать несколько OData sources. Главное — явно назвать connection и save_as, чтобы следующий step не перепутал contractor и product.',
    before: ['Пройден урок 06.', 'В OData Explorer проверен resource номенклатуры.', 'В flow есть variable \`product_code\`.'],
    steps: [
      'Добавьте второй OData lookup после contractor lookup.',
      'Выберите connection `OData ERP training` или `OData WMS training`, если товар хранится в WMS.',
      'Укажите resource `Catalog_Номенклатура`.',
      'Укажите filter field `Артикул`, operator `eq`, value `{{variables.product_code}}`.',
      'Укажите select `Ref_Key,Description,Артикул`.',
      'Save as: `product`.',
      'Включите Required result, если без товара DNP payload нельзя отправлять.'
    ],
    example: `~~~json
{
  "connection": "OData ERP training",
  "resource": "Catalog_Номенклатура",
  "filter": "Артикул eq '{{variables.product_code}}'",
  "select": ["Ref_Key", "Description", "Артикул"],
  "top": 1,
  "save_as": "product",
  "required": true
}
~~~`,
    expected: [
      'Preview показывает два независимых результата: `contractor` и `product`.',
      'Timeline содержит два OData request artifacts.',
      'Product lookup использует \`product_code\`, а не \`inn\`.'
    ],
    mistakes: [
      'Назвать второй lookup тоже `contractor` и перезаписать результат.',
      'Выбрать не ту OData connection, например WMS вместо ERP без проверки.',
      'Не ограничить `$select` и тащить весь справочник.'
    ],
    checklist: ['Добавил второй lookup', 'Выбрал правильную базу', 'Сохранил as product', 'Проверил два artifacts'],
    next: '[Урок 08 — Собираем целевой JSON](/docs/onec/academy/lesson-08-build-target-json).'
  }),
  lesson({
    slug: 'lesson-08-build-target-json',
    order: 80,
    title: 'Урок 08 — Собираем целевой JSON',
    description: 'Сборка финального JSON для DNP API из входных данных и OData результатов.',
    build: 'Вы соберете `target_payload`, где pool_id и codes приходят из 1C, а contractor/product UUID и names приходят из OData.',
    why: 'Целевой API должен получить стабильную схему, а не случайный сырой ответ 1C OData. JSON Builder делает контракт явным и тестируемым.',
    before: ['Пройдены уроки 06 и 07.', 'В preview есть `contractor` и `product`.', 'Известна схема DNP API.'],
    steps: [
      'Добавьте Build JSON step.',
      'Создайте поле `pool_id` из `{{variables.pool_id}}`.',
      'Создайте поле `contractor_uuid` из `{{steps.contractor.first.Ref_Key}}` или equivalent path вашего builder.',
      'Создайте поле `contractor_name` из `{{steps.contractor.first.Description}}`.',
      'Создайте поле `product_uuid` из `{{steps.product.first.Ref_Key}}`.',
      'Создайте поле `product_name` из `{{steps.product.first.Description}}`.',
      'Передайте `codes` как массив, не как строку.',
      'Добавьте `source_system`: `1C`.',
      'Save as: `target_payload`.'
    ],
    example: `~~~json
${goldenScenarioTargetJson}
~~~`,
    expected: [
      'Preview показывает JSON той же формы, что ожидает DNP API.',
      'В target_payload нет лишнего сырого OData объекта.',
      '`codes` остается массивом.'
    ],
    mistakes: [
      'Отправлять наружу весь `contractor` и `product` вместо нужных полей.',
      'Потерять массив codes при ручной строковой склейке.',
      'Не зафиксировать target schema в документации flow.'
    ],
    checklist: ['Собрал pool_id', 'Собрал contractor fields', 'Собрал product fields', 'Сохранил codes массивом', 'Проверил target_payload'],
    next: '[Урок 09 — Отправляем JSON во внешний API](/docs/onec/academy/lesson-09-send-json-to-external-api).'
  }),
  lesson({
    slug: 'lesson-09-send-json-to-external-api',
    order: 90,
    title: 'Урок 09 — Отправляем JSON во внешний API',
    description: 'Отправка target_payload во внешний DNP/internal API.',
    build: 'Вы добавите target call: POST JSON на внутренний DNP API с timeout, headers и response handling.',
    why: 'Интеграция заканчивается не сборкой JSON, а контролируемым вызовом внешней системы с artifacts, timeout и понятной ошибкой.',
    before: ['Пройден урок 08.', 'Создан REST connector или endpoint для DNP API.', 'Известен path и auth target API.'],
    steps: [
      'Добавьте Target call или REST step.',
      'Выберите connector `DNP internal API`.',
      'Method: POST.',
      'Path: `/api/v1/marking/pools`.',
      'Header `Content-Type: application/json`.',
      'Body source: `target_payload`.',
      'Timeout: начните с 10 секунд для sync и больше для async.',
      'Включите сохранение target.request и target.response artifacts.'
    ],
    example: `~~~bash
curl -X POST https://dnp.internal/api/v1/marking/pools \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer <secret>' \\
  -d '${goldenScenarioTargetJson.replace(/'/g, "'\\''")}'
~~~`,
    expected: [
      'Target request artifact содержит финальный JSON.',
      'Target response artifact содержит HTTP status и body DNP API.',
      'При 4xx/5xx ошибка не теряется, а видна в Timeline.'
    ],
    mistakes: [
      'Вызывать target API до Required OData lookup.',
      'Не сохранять response artifact и потом не понимать, что вернула внешняя система.',
      'Держать production bearer token в flow JSON вместо Secrets Store.'
    ],
    checklist: ['Выбрал target connector', 'Настроил POST', 'Передал target_payload', 'Проверил timeout', 'Проверил artifacts'],
    next: '[Урок 10 — Проверяем весь интеграционный поток](/docs/onec/academy/lesson-10-test-full-flow).'
  }),
  lesson({
    slug: 'lesson-10-test-full-flow',
    order: 100,
    title: 'Урок 10 — Проверяем весь интеграционный поток',
    description: 'Полный прогон Golden Scenario через Test Console и curl.',
    build: 'Вы отправите учебный POST, проверите response, event id и убедитесь, что все шаги flow прошли в правильном порядке.',
    why: 'Настройка считается рабочей только после полного end-to-end теста. Отдельный OData success не доказывает, что target JSON и DNP call настроены правильно.',
    before: ['Пройдены уроки 01-09.', 'Flow сохранен как draft или опубликован.', 'DNP target доступен или заменен mock endpoint.'],
    steps: [
      'Откройте Test Console.',
      'Выберите endpoint `onec-pool-to-dnp`.',
      'Вставьте Golden Scenario payload.',
      'Добавьте headers `Content-Type` и \`X-OMH-Token\`.',
      'Нажмите Send.',
      'Скопируйте event id из ответа.',
      'Повторите тот же запрос через curl, чтобы разработчик 1C видел контракт без UI.'
    ],
    example: `~~~json
${goldenScenarioPayload}
~~~`,
    expected: [
      'Test Console возвращает success, accepted или понятную контролируемую ошибку.',
      'Event появился в Event Journal.',
      'Flow steps идут в порядке: incoming, read fields, contractor lookup, product lookup, build JSON, target call.'
    ],
    mistakes: [
      'Проверять только preview, но не отправлять реальный POST.',
      'Не проверять negative case: неверный token, пустой INN, неизвестный product_code.',
      'Не сохранять curl пример для 1C разработчика.'
    ],
    checklist: ['Отправил Test Console', 'Получил event id', 'Повторил curl', 'Проверил success и controlled error'],
    next: '[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts).'
  }),
  lesson({
    slug: 'lesson-11-read-timeline-and-artifacts',
    order: 110,
    title: 'Урок 11 — Читаем Timeline и артефакты',
    description: 'Как читать результат выполнения без доступа к коду.',
    build: 'Вы откроете event Timeline и научитесь находить входной JSON, OData requests, OData responses, target JSON и ошибку внешней системы.',
    why: 'Timeline превращает “не работает” в конкретный факт: какой шаг упал, какой request ушел, какой response вернулся и что можно повторить.',
    before: ['Пройден урок 10.', 'Есть event id успешного или ошибочного теста.', 'Доступен Event Journal.'],
    steps: [
      'Откройте Event Journal.',
      'Найдите event по id, trace id, pool_id или времени.',
      'Откройте Timeline.',
      'Найдите `incoming.request` и проверьте исходный payload.',
      'Откройте artifacts contractor lookup: request и response.',
      'Откройте artifacts product lookup: request и response.',
      'Откройте `transform.output` или `target_payload`.',
      'Откройте \`target.request\` и \`target.response\`.',
      'Если step failed, сначала читайте original external error.'
    ],
    example: `~~~text
Artifacts to read:
- incoming.request.json
- odata.contractor.request.json
- odata.contractor.response.json
- odata.product.request.json
- odata.product.response.json
- target_payload.json
- target.request.json
- target.response.json
- external.error.json
~~~`,
    expected: [
      'Пользователь может объяснить результат по artifacts, а не по догадкам.',
      'Видно, какое поле пришло из 1C и какое поле пришло из OData.',
      'Оригинальная ошибка target/OData не замаскирована общим текстом.'
    ],
    mistakes: [
      'Смотреть только общий статус event.',
      'Не открывать OData request artifact при пустом lookup.',
      'Делать retry до понимания root cause.'
    ],
    checklist: ['Открыл incoming.request', 'Открыл оба OData artifacts', 'Открыл target_payload', 'Открыл target.response', 'Понял failed step'],
    next: '[Урок 12 — Исправляем частые ошибки](/docs/onec/academy/lesson-12-fix-common-errors).'
  }),
  lesson({
    slug: 'lesson-12-fix-common-errors',
    order: 120,
    title: 'Урок 12 — Исправляем частые ошибки',
    description: 'Первые действия при 401, resource not found, empty lookup, target error и DLQ.',
    build: 'Вы получите короткий алгоритм исправления Golden Scenario без паники: где смотреть, что менять и когда делать replay.',
    why: 'В production важна не только настройка happy path. Пользователь должен понимать, какие ошибки исправляются данными, какие конфигурацией, а какие retry.',
    before: ['Пройден урок 11.', 'Есть доступ к Timeline, OData Connections, OData Explorer и DLQ.', 'Пользователь понимает разницу inbound token, OData credentials и target API auth.'],
    steps: [
      'Если входной endpoint вернул 401, проверьте \`X-OMH-Token\`.',
      'Если OData вернула 401, проверьте OData Connection credentials или secret.',
      'Если resource не найден, откройте OData Explorer и выберите resource из metadata.',
      'Если contractor/product lookup пустой, скопируйте filter из artifact и повторите в Explorer.',
      'Если target API вернул ошибку, откройте target.response и проверьте business message.',
      'Если event в DLQ, сначала прочитайте root cause, потом исправьте данные/config и только затем Replay from DLQ.',
      'Если меняли flow, публикуйте новую config version с нормальным comment.'
    ],
    example: `~~~text
401 inbound endpoint -> X-OMH-Token
401 OData -> OData username/password/secret
404 OData resource -> metadata/resource name
Required lookup empty -> filter/value/source data
Target 400 -> target_payload contract
Target timeout -> response mode, queue, retry policy
DLQ -> inspect artifacts, fix, replay
~~~`,
    expected: [
      'Пользователь выбирает правильный экран для каждой ошибки.',
      'Replay выполняется только после исправления причины.',
      'Ошибки Golden Scenario объяснимы для поддержки и 1C разработчика.'
    ],
    mistakes: [
      'Нажимать retry на auth ошибку без изменения credentials.',
      'Менять flow filter, не проверив его в OData Explorer.',
      'Удалять DLQ событие до разбора artifacts.'
    ],
    checklist: ['Понял 401 inbound', 'Понял 401 OData', 'Понял empty lookup', 'Понял target error', 'Понял DLQ replay']
  }),
];

export const referencePages: PageSeed[] = [
  page('reference', 'odata-connection', 'Reference — OData Connection', 'Что хранит OData connection и где он используется.', 10, md(`
# Reference — OData Connection

OData Connection — сохраненное подключение к конкретной публикации 1C OData. Пользователь создает его один раз, а потом выбирает из списка в OData Explorer и Flow Builder.

## Примеры имен
- OData ERP production
- OData WMS
- OData УСП test

## Что хранить
~~~json
{
  "name": "OData ERP production",
  "base_url": "https://erp.example.local/ERP/odata/standard.odata",
  "auth_type": "basic",
  "username": "exchange_user",
  "password": "$secret:onec.erp.password"
}
~~~

## Почему это важно
Flow должен явно показывать, в какую базу идет lookup. Пароль храните через Secrets Store.
`)),
  page('reference', 'endpoint', 'Reference — Endpoint', 'Куда 1C отправляет request и какие headers нужны.', 20, md(`
# Reference — Endpoint

Endpoint — URL в OMH, куда 1C отправляет запрос.

~~~text
POST /api/bus/in/onec-pool-to-dnp
~~~

## Минимальный контракт
- Method: POST.
- Header: Content-Type: application/json.
- Header: X-OMH-Token, если endpoint закрыт static token.
- Body: JSON или XML по выбранному input mode.

Endpoint защищает вход в OMH. Он не заменяет OData credentials.
`)),
  page('reference', 'integration-flow', 'Reference — Integration Flow', 'No-code сценарий для endpoint, lookup, transform и target call.', 30, md(`
# Reference — Integration Flow

Integration Flow — пользовательский сценарий обмена. В Golden Scenario flow делает: read fields, contractor lookup, product lookup, build JSON, call DNP API.

## Хороший flow
1. Имеет понятный endpoint slug.
2. Использует named OData connections.
3. Сохраняет результаты как \`contractor\`, \`product\`, \`target_payload\`.
4. Публикуется через draft/publish, а не правится вслепую.
`)),
  page('reference', 'visual-flow-builder', 'Reference — Visual Flow Builder', 'Где собирать шаги Golden Scenario.', 40, md(`
# Reference — Visual Flow Builder

Visual Flow Builder — экран, где внедренец собирает integration flow без кода.

## Основные блоки
- Read field: берет значения из \`request.body\`.
- OData lookup: ищет объект в 1C OData.
- JSON Builder: собирает target payload.
- Target call: отправляет JSON во внешнюю систему.
- Preview: проверяет flow на sample request до публикации.
`)),
  page('reference', 'json-builder', 'Reference — JSON Builder', 'Как собирать финальный JSON из variables и lookup results.', 50, md(`
# Reference — JSON Builder

JSON Builder превращает входные поля и результаты OData в стабильный target payload.

~~~json
${goldenScenarioTargetJson}
~~~

## Практическое правило
Отправляйте наружу только поля target contract. Не отправляйте целиком raw OData response, если внешней системе нужны только UUID и name.
`)),
  page('reference', 'timeline', 'Reference — Timeline', 'Где OMH показывает шаги, длительность, ошибки и artifacts.', 60, md(`
# Reference — Timeline

Timeline — главный экран диагностики одного event. Он показывает каждый step, статус, duration и artifacts.

## Что открывать первым
- failed step;
- incoming.request;
- odata request/response;
- target request/response;
- external.error.
`)),
  page('reference', 'queue-dlq', 'Reference — Queue / DLQ', 'Очередь, retry и Dead Letter Queue для 1C интеграций.', 70, md(`
# Reference — Queue / DLQ

Queue нужна для async processing и retry. DLQ — место, куда попадают события после исчерпания попыток или после non-retryable ошибки.

## Когда retry уместен
- timeout;
- temporary network error;
- target 5xx;
- блокировка объекта 1C.

## Когда retry вреден
- неверный token;
- неверный OData пароль;
- обязательный объект не найден;
- ошибка mapping contract.
`)),
  page('reference', 'secrets', 'Reference — Secrets', 'Как хранить пароли OData и target API безопасно.', 80, md(`
# Reference — Secrets

Secrets Store хранит реальные значения паролей и токенов. В config остается только reference.

~~~json
{
  "password": "$secret:onec.erp.password",
  "authorization_header": "$secret:dnp.api.authorization"
}
~~~

Так config можно переносить между окружениями без раскрытия production secret values.
`)),
];

export const troubleshootingPages: PageSeed[] = [
  page("troubleshooting", "onec-returned-401", "Симптом: 1C вернула 401", "Как отличить inbound 401, OData 401 и target 1C 401.", 10, mdLines(
    "# Симптом: 1C вернула 401",
    "",
    "## Что вы видите",
    "- In Test Console or Timeline a step has HTTP `401 Unauthorized`.",
    "- OData Explorer may show `401` while resources are being loaded.",
    "- 1C code receives 401 from OMH endpoint, or OMH receives 401 from 1C OData/HTTP service.",
    "",
    "[SCREENSHOT: Troubleshooting 1C returned 401 timeline]",
    "",
    "## Что это означает",
    "401 is an authentication failure, but the owner depends on the failed step. Inbound endpoint 401 means 1C did not authenticate to OMH. OData 401 means OMH did not authenticate to 1C OData. Target 1C service 401 means target connector credentials or publication path are wrong.",
    "",
    "## Что проверить",
    "- Failed step name: `receive`, `odata_query`, or `call_endpoint`.",
    "- `X-OMH-Token` header in `incoming.request.headers`.",
    "- OData Connection username/password secret.",
    "- Basic auth enabled for the published OData service.",
    "- 1C user rights to read the catalog/document.",
    "- Publication path: `/base/odata/standard.odata` or actual publication alias.",
    "",
    "## Как исправить",
    "1. If failed step is `receive`, update the token used by 1C and retry.",
    "2. If failed step is `odata_query`, open OData Connections and run Test metadata.",
    "3. Re-enter password secret if it was rotated.",
    "4. In 1C, verify the OData user can open the required object.",
    "5. If target HTTP service failed, test the connector against the exact `/hs/...` path.",
    "6. Replay only after credentials pass healthcheck.",
    "",
    "## Где смотреть в OMH",
    "- Timeline -> failed step.",
    "- `incoming.request.headers` for inbound token presence, with secrets redacted.",
    "- `odata.request.json` and `odata.response.json` for OData 401.",
    "- `target.response.json` for 1C HTTP service 401.",
    "- OData Connections -> Test metadata.",
    "",
    "## Связанные страницы",
    "- [Справочник OData Connection](/docs/onec/reference/odata-connection)",
    "- [Создаём OData-подключение к 1С](/docs/onec/academy/create-odata-connection)",
    "- [Справочник Timeline](/docs/onec/reference/timeline)"
  )),
  page("troubleshooting", "odata-resource-not-found", "Симптом: OData resource не найден", "Resource отсутствует в metadata или выбран не тот OData profile.", 20, mdLines(
    "# Симптом: OData resource не найден",
    "",
    "## Что вы видите",
    "- OData step fails with resource not found.",
    "- OData Explorer resources list does not contain `Catalog_Контрагенты` or `Catalog_Номенклатура`.",
    "- Timeline has `odata.request.json`, but 1C returns 404 or metadata mismatch.",
    "",
    "[SCREENSHOT: Troubleshooting OData resource not found]",
    "",
    "## Что это означает",
    "Flow points to a resource that is not published in the selected 1C OData base. Most often the technical OData name is different, metadata was not loaded, the wrong base was selected, or the object is not published in 1C.",
    "",
    "## Что проверить",
    "- Exact OData Connection selected in the step.",
    "- Resource name copied from OData Explorer, not typed by memory.",
    "- `$metadata` can be loaded successfully.",
    "- Object is published in 1C OData settings.",
    "- Base URL points to the intended ERP/УСП/WMS base.",
    "",
    "## Как исправить",
    "1. Open OData Explorer.",
    "2. Select the same OData Connection as the failing flow step.",
    "3. Reload metadata.",
    "4. Search the resource list and copy the exact resource name.",
    "5. If missing, publish the object in 1C and reload metadata.",
    "6. Update the flow step, publish config and rerun Preview.",
    "",
    "## Где смотреть в OMH",
    "- OData Explorer resources list.",
    "- Timeline -> `odata.request.json`.",
    "- OData Connection -> base URL and Test metadata.",
    "- Config History if the resource worked before and changed after publish.",
    "",
    "## Связанные страницы",
    "- [Урок OData Explorer](/docs/onec/academy/test-odata-explorer)",
    "- [Фильтры OData и chaining](/docs/onec/tools/odata-chaining-fields)",
    "- [Справочник Flow Builder](/docs/onec/reference/visual-flow-builder)"
  )),
  page("troubleshooting", "contractor-not-found-by-inn", "Симптом: контрагент не найден по ИНН", "Lookup контрагента вернул пустой OData result.", 30, mdLines(
    "# Симптом: контрагент не найден по ИНН",
    "",
    "## Что вы видите",
    "- Timeline shows OData contractor step failed as required lookup empty.",
    "- `odata.contractor.response.json` contains an empty result.",
    "- Target JSON has no `contractor_uuid`, or flow stops before target call.",
    "",
    "```json",
    "{",
    "  \"value\": []",
    "}",
    "```",
    "",
    "[SCREENSHOT: Troubleshooting contractor not found by INN]",
    "",
    "## Что это означает",
    "OMH successfully called OData, but the filter did not find a contractor. The usual reasons are wrong INN, spaces, wrong catalog, wrong OData connection, missing user permissions, or a value that must be normalized before lookup.",
    "",
    "## Что проверить",
    "- Actual value in `incoming.request.json` at `request.body.inn`.",
    "- Spaces, non-breaking spaces, quotes and leading zeros.",
    "- Filter field: `ИНН`, `INN` or custom field from metadata.",
    "- Resource: `Catalog_Контрагенты` or actual catalog name.",
    "- OData Connection points to the base where contractor exists.",
    "- OData user has rights to read contractors.",
    "",
    "## Как исправить",
    "1. Copy the exact INN from `incoming.request.json`.",
    "2. Copy the exact filter from `odata.contractor.request.json`.",
    "3. Run the same filter in OData Explorer.",
    "4. Add transform before lookup: trim, remove spaces, normalize string.",
    "5. If contractor is missing in 1C, create/fix it and replay.",
    "6. If permissions are missing, fix 1C user rights and rerun Test metadata.",
    "",
    "## Где смотреть в OMH",
    "- Timeline -> `incoming.request.json`.",
    "- Timeline -> `odata.contractor.request.json`.",
    "- Timeline -> `odata.contractor.response.json`.",
    "- OData Explorer with same OData Connection.",
    "- Transform output before OData step.",
    "",
    "## Связанные страницы",
    "- [Ищем контрагента по ИНН](/docs/onec/academy/find-contractor-by-inn)",
    "- [Первый OData-запрос контрагента](/docs/onec/academy/first-odata-query-contractor)",
    "- [Recipe 2 two OData queries](/docs/onec/recipes/recipe-02-onec-post-two-odata-lookups)"
  )),
  page("troubleshooting", "product-not-found", "Симптом: товар не найден по артикулу", "Lookup товара по product_code вернул пустой result.", 40, mdLines(
    "# Симптом: товар не найден по артикулу",
    "",
    "## Что вы видите",
    "- Product OData step returns empty value.",
    "- Timeline shows `odata_query product` failed.",
    "- JSON Builder cannot fill `product_uuid`.",
    "",
    "```json",
    "{",
    "  \"value\": []",
    "}",
    "```",
    "",
    "[SCREENSHOT: Troubleshooting product not found by article]",
    "",
    "## Что это означает",
    "The product exists somewhere, but the configured OData lookup does not match it. Common causes: field name mismatch, product is in another base, article format differs from input, or the value needs uppercase/trim transform.",
    "",
    "## Что проверить",
    "- Input field: `request.body.product_code`.",
    "- OData field: `Артикул`, `Code`, `SKU` or a custom attribute.",
    "- OData Connection: ERP, УСП or WMS.",
    "- Case sensitivity and spaces.",
    "- Whether product code includes prefix, barcode or variant suffix.",
    "",
    "## Как исправить",
    "1. Open `incoming.request.json` and copy `product_code`.",
    "2. Open OData Explorer for the same base.",
    "3. Try filter by `Артикул`, then `Code`, then custom SKU field from metadata.",
    "4. Add transform: trim, uppercase, remove spaces, map aliases.",
    "5. If product is in WMS, change the second OData step to OData WMS.",
    "6. Replay after Preview shows `product.Ref_Key`.",
    "",
    "## Где смотреть в OMH",
    "- Timeline -> `odata.product.request.json`.",
    "- Timeline -> `odata.product.response.json`.",
    "- OData Explorer resources and fields.",
    "- Transform output before product lookup.",
    "- Flow Builder second OData step settings.",
    "",
    "## Связанные страницы",
    "- [Второй OData-запрос товара](/docs/onec/academy/second-odata-query-product)",
    "- [Фильтры OData и chaining](/docs/onec/tools/odata-chaining-fields)",
    "- [Recipe 2 two OData queries](/docs/onec/recipes/recipe-02-onec-post-two-odata-lookups)"
  )),
  page("troubleshooting", "target-api-returned-error", "Симптом: target API вернул ошибку", "Внешний API вернул 4xx/5xx или business failure.", 50, mdLines(
    "# Симптом: target API вернул ошибку",
    "",
    "## Что вы видите",
    "- Flow reached `call_endpoint`, then failed.",
    "- 1C received proxy response with target failure, or accepted event later failed in Timeline.",
    "- Target response body contains an auth, validation or business message.",
    "",
    "```json",
    "{",
    "  \"error\": \"Invalid token\",",
    "  \"message\": \"Token expired\"",
    "}",
    "```",
    "",
    "[SCREENSHOT: Troubleshooting target API returned error]",
    "",
    "## Что это означает",
    "OMH built a request and called the external target, but the target rejected it or failed. The original target message must be read from artifacts, not guessed from a generic status.",
    "",
    "## Что проверить",
    "- `target.request.json`: URL, method, headers and body sent to target.",
    "- `target.response.json`: HTTP status and original body.",
    "- External error tab in event details.",
    "- Response mode: proxy_response returns target failure to caller, accepted_event stores it in Timeline.",
    "- Whether the target operation is safe to retry.",
    "",
    "## Как исправить",
    "1. Open `target.request.json` and compare it with target API contract.",
    "2. Open `target.response.json` and read original body.",
    "3. If token expired, rotate secret and test connector.",
    "4. If validation failed, fix JSON Builder mapping.",
    "5. If target returned 5xx or timeout, use retry only if the operation is idempotent.",
    "6. If proxy_response is used, update 1C code to handle target status and body.",
    "",
    "## Где смотреть в OMH",
    "- Timeline -> `target.request.json`.",
    "- Timeline -> `target.response.json`.",
    "- External error tab.",
    "- Queue retry status and DLQ if attempts are exhausted.",
    "- Secrets Store for target token reference.",
    "",
    "## Связанные страницы",
    "- [Отправляем JSON во внешний API](/docs/onec/academy/send-to-external-api)",
    "- [Queue / DLQ reference](/docs/onec/reference/queue-dlq)",
    "- [Recipe 1 marking pool external API](/docs/onec/recipes/recipe-01-onec-marking-pool-to-external-api)"
  )),
  page("troubleshooting", "xml-parse-error", "Симптом: XML не парсится", "XML не парсится, кодировка сломана или выбран неверный режим XML.", 60, mdLines(
    "# Симптом: XML не парсится",
    "",
    "## Что вы видите",
    "- XML Tools or flow parse step reports invalid XML.",
    "- Extracted fields are empty.",
    "- Cyrillic text appears corrupted.",
    "- Raw forwarding scenario unexpectedly tries to parse XML.",
    "",
    "[SCREENSHOT: Troubleshooting XML parse failed]",
    "",
    "## Что это означает",
    "The XML body is invalid for the selected mode, encoding is wrong, namespace/path is not handled, or the flow should use raw_forward instead of parse_and_forward.",
    "",
    "## Что проверить",
    "- Raw body in `incoming.request.xml`.",
    "- `Content-Type`: `application/xml` or `text/xml` with correct charset.",
    "- XML declaration encoding.",
    "- Namespaces in XML paths.",
    "- Whether input is raw XML or escaped XML string inside JSON.",
    "- Flow mode: `raw_forward` vs `parse_and_forward`.",
    "",
    "## Как исправить",
    "1. Open XML Tools and paste raw artifact content.",
    "2. Validate XML before looking at OData or target steps.",
    "3. If the goal is unchanged forwarding, switch to raw_forward.",
    "4. If parsing is required, fix XPath/namespace handling.",
    "5. Align Content-Type and XML declaration encoding.",
    "6. Add a negative test for invalid XML before publishing.",
    "",
    "## Где смотреть в OMH",
    "- Timeline -> `incoming.request.xml`.",
    "- XML Tools parse/hash/diff.",
    "- `xml.parse.result.json`.",
    "- `incoming.hash.json` for raw forwarding.",
    "- `target.request.xml` to compare forwarded XML.",
    "",
    "## Связанные страницы",
    "- [Recipe 3 XML raw forwarding](/docs/onec/recipes/recipe-03-onec-xml-raw-forwarding)",
    "- [Рецепт 4. XML из 1C с поиском по ИНН](/docs/onec/recipes/recipe-04-onec-xml-inn-lookup)",
    "- [XML Tools](/docs/onec/tools/xml-tools)"
  )),
  page("troubleshooting", "printer-unavailable", "Симптом: принтер недоступен", "Zebra/printer connector cannot deliver print job.", 70, mdLines(
    "# Симптом: принтер недоступен",
    "",
    "## Что вы видите",
    "- Print job stays failed or retry_waiting.",
    "- Timeline shows printer connector network failure.",
    "- The printer does not print, but 1C has already sent the request.",
    "",
    "```text",
    "Connection refused 192.168.1.50:9100",
    "```",
    "",
    "[SCREENSHOT: Troubleshooting printer unavailable]",
    "",
    "## Что это означает",
    "OMH rendered the print job, but could not connect to the printer or the printer rejected the socket connection. This is usually IP, TCP port, network route, firewall or printer state.",
    "",
    "## Что проверить",
    "- Printer IP and TCP port, usually 9100 for raw ZPL.",
    "- Network route from backend/container host to printer subnet.",
    "- Printer connector status.",
    "- `zpl.rendered.txt` artifact exists.",
    "- Whether duplicate guard/request_id prevents repeated printing.",
    "",
    "## Как исправить",
    "1. Ping or test TCP connection from the OMH host/network.",
    "2. Verify printer IP did not change after DHCP lease update.",
    "3. Check printer is online and accepts raw socket jobs.",
    "4. Open `zpl.rendered.txt` to confirm render succeeded.",
    "5. Retry only after you know the previous job was not printed.",
    "6. If reprint is needed, use explicit reprint action or new request_id.",
    "",
    "## Где смотреть в OMH",
    "- Printing page -> printer connector status.",
    "- Printing page -> print job state.",
    "- Timeline -> `zpl.rendered.txt`.",
    "- Timeline -> `printer.request.json` and `printer.response.json`.",
    "- Queue retry/DLQ for failed print events.",
    "",
    "## Связанные страницы",
    "- [Рецепт 5. Запрос печати на Zebra](/docs/onec/recipes/recipe-05-onec-print-request-to-zebra)",
    "- [Printing page](/printing)",
    "- [Queue / DLQ reference](/docs/onec/reference/queue-dlq)"
  )),
  page("troubleshooting", "event-moved-to-dlq", "Симптом: событие попало в DLQ", "Retry attempts are exhausted or event is non-retryable.", 80, mdLines(
    "# Симптом: событие попало в DLQ",
    "",
    "## Что вы видите",
    "- Event status is `dlq` or appears on Dead Letter Queue page.",
    "- Queue attempts are exhausted.",
    "- Replay from normal queue is no longer happening.",
    "",
    "[SCREENSHOT: Troubleshooting event moved to DLQ]",
    "",
    "## Что это означает",
    "OMH stopped automatic processing to avoid endless retries. The root cause may be bad data, missing OData object, target outage, wrong secret, invalid XML or a non-retryable business rule failure.",
    "",
    "## Что проверить",
    "- Original failed step in Timeline.",
    "- `external.error` or failed step artifact.",
    "- Retry attempts and retry policy.",
    "- Whether the failure is data/config or temporary infrastructure.",
    "- Whether replay can duplicate a target operation or print job.",
    "",
    "## Как исправить",
    "1. Open DLQ and select the event.",
    "2. Open Timeline from the DLQ row.",
    "3. Read the first failed step, not only the final DLQ status.",
    "4. Fix data in 1C, update secret, change mapping or publish new config.",
    "5. Use Edit & Retry if the payload itself needs correction.",
    "6. Use Replay from DLQ after the root cause is fixed.",
    "7. Use Force complete only when business owner confirms the event should not run.",
    "",
    "## Где смотреть в OMH",
    "- Dead Letter Queue page.",
    "- Timeline -> failed step artifacts.",
    "- Queue attempt history.",
    "- Config History if a new config version caused failures.",
    "- Audit log for manual replay, edit retry or force complete.",
    "",
    "## Связанные страницы",
    "- [Queue / DLQ reference](/docs/onec/reference/queue-dlq)",
    "- [Ошибка target API](/docs/onec/troubleshooting/target-api-returned-error)",
    "- [Контрагент не найден по ИНН](/docs/onec/troubleshooting/contractor-not-found-by-inn)"
  )),
];

export const recipePages: PageSeed[] = [
  page("recipes", "recipe-01-onec-marking-pool-to-external-api", "Рецепт 1. 1C отправляет пул кодов маркировки во внешний API", "Маркировочный пул из 1C отправляется во внешний API с понятным endpoint, matcher, target JSON и Timeline.", 10, mdLines(
    "# Рецепт 1. 1C отправляет пул кодов маркировки во внешний API",
    "",
    "## Когда использовать",
    "1C уже сформировала пул кодов маркировки и должна отправить его во внешний DNP/API сервис. OMH нужен как стабильный endpoint, нормализатор payload, маршрутизатор и место, где можно увидеть request, target request, response и повторить событие.",
    "",
    "## Схема",
    "```text",
    "1C POST /api/bus/in/onec-marking-pool",
    "  -> Endpoint matcher pool_type == DNP",
    "  -> Optional transforms: trim codes, normalize pool_id",
    "  -> Build target JSON",
    "  -> REST connector DNP Service",
    "  -> Timeline and artifacts",
    "```",
    "",
    "[SCREENSHOT: Recipe 1 marking pool endpoint and target JSON]",
    "",
    "## URL endpoint",
    "```text",
    "POST http://omh-server:8000/api/bus/in/onec-marking-pool",
    "Content-Type: application/json",
    "X-OMH-Token: <static inbound token>",
    "```",
    "",
    "## Request JSON из 1C",
    "```json",
    "{",
    "  \"pool_id\": \"POOL-001\",",
    "  \"pool_type\": \"DNP\",",
    "  \"product_code\": \"ABC-123\",",
    "  \"codes\": [\"010464615169738421ABC\", \"010464615169738421DEF\"],",
    "  \"source_document\": \"РеализацияТоваровУслуг 000000123\"",
    "}",
    "```",
    "",
    "## Matcher",
    "| Поле | Значение | Что означает |",
    "| --- | --- | --- |",
    "| Endpoint slug | onec-marking-pool | URL part for 1C |",
    "| Matcher path | request.body.pool_type | Value used for routing |",
    "| Operator | equals | Exact match |",
    "| Expected value | DNP | Send to DNP API branch |",
    "| Fallback | fail with business message | Do not silently send unknown pool types |",
    "",
    "## Необязательные transforms",
    "```text",
    "codes = request.body.codes -> trim each item -> remove empty items",
    "pool_id = request.body.pool_id -> trim -> uppercase",
    "source_document = request.body.source_document -> keep as audit field",
    "```",
    "",
    "## Целевой REST connector",
    "```text",
    "Connector: DNP Service",
    "Base URL: https://dnp.example.local",
    "Method: POST",
    "Path: /api/marking/pools",
    "Auth: Bearer token from $secret:dnp.api.token",
    "Timeout: 20 seconds",
    "Response mode to 1C: accepted_event",
    "```",
    "",
    "## Целевой JSON",
    "```json",
    "{",
    "  \"pool_id\": \"POOL-001\",",
    "  \"source_system\": \"1C\",",
    "  \"source_document\": \"РеализацияТоваровУслуг 000000123\",",
    "  \"product_code\": \"ABC-123\",",
    "  \"codes\": [\"010464615169738421ABC\", \"010464615169738421DEF\"]",
    "}",
    "```",
    "",
    "## Ответ для 1C",
    "```json",
    "{",
    "  \"accepted\": true,",
    "  \"event_id\": \"event-uuid\",",
    "  \"timeline_url\": \"/events/event-uuid\"",
    "}",
    "```",
    "",
    "## Timeline",
    "| Шаг | Artifact | Что проверить |",
    "| --- | --- | --- |",
    "| receive | incoming.request.json | 1C payload is saved exactly |",
    "| match_route | route.match.json | pool_type == DNP selected DNP branch |",
    "| transform | transform.output.json | codes are still JSON array |",
    "| call_endpoint | target.request.json | POST /api/marking/pools has expected body |",
    "| handle_response | target.response.json | DNP response body and status are visible |",
    "",
    "## Частые ошибки",
    "- Inbound 401: 1C sent wrong `X-OMH-Token`.",
    "- Unknown pool type: `pool_type` is not `DNP`, `PRINT` or supported value.",
    "- Target 401/403: DNP connector token expired.",
    "- Target 422: target JSON misses `pool_id` or `codes` is not an array.",
    "",
    "## Связанные страницы",
    "- [Собираем целевой JSON](/docs/onec/academy/build-target-json)",
    "- [Отправляем JSON во внешний API](/docs/onec/academy/send-to-external-api)",
    "- [Диагностика ошибки target API](/docs/onec/troubleshooting/target-api-returned-error)",
    "- [Справочник Timeline](/docs/onec/reference/timeline)"
  )),
  page("recipes", "recipe-02-onec-post-two-odata-lookups", "Рецепт 2. 1C отправляет пул, OMH обогащает его двумя OData-запросами", "Компактный production-рецепт: INN -> contractor, product_code -> product, затем финальный JSON.", 20, mdLines(
    "# Рецепт 2. 1C отправляет пул, OMH обогащает его двумя OData-запросами",
    "",
    "## Когда использовать",
    "1C отправляет бизнес-ключи, а внешний API требует внутренние UUID. OMH должен найти контрагента по INN, товар по product_code и собрать compact target JSON.",
    "",
    "## Схема",
    "```text",
    "1C POST",
    "  -> Read request.body.inn, request.body.product_code, request.body.pool_id, request.body.codes",
    "  -> OData query contractor by INN",
    "  -> OData query product by product_code",
    "  -> Build JSON",
    "  -> Target REST API",
    "  -> Timeline",
    "```",
    "",
    "[SCREENSHOT: Recipe 2 two OData queries recipe]",
    "",
    "## Request JSON",
    "```json",
    "{",
    "  \"inn\": \"7707083893\",",
    "  \"product_code\": \"ABC-123\",",
    "  \"pool_id\": \"POOL-001\",",
    "  \"codes\": [\"code1\", \"code2\"]",
    "}",
    "```",
    "",
    "## Lookup контрагента по ИНН",
    "```text",
    "Step type: OData Query",
    "OData connection: OData ERP",
    "Resource: Catalog_Контрагенты",
    "Filter: ИНН eq request.body.inn",
    "Select: Ref_Key,Description,ИНН",
    "Top: 1",
    "Save result as: contractor",
    "Required: yes",
    "```",
    "",
    "## Lookup товара по product_code",
    "```text",
    "Step type: OData Query",
    "OData connection: OData ERP or OData WMS",
    "Resource: Catalog_Номенклатура",
    "Filter: Артикул eq request.body.product_code",
    "Select: Ref_Key,Description,Артикул",
    "Top: 1",
    "Save result as: product",
    "Required: yes",
    "```",
    "",
    "## Итоговый JSON",
    "```json",
    "{",
    "  \"pool_id\": \"POOL-001\",",
    "  \"contractor_uuid\": \"contractor-uuid\",",
    "  \"contractor_name\": \"ООО Ромашка\",",
    "  \"product_uuid\": \"product-uuid\",",
    "  \"product_name\": \"Плата ABC\",",
    "  \"codes\": [\"code1\", \"code2\"],",
    "  \"source_system\": \"1C\"",
    "}",
    "```",
    "",
    "## Ответ",
    "```json",
    "{",
    "  \"accepted\": true,",
    "  \"event_id\": \"event-uuid\",",
    "  \"timeline_url\": \"/events/event-uuid\"",
    "}",
    "```",
    "",
    "## Timeline",
    "- `incoming.request.json` shows exactly what 1C sent.",
    "- `odata.contractor.request.json` shows `Catalog_Контрагенты` and the INN filter.",
    "- `odata.contractor.response.json` should contain one `Ref_Key`.",
    "- `odata.product.request.json` shows `Catalog_Номенклатура` and the article filter.",
    "- `target_payload.json` is the final JSON before target API.",
    "- `target.response.json` is the external API answer.",
    "",
    "## Частые ошибки",
    "- Contractor lookup returns `{ \"value\": [] }`: wrong INN, spaces, wrong OData connection or permissions.",
    "- Product lookup returns empty result: article field name mismatch or product exists in another base.",
    "- Target JSON contains whole OData objects: JSON Builder should select only required fields.",
    "",
    "## Связанные страницы",
    "- [Чтение полей запроса](/docs/onec/academy/read-request-fields)",
    "- [Первый OData-запрос](/docs/onec/academy/first-odata-query-contractor)",
    "- [Второй OData-запрос](/docs/onec/academy/second-odata-query-product)",
    "- [Диагностика: контрагент не найден](/docs/onec/troubleshooting/contractor-not-found-by-inn)"
  )),
  page("recipes", "recipe-03-onec-xml-raw-forwarding", "Рецепт 3. Raw-forwarding XML из одной 1C в другую 1C", "Переслать XML без изменения тела, сохранить SHA256 и доказать, что XML не менялся.", 30, mdLines(
    "# Рецепт 3. Raw-forwarding XML из одной 1C в другую 1C",
    "",
    "## Когда использовать",
    "Старый обмен между двумя 1C уже работает через XML, но нужна наблюдаемость, retry и Timeline. OMH не должен менять XML: он принимает raw body, считает SHA256, сохраняет artifact и пересылает тело дальше.",
    "",
    "## Схема",
    "```text",
    "1C A XML POST",
    "  -> OMH endpoint input_mode raw_xml",
    "  -> raw_forward mode",
    "  -> SHA256 before forwarding",
    "  -> 1C B HTTP service",
    "  -> SHA256 after forwarding",
    "  -> Timeline artifacts",
    "```",
    "",
    "[SCREENSHOT: Recipe 3 XML raw forward artifacts]",
    "",
    "## Raw XML",
    "```xml",
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
    "<ExchangeMessage>",
    "  <DocumentNumber>SO-1001</DocumentNumber>",
    "  <CustomerINN>7707083893</CustomerINN>",
    "  <Amount>12500.00</Amount>",
    "</ExchangeMessage>",
    "```",
    "",
    "## Endpoint и режим",
    "```text",
    "POST http://omh-server:8000/api/bus/in/onec-xml-raw-forward",
    "Content-Type: application/xml; charset=utf-8",
    "Input mode: raw_xml",
    "Forward mode: raw_forward",
    "Do not parse: true",
    "Do not transform: true",
    "```",
    "",
    "## Целевой HTTP-сервис 1C",
    "```text",
    "Connector: 1C B HTTP Service",
    "Method: POST",
    "Path: /hs/exchange/raw",
    "Body source: incoming.raw_body",
    "Headers forwarded: Content-Type, X-OMH-Trace-Id",
    "```",
    "",
    "## SHA256 hash",
    "```text",
    "incoming.sha256 = 8f5c8c4f2a1d7f0c4b0d7e9a6a1e0d7a8c3f6b9c0a1d2e3f4a5b6c7d8e9f0011",
    "forwarded.sha256 = 8f5c8c4f2a1d7f0c4b0d7e9a6a1e0d7a8c3f6b9c0a1d2e3f4a5b6c7d8e9f0011",
    "```",
    "",
    "## Ответ для 1C A",
    "```json",
    "{",
    "  \"accepted\": true,",
    "  \"event_id\": \"event-uuid\",",
    "  \"incoming_sha256\": \"8f5c8c4f...\",",
    "  \"timeline_url\": \"/events/event-uuid\"",
    "}",
    "```",
    "",
    "## Как проверить, что XML не изменился",
    "1. Open Timeline.",
    "2. Open `incoming.request.xml`.",
    "3. Open `target.request.xml`.",
    "4. Compare `incoming.sha256` and `forwarded.sha256`.",
    "5. If hashes are equal, OMH did not mutate XML body.",
    "6. If hashes differ, check whether parse/transform mode was accidentally enabled.",
    "",
    "## Timeline artifacts",
    "- `incoming.request.xml`: original XML from 1C A.",
    "- `incoming.hash.json`: SHA256 before forwarding.",
    "- `target.request.xml`: XML sent to 1C B.",
    "- `target.response.xml` or `target.response.txt`: answer from 1C B.",
    "- `external.error` artifact - original 1C B response if HTTP status is not success.",
    "",
    "## Частые ошибки",
    "- XML parse failed appears even though raw forwarding was expected: input mode was parse_and_forward, not raw_forward.",
    "- SHA256 differs: some transform step changed whitespace, encoding or XML declaration.",
    "- 1C B returned 401: target connector credentials are wrong.",
    "",
    "## Связанные страницы",
    "- [XML Tools](/docs/onec/tools/xml-tools)",
    "- [Диагностика ошибки парсинга XML](/docs/onec/troubleshooting/xml-parse-error)",
    "- [Справочник Timeline](/docs/onec/reference/timeline)"
  )),
  page("recipes", "recipe-04-onec-xml-inn-lookup", "Рецепт 4. XML из 1C с поиском по ИНН", "Прочитать INN из XML, найти contractor через OData и вызвать целевой 1C HTTP service.", 40, mdLines(
    "# Рецепт 4. XML из 1C с поиском по ИНН",
    "",
    "## Когда использовать",
    "1C или legacy system отправляет XML, но целевой 1C HTTP service требует внутренний UUID контрагента. OMH парсит XML, достает INN, делает OData lookup и добавляет contractor UUID в target payload.",
    "",
    "## Схема",
    "```text",
    "XML input",
    "  -> XML parse",
    "  -> Read /Envelope/Customer/INN",
    "  -> OData contractor lookup",
    "  -> Inject contractor_uuid",
    "  -> Call 1C HTTP service",
    "  -> Timeline",
    "```",
    "",
    "[SCREENSHOT: Recipe 4 XML INN lookup path picker]",
    "",
    "## Пример XML",
    "```xml",
    "<Envelope>",
    "  <Customer>",
    "    <INN>7707083893</INN>",
    "    <Name>ООО Ромашка</Name>",
    "  </Customer>",
    "  <Order>",
    "    <Number>WEB-1001</Number>",
    "    <Amount>12500.00</Amount>",
    "  </Order>",
    "</Envelope>",
    "```",
    "",
    "## Path к ИНН",
    "```text",
    "XML path: /Envelope/Customer/INN",
    "Save result as: inn",
    "Required: yes",
    "Normalize: trim, remove spaces",
    "```",
    "",
    "## OData lookup",
    "```text",
    "OData connection: OData ERP",
    "Resource: Catalog_Контрагенты",
    "Filter: ИНН eq inn",
    "Select: Ref_Key,Description,ИНН",
    "Top: 1",
    "Save result as: contractor",
    "Required: yes",
    "```",
    "",
    "## Подстановка contractor UUID",
    "```json",
    "{",
    "  \"order_number\": \"WEB-1001\",",
    "  \"amount\": 12500.00,",
    "  \"contractor_uuid\": \"contractor-uuid\",",
    "  \"contractor_inn\": \"7707083893\",",
    "  \"source_system\": \"XML exchange\"",
    "}",
    "```",
    "",
    "## Вызов целевого HTTP-сервиса 1C",
    "```text",
    "Connector: 1C ERP HTTP Service",
    "Method: POST",
    "Path: /hs/orders/import",
    "Body: injected JSON",
    "Response mode: proxy_response or accepted_event",
    "```",
    "",
    "## Пример бизнес-ошибки 1C",
    "```json",
    "{",
    "  \"success\": false,",
    "  \"error_code\": \"ORDER_NOT_FOUND\",",
    "  \"error_message\": \"Заказ 404 не найден в 1С\"",
    "}",
    "```",
    "",
    "## Timeline",
    "- `incoming.request.xml`: raw XML.",
    "- `xml.parse.result.json`: parsed XML fields.",
    "- `odata.contractor.request.json`: INN filter.",
    "- `odata.contractor.response.json`: contractor `Ref_Key`.",
    "- `target.request.json`: body with injected `contractor_uuid`.",
    "- `target.response.json`: 1C HTTP service response.",
    "",
    "## Связанные страницы",
    "- [XML Tools](/docs/onec/tools/xml-tools)",
    "- [Ищем контрагента по ИНН](/docs/onec/academy/find-contractor-by-inn)",
    "- [Диагностика: контрагент не найден](/docs/onec/troubleshooting/contractor-not-found-by-inn)"
  )),
  page("recipes", "recipe-05-onec-print-request-to-zebra", "Рецепт 5. 1C отправляет запрос печати на Zebra", "Принять JSON из 1C, создать print job, сохранить ZPL artifact и диагностировать printer errors.", 50, mdLines(
    "# Рецепт 5. 1C отправляет запрос печати на Zebra",
    "",
    "## Когда использовать",
    "1C должна печатать этикетку на Zebra, но принтеры, retry, ZPL artifacts и сетевые ошибки должны быть видны в OMH, а не спрятаны в коде обработки 1C.",
    "",
    "## Endpoint",
    "```text",
    "POST http://omh-server:8000/api/bus/in/onec-print-label",
    "Content-Type: application/json",
    "X-OMH-Token: <static inbound token>",
    "```",
    "",
    "[SCREENSHOT: Recipe 5 Zebra print job timeline]",
    "",
    "## JSON payload",
    "```json",
    "{",
    "  \"request_id\": \"PRINT-2026-0001\",",
    "  \"printer\": \"Zebra-01\",",
    "  \"label_template\": \"sscc-small\",",
    "  \"copies\": 1,",
    "  \"fields\": {",
    "    \"product_name\": \"Плата ABC\",",
    "    \"gtin\": \"04646151697384\",",
    "    \"sscc\": \"04646151697384000001\"",
    "  }",
    "}",
    "```",
    "",
    "## Коннектор принтера",
    "```text",
    "Connector: Zebra-01",
    "Protocol: TCP raw socket",
    "Host: 192.168.1.50",
    "Port: 9100",
    "Timeout: 5 seconds",
    "Duplicate guard: request_id",
    "```",
    "",
    "## Print job",
    "```json",
    "{",
    "  \"print_job_id\": \"print-job-uuid\",",
    "  \"status\": \"queued\",",
    "  \"printer\": \"Zebra-01\",",
    "  \"copies\": 1,",
    "  \"timeline_url\": \"/events/event-uuid\"",
    "}",
    "```",
    "",
    "## ZPL artifact",
    "```text",
    "^XA",
    "^FO40,40^A0N,30,30^FDПлата ABC^FS",
    "^FO40,90^BY2^BCN,90,Y,N,N^FD04646151697384000001^FS",
    "^XZ",
    "```",
    "",
    "## Ответ для 1C",
    "```json",
    "{",
    "  \"accepted\": true,",
    "  \"event_id\": \"event-uuid\",",
    "  \"print_job_id\": \"print-job-uuid\"",
    "}",
    "```",
    "",
    "## Ошибки принтера",
    "```text",
    "Connection refused 192.168.1.50:9100",
    "```",
    "",
    "If you see this, do not blindly replay until you know whether the printer received the job. Check print job state, printer network and duplicate guard by `request_id`.",
    "",
    "## Timeline artifacts",
    "- `incoming.request.json`: print request from 1C.",
    "- `zpl.rendered.txt`: exact ZPL sent to printer.",
    "- `printer.request.json`: printer connector and socket target.",
    "- `printer.response.json`: status or network failure.",
    "- `print_job.json`: queued/sent/failed state.",
    "",
    "## Связанные страницы",
    "- [Printing page](/printing)",
    "- [Диагностика недоступного принтера](/docs/onec/troubleshooting/printer-unavailable)",
    "- [Справочник Timeline](/docs/onec/reference/timeline)"
  )),
  page("recipes", "recipe-06-website-api-query-onec-odata", "Рецепт 6. Сайт/API просит OMH запросить 1C OData", "Внешний сайт вызывает OMH, OMH читает 1C OData и возвращает sync/proxy response.", 60, mdLines(
    "# Рецепт 6. Сайт/API просит OMH запросить 1C OData",
    "",
    "## Когда использовать",
    "Сайту или внешнему API нужно получить данные из 1C, но нельзя давать ему прямой доступ к OData 1C. OMH выступает контролируемым proxy: проверяет token, выполняет OData query и возвращает ограниченный response.",
    "",
    "## Запрос внешнего API",
    "```http",
    "POST /api/bus/in/web-customer-balance",
    "Content-Type: application/json",
    "Authorization: Bearer <website-token>",
    "```",
    "",
    "```json",
    "{",
    "  \"inn\": \"7707083893\",",
    "  \"include_overdue\": true",
    "}",
    "```",
    "",
    "[SCREENSHOT: Recipe 6 website API OData proxy]",
    "",
    "## OData connection",
    "```text",
    "OData connection: OData ERP production",
    "Resource: AccumulationRegister_ВзаиморасчетыСКонтрагентами/Balance",
    "Filter: Контрагент/ИНН eq request.body.inn",
    "Select: Контрагент_Key,СуммаОстаток,Валюта",
    "Top: 20",
    "Save result as: balances",
    "Required: no",
    "```",
    "",
    "## Ответ to website",
    "```json",
    "{",
    "  \"inn\": \"7707083893\",",
    "  \"items\": [",
    "    {",
    "      \"contractor_uuid\": \"contractor-uuid\",",
    "      \"amount\": 12500.00,",
    "      \"currency\": \"RUB\"",
    "    }",
    "  ],",
    "  \"source\": \"1C OData\",",
    "  \"trace_id\": \"event-uuid\"",
    "}",
    "```",
    "",
    "## Режим proxy/sync response",
    "```text",
    "Response mode: sync_response",
    "Reason: website expects data immediately.",
    "Timeout: 10 seconds",
    "If OData is slow: return 504-like controlled response and keep Timeline.",
    "```",
    "",
    "## Timeline artifacts",
    "- `incoming.request.json`: website request.",
    "- `odata.request.json`: exact OData URL and filter.",
    "- `odata.response.json`: original 1C OData response.",
    "- `return_response.json`: compact response returned to website.",
    "",
    "## Частые ошибки",
    "- Website receives empty `items`: OData returned `{ \"value\": [] }` or filter is too narrow.",
    "- Website receives timeout: do not use sync response for heavy reports.",
    "- OData 401: check OData connection credentials, not website token.",
    "",
    "## Связанные страницы",
    "- [OData Explorer](/odata-explorer)",
    "- [Фильтры OData и chaining](/docs/onec/tools/odata-chaining-fields)",
    "- [Диагностика 401 от 1C](/docs/onec/troubleshooting/onec-returned-401)"
  )),
  page("recipes", "recipe-07-wms-shipment-fact-to-onec", "Рецепт 7. WMS отправляет факт отгрузки в 1C", "WMS payload преобразуется в payload 1C HTTP service с business error diagnostics.", 70, mdLines(
    "# Рецепт 7. WMS отправляет факт отгрузки в 1C",
    "",
    "## Когда использовать",
    "WMS сообщает факт отгрузки, а 1C должна получить документ или команду HTTP service. OMH отвечает за mapping, validation, target call и сохранение business error от 1C.",
    "",
    "## WMS payload",
    "```json",
    "{",
    "  \"shipment_id\": \"SHIP-404\",",
    "  \"warehouse\": \"MAIN\",",
    "  \"order_number\": \"SO-1001\",",
    "  \"lines\": [",
    "    { \"sku\": \"ABC-123\", \"qty\": 2, \"serials\": [\"S1\", \"S2\"] }",
    "  ],",
    "  \"shipped_at\": \"2026-07-05T10:30:00+03:00\"",
    "}",
    "```",
    "",
    "[SCREENSHOT: Recipe 7 WMS to 1C mapping]",
    "",
    "## Mapping в payload HTTP-сервиса 1C",
    "| 1C field | Source | Transform |",
    "| --- | --- | --- |",
    "| НомерЗаказа | request.body.order_number | trim |",
    "| Склад | request.body.warehouse | map MAIN -> Основной склад |",
    "| ДатаОтгрузки | request.body.shipped_at | ISO to 1C date |",
    "| Строки[].Артикул | lines[].sku | uppercase trim |",
    "| Строки[].Количество | lines[].qty | number |",
    "| Строки[].СерийныеНомера | lines[].serials | array |",
    "",
    "## Целевой HTTP-сервис 1C",
    "```text",
    "Connector: 1C ERP HTTP Service",
    "Method: POST",
    "Path: /hs/wms/shipment-fact",
    "Body: mapped 1C payload",
    "Response mode: proxy_response for operator action, accepted_event for background import",
    "```",
    "",
    "## Пример бизнес-ошибки 1C",
    "```json",
    "{",
    "  \"success\": false,",
    "  \"error_code\": \"ORDER_NOT_FOUND\",",
    "  \"error_message\": \"Заказ 404 не найден в 1С\"",
    "}",
    "```",
    "",
    "## Timeline",
    "- `incoming.request.json`: WMS payload.",
    "- `validation.result.json`: required fields and line checks.",
    "- `mapping.output.json`: payload for 1C HTTP service.",
    "- `target.request.json`: exact POST to `/hs/wms/shipment-fact`.",
    "- `target.response.json`: 1C business response.",
    "- `external.error` artifact - original 1C business error without simplification.",
    "",
    "## Как исправить частые сбои",
    "1. If order is not found, open 1C and check `order_number` mapping.",
    "2. If warehouse is unknown, update mapping table for WMS warehouse codes.",
    "3. If serials are rejected, compare `mapping.output.json` with 1C service contract.",
    "4. Replay only after data or mapping is fixed.",
    "",
    "## Связанные страницы",
    "- [Mapping editor](/mappings)",
    "- [Диагностика ошибки target API](/docs/onec/troubleshooting/target-api-returned-error)",
    "- [Event перемещён в DLQ](/docs/onec/troubleshooting/event-moved-to-dlq)"
  )),
  page("recipes", "recipe-08-route-by-key-phrase-value", "Рецепт 8. Маршрутизация по ключевому phrase/value", "Business rules выбирают DNP API, printer или controlled failure по pool_type.", 80, mdLines(
    "# Рецепт 8. Маршрутизация по ключевой фразе или значению",
    "",
    "## Когда использовать",
    "Один endpoint принимает разные виды событий из 1C. Например, `pool_type == DNP` должен идти в DNP API, `pool_type == PRINT` должен создавать print job, а неизвестный тип должен завершаться понятной business validation ошибкой.",
    "",
    "## Матрица маршрутизации",
    "```text",
    "If pool_type == DNP   -> DNP API",
    "If pool_type == PRINT -> printer",
    "Else fail",
    "```",
    "",
    "[SCREENSHOT: Recipe 8 business rules route by value]",
    "",
    "## Request JSON",
    "```json",
    "{",
    "  \"pool_id\": \"POOL-001\",",
    "  \"pool_type\": \"PRINT\",",
    "  \"product_code\": \"ABC-123\",",
    "  \"codes\": [\"code1\", \"code2\"],",
    "  \"printer\": \"Zebra-01\"",
    "}",
    "```",
    "",
    "## Бизнес-правила",
    "| Rule | Condition | Action |",
    "| --- | --- | --- |",
    "| send_to_dnp | request.body.pool_type == DNP | call connector DNP Service |",
    "| send_to_printer | request.body.pool_type == PRINT | create print job |",
    "| unsupported_pool_type | otherwise | fail with `UNSUPPORTED_POOL_TYPE` |",
    "",
    "## Целевой JSON для ветки DNP",
    "```json",
    "{",
    "  \"pool_id\": \"POOL-001\",",
    "  \"product_code\": \"ABC-123\",",
    "  \"codes\": [\"code1\", \"code2\"],",
    "  \"source_system\": \"1C\"",
    "}",
    "```",
    "",
    "## Целевой JSON для ветки PRINT",
    "```json",
    "{",
    "  \"request_id\": \"POOL-001\",",
    "  \"printer\": \"Zebra-01\",",
    "  \"template\": \"marking-codes\",",
    "  \"codes\": [\"code1\", \"code2\"]",
    "}",
    "```",
    "",
    "## Ответ на неподдерживаемое значение",
    "```json",
    "{",
    "  \"success\": false,",
    "  \"error_code\": \"UNSUPPORTED_POOL_TYPE\",",
    "  \"message\": \"pool_type must be DNP or PRINT\"",
    "}",
    "```",
    "",
    "## Timeline",
    "- `incoming.request.json`: source value `pool_type`.",
    "- `business_rule.result.json`: matched rule and selected branch.",
    "- `target.request.json` or `printer.request.json`: branch output.",
    "- `target.response.json` or `print_job.json`: branch result.",
    "- `external.error` artifact - only if branch target failed.",
    "",
    "## Частые ошибки",
    "- `pool_type` has spaces or lower case: add trim/uppercase transform before business rules.",
    "- Fallback rule missing: unknown value may silently choose wrong branch.",
    "- DNP branch and PRINT branch reuse one target JSON: split templates by branch.",
    "",
    "## Связанные страницы",
    "- [Business rules](/business-rules)",
    "- [Диагностика остановки business rule](/docs/onec/error-playbooks/business-rule-stopped)",
    "- [Диагностика недоступного принтера](/docs/onec/troubleshooting/printer-unavailable)"
  )),
];

type CaseStudyConfig = {
  slug: string;
  order: number;
  title: string;
  description: string;
  businessGoal: string;
  actors: string[];
  flow: string;
  inbound: string;
  setup: string[];
  odata: string[];
  timeline: string[];
  risks: string[];
  exampleId?: string;
};

function caseStudy(config: CaseStudyConfig): PageSeed {
  return page('case-studies', config.slug, config.title, config.description, config.order, md(`
# ${config.title}

## Бизнес-цель
${config.businessGoal}

## Кто участвует
${config.actors.map((item) => `- ${item}`).join('\n')}

## Схема процесса
\`\`\`text
${config.flow}
\`\`\`

## Входной контракт
\`\`\`json
${config.inbound}
\`\`\`

${config.exampleId ? `::example{exampleId="${config.exampleId}"}` : ''}

## Настройка в OMH
${config.setup.map((item, index) => `${index + 1}. ${item}`).join('\n')}

## OData и 1C детали
${config.odata.map((item) => `- ${item}`).join('\n')}

## Что должно появиться в Timeline
${config.timeline.map((item) => `- ${item}`).join('\n')}

## Риски и как проверить
${config.risks.map((item) => `- ${item}`).join('\n')}

::checklist{id="case-${config.slug}" items="Понятна бизнес-цель|Созданы подключения|Проверен OData/target|Проверен success case|Проверен error case|Timeline читается без разработчика"}
`));
}

export const caseStudyPages: PageSeed[] = [
  caseStudy({
    slug: 'case-01-customer-master-sync', order: 10, title: 'Кейс 1. Синхронизация контрагентов 1C -> CRM/API', description: 'Контрагент создается или меняется в 1C, OMH отправляет нормализованный JSON во внешний API.',
    businessGoal: 'CRM должна получать актуальные данные контрагентов из 1C, но без прямого доступа к базе 1C и без ручной выгрузки файлов.',
    actors: ['1C ERP или УСП как master data source.', 'OMH как endpoint, validator, transformer и observable runtime.', 'CRM/API как target system.'],
    flow: '1C POST customer_changed -> OMH endpoint -> optional OData verification -> Build JSON -> CRM API -> Timeline',
    inbound: '{\n  "event": "customer_changed",\n  "inn": "7707083893",\n  "kpp": "770701001",\n  "name": "ООО Ромашка",\n  "ref_key": "8f1b..."\n}',
    exampleId: 'onec.customer_lookup_by_inn',
    setup: ['Создайте REST connector CRM/API.', 'Создайте OData ERP profile, если нужно дочитать поля контрагента по Ref_Key или INN.', 'Создайте flow source=1C target=REST.', 'Добавьте Validate/Read fields для inn, name, ref_key.', 'Если 1C отправляет только INN, добавьте OData lookup Catalog_Контрагенты.', 'Соберите JSON с явными именами полей CRM.', 'Выберите response_mode accepted_event, если CRM может отвечать долго.'],
    odata: ['Resource: Catalog_Контрагенты.', 'Filter для INN: ИНН eq \'{inn}\'.', 'Filter для Ref_Key: Ref_Key eq guid\'{ref_key}\' если ваша OData публикация требует guid literal.', 'Select: Ref_Key,Description,ИНН,КПП,ЮридическийАдрес.', 'Required lookup включайте только если 1C не присылает полный payload.'],
    timeline: ['incoming.request с исходным payload.', 'validation.result с обязательными полями.', 'odata_query_request.json если был lookup.', 'json_builder_result.json с payload для CRM.', 'target.response с ответом CRM.'],
    risks: ['CRM может требовать idempotency key: используйте ref_key или inn+kpp.', 'INN не уникален для филиалов: добавьте KPP.', 'Если CRM вернула 409 duplicate, это не retry, а бизнес-ошибка mapping/idempotency.']
  }),
  caseStudy({
    slug: 'case-02-product-catalog-to-marketplace', order: 20, title: 'Кейс 2. Номенклатура 1C -> маркетплейс', description: '1C отправляет товар, OMH дополняет данные и отправляет карточку во внешний marketplace API.',
    businessGoal: 'Операторы ведут товар в 1C, а маркетплейс должен получать артикул, название, штрихкод, цену и остаток в своем формате.',
    actors: ['1C ERP/УТ как источник номенклатуры.', 'OData profile для Catalog_Номенклатура и register остатка.', 'Marketplace REST API.'],
    flow: '1C product_changed -> OData product -> OData stock/price -> transform rules -> Marketplace API',
    inbound: '{\n  "article": "A-100",\n  "barcode": "04601234567890",\n  "price_type": "Retail",\n  "warehouse": "MAIN"\n}',
    exampleId: 'onec.product_lookup_by_article',
    setup: ['Создайте OData ERP profile.', 'В OData Explorer проверьте Catalog_Номенклатура по Артикул.', 'Создайте второй lookup для остатка или цены, если они опубликованы отдельным регистром.', 'Добавьте transform: trim article, normalize barcode, convert price to number.', 'Добавьте business rule: не отправлять товар без barcode.', 'Отправьте target payload в marketplace REST connector.'],
    odata: ['Catalog_Номенклатура: Артикул eq \'{article}\'.', 'Для регистров часто нужны Period, Recorder или измерения склада: проверьте metadata.', 'Для цены используйте $top 1 и $orderby Period desc, если OData ресурс поддерживает сортировку.', 'Не делайте широкий запрос без $filter по всему каталогу.'],
    timeline: ['Два OData request: product и stock/price.', 'Business rule decision: publish/skip/fail.', 'Target request содержит marketplace schema.', 'Если barcode пустой, event должен завершиться понятной validation error.'],
    risks: ['Разные базы 1C могут иметь разные имена русских полей.', 'Цена может быть строкой, decimal или объектом: проверьте sample response.', 'Маркетплейс может ограничивать rate limit: используйте queue и retry policy.']
  }),
  caseStudy({
    slug: 'case-03-wms-stock-fact-to-1c', order: 30, title: 'Кейс 3. WMS отправляет остатки в 1C', description: 'WMS/API присылает факт остатка, OMH резолвит SKU/склад и вызывает 1C HTTP service.',
    businessGoal: 'Складская система должна сообщать 1C актуальные остатки без ручной загрузки CSV и без прямой публикации 1C в интернет.',
    actors: ['WMS как source API.', 'OMH resolver/cache.', '1C HTTP service как target.'],
    flow: 'WMS POST stock_balance -> Resolver Product -> Resolver Warehouse -> Build 1C envelope -> 1C HTTP service',
    inbound: '{\n  "sku": "A-100",\n  "warehouse_code": "MAIN",\n  "quantity": 125.5,\n  "moment": "2026-07-05T10:00:00Z"\n}',
    exampleId: 'onec.stock_balance_update',
    setup: ['Создайте endpoint для WMS.', 'Создайте OData profile к 1C для resolver Product by SKU.', 'Создайте resolver Warehouse by code.', 'Добавьте Resolve Business Object steps.', 'Соберите envelope для операции update_stock_balance.', 'Включите accepted_event, если 1C может блокировать документы.'],
    odata: ['Product lookup: Catalog_Номенклатура by Артикул or Код.', 'Warehouse lookup: Catalog_Склады by Код.', 'Cache включайте для справочников, но не для остатков.', 'Если SKU не найден, ошибка должна быть business validation, а не target 500.'],
    timeline: ['resolver.product request/result.', 'resolver.warehouse request/result.', 'target.request к 1C HTTP service.', 'external.error с оригинальной 1C ошибкой при блокировке объекта.'],
    risks: ['Количество может прийти строкой: добавьте transform to_number.', 'WMS может повторить тот же факт: добавьте idempotency key.', '1C может вернуть object locked: это retryable, но 401 auth не retryable.']
  }),
  caseStudy({
    slug: 'case-04-site-order-status-to-1c', order: 40, title: 'Кейс 4. Сайт отправляет статус заказа в 1C', description: 'Сайт присылает paid/shipped/cancelled, OMH нормализует статус и вызывает 1C.',
    businessGoal: 'Интернет-магазин должен обновлять заказ в 1C, но статусы сайта не совпадают один-в-один со статусами 1C.',
    actors: ['Website/API как source.', 'Business Rules в OMH.', '1C HTTP service как target.'],
    flow: 'Website POST order_status -> Normalize status -> Business rule mapping -> 1C HTTP service -> response',
    inbound: '{\n  "external_order_id": "WEB-9001",\n  "status": "paid",\n  "paid_at": "2026-07-05T11:10:00Z",\n  "amount": 12990\n}',
    exampleId: 'onec.order_status_to_1c',
    setup: ['Создайте webhook/API endpoint.', 'Добавьте transform status to lowercase.', 'Добавьте business rules: paid -> Оплачен, shipped -> Отгружен, cancelled -> Отменен.', 'Добавьте target 1C HTTP operation update_order_status.', 'Выберите sync_response, если сайту нужен понятный accepted/rejected JSON.'],
    odata: ['OData не обязателен, если сайт передает внешний номер заказа, известный 1C.', 'Если 1C требует Ref_Key заказа, добавьте OData lookup Document_ЗаказПокупателя по Номер или external_order_id.', 'Проверяйте, как 1C публикует дату и номер документа.'],
    timeline: ['incoming.request от сайта.', 'transform.output normalized_status.', 'business_rule.result с выбранным статусом 1C.', 'target.response 1C.'],
    risks: ['Статус может прийти повторно: target должен быть idempotent.', 'Сайт может отправить unknown status: остановите flow business error, не отправляйте мусор в 1C.', 'Если 1C долго проводит документ, используйте accepted_event.']
  }),
  caseStudy({
    slug: 'case-05-xml-upd-to-api', order: 50, title: 'Кейс 5. XML УПД из 1C -> проверка ИНН -> внешний API', description: 'Старый XML обмен остается, но OMH извлекает ключи, делает OData lookup и отправляет JSON.',
    businessGoal: 'Не переписывать старую XML выгрузку 1C, но подключить новый API, которому нужен JSON и UUID контрагента.',
    actors: ['1C XML sender.', 'XML Tools / Flow XML extraction.', 'OData ERP.', 'External API.'],
    flow: '1C XML -> preserve raw XML -> extract INN/document -> OData customer -> Build JSON -> API',
    inbound: '{\n  "xml": "<Request><INN>7707083893</INN><Document>UPD-1001</Document></Request>"\n}',
    exampleId: 'onec.xml_inn_to_api',
    setup: ['Выберите input_mode XML.', 'Проверьте XML в XML Tools: parse, hash, preview.', 'Добавьте extraction INN и Document.', 'Проверьте OData lookup в Explorer.', 'Соберите JSON для target API и сохраните raw XML artifact.'],
    odata: ['INN извлекается из XML и используется в Catalog_Контрагенты.', 'Если XML содержит namespace, XPath должен учитывать namespace или использовать local-name.', 'Raw XML artifact нужен для доказательства, что тело не изменено.'],
    timeline: ['incoming.request.xml сохраняет исходный XML.', 'xml.parse.result показывает extracted fields.', 'odata_query_result связывает INN с Ref_Key.', 'target.request показывает JSON, а не XML.'],
    risks: ['Кодировка Windows-1251: проверьте Content-Type и XML declaration.', 'Namespace ломает простой XPath.', 'Нельзя терять raw XML, если обмен юридически значимый.']
  }),
  caseStudy({
    slug: 'case-06-sscc-printing', order: 60, title: 'Кейс 6. Печать SSCC этикеток из 1C', description: '1C отправляет SSCC и параметры паллеты, OMH создает print job и сохраняет trace.',
    businessGoal: 'Оператор 1C нажимает печать, а OMH должен надежно отправить этикетку на нужный принтер и показать, где произошла ошибка.',
    actors: ['1C as print source.', 'Printer Package.', 'Zebra/ZPL printer.'],
    flow: '1C POST print_label -> validate SSCC -> build ZPL variables -> print job -> printer logs',
    inbound: '{\n  "printer_id": "zebra-warehouse-1",\n  "template": "sscc-pallet-v1",\n  "variables": {"sscc": "046012345678901234", "order": "SO-1001"}\n}',
    exampleId: 'onec.printer_sscc_label',
    setup: ['Установите Printer Package.', 'Создайте printer в Printing.', 'Создайте flow source=1C target=printer.', 'Проверьте ZPL template отдельно.', 'Включите retry только для сетевых ошибок принтера.'],
    odata: ['OData optional: можно дочитать товар, склад или заказ перед печатью.', 'Если этикетка зависит от номенклатуры, добавьте OData product lookup до print step.', 'Не используйте OData для каждого экземпляра этикетки, если данные одинаковые: кешируйте результат в flow variables.'],
    timeline: ['incoming.request с SSCC.', 'validation.result для SSCC length/check.', 'print_job.created.', 'printer.response или printer.error.'],
    risks: ['Неверный printer_id должен быть понятной validation error.', 'Принтер offline retryable, неверный ZPL не retryable.', 'Дубликаты печати опасны: добавьте idempotency key для print request.']
  }),
  caseStudy({
    slug: 'case-07-odata-polling-orders', order: 70, title: 'Кейс 7. OMH опрашивает новые заказы из 1C OData', description: 'Когда 1C не умеет отправлять POST, OMH периодически читает документы и отправляет изменения.',
    businessGoal: 'Получать новые/измененные документы из 1C без доработки 1C HTTP отправки.',
    actors: ['Scheduler/Polling job.', 'OData ERP.', 'Target API или internal flow.'],
    flow: 'Polling schedule -> OData Document_ЗаказПокупателя -> cursor -> per-row event -> target API',
    inbound: '{\n  "resource": "Document_ЗаказПокупателя",\n  "since": "last cursor",\n  "top": 100\n}',
    exampleId: 'onec.odata_polling_delta',
    setup: ['Создайте OData profile.', 'Выберите resource документа.', 'Определите cursor: Date, PostedAt, Ref_Key или custom timestamp.', 'Ограничьте page size.', 'Создавайте отдельное event на каждую запись, чтобы DLQ был точным.'],
    odata: ['Filter: Date gt datetime\'{last_cursor}\' зависит от версии OData.', 'Orderby: Date asc помогает безопасно двигать cursor.', 'Select только нужных полей уменьшает нагрузку.', 'NextLink должен обрабатываться постранично.'],
    timeline: ['polling.run started.', 'odata page request/response.', 'cursor before/after.', 'per-row target event links.'],
    risks: ['Cursor нельзя двигать вперед, пока batch не обработан.', 'Изменения задним числом могут потеряться: используйте overlap window.', 'Большой $top перегружает 1C.']
  }),
  caseStudy({
    slug: 'case-08-multi-base-erp-usp-wms', order: 80, title: 'Кейс 8. Один flow, несколько баз: ERP, УСП и WMS', description: 'Flow выбирает разные OData profiles для разных lookup и не смешивает credentials.',
    businessGoal: 'Интеграция должна брать контрагента из ERP, маркировку из УСП, складской остаток из WMS и отправлять единый JSON.',
    actors: ['OData ERP.', 'OData УСП.', 'OData WMS.', 'Target API.'],
    flow: '1C/API request -> OData ERP customer -> OData УСП marking -> OData WMS stock -> Build JSON -> API',
    inbound: '{\n  "inn": "7707083893",\n  "gtin": "04601234567890",\n  "warehouse": "MAIN"\n}',
    setup: ['Создайте три OData profiles с понятными именами.', 'В Explorer проверьте каждый profile отдельно.', 'В Builder добавьте три OData steps с разными save_as.', 'В Build JSON явно укажите источник каждого поля.', 'Для каждого profile задайте timeout и max_pages отдельно.'],
    odata: ['ERP: Catalog_Контрагенты by INN.', 'УСП: register или catalog marking by GTIN.', 'WMS: stock balance by warehouse and product.', 'Не используйте один generic connector с переключаемым base_url внутри flow.'],
    timeline: ['Три lookup request с разными connection names.', 'Каждый response artifact показывает свою базу.', 'Target JSON содержит customer_uuid, marking_status, stock_qty.'],
    risks: ['Одинаковые resource names в разных базах не означают одинаковые поля.', 'Credentials разных баз нельзя хранить в одном секрете.', 'Если одна база недоступна, решите: fail whole flow или partial response.']
  }),
  caseStudy({
    slug: 'case-09-return-document-number-sync', order: 90, title: 'Кейс 9. 1C ждет номер документа от внешнего API', description: 'Синхронный сценарий, где 1C не просто отправляет событие, а получает business response.',
    businessGoal: 'Пользователь в 1C нажимает кнопку и должен сразу увидеть номер заявки/операции, созданной во внешней системе.',
    actors: ['1C user form.', 'OMH flow with proxy_response.', 'External API.'],
    flow: '1C button -> OMH endpoint -> OData validation -> target API -> proxy_response to 1C',
    inbound: '{\n  "document": "SO-1001",\n  "inn": "7707083893",\n  "amount": 12990\n}',
    setup: ['Выберите response_mode proxy_response.', 'Установите короткий timeout target API.', 'Сделайте OData validation до target call.', 'В 1C коде обработайте non-2xx и покажите пользователю понятную ошибку.', 'Для долгих операций не используйте этот кейс, используйте accepted_event.'],
    odata: ['OData lookup должен быть быстрым: $top 1, $select минимум полей.', 'Если lookup пустой, верните 4xx/business error, не вызывайте target.', 'Сохраните target response artifact полностью.'],
    timeline: ['incoming.request.', 'odata validation.', 'target.request.', 'target.response с номером документа.', 'return_response artifact.'],
    risks: ['Пользовательская форма 1C не должна зависать из-за долгого target.', 'Target timeout не всегда означает, что операция не создана: нужен idempotency key.', 'Повторный POST из 1C должен быть безопасным.']
  }),
  caseStudy({
    slug: 'case-10-production-incident-replay', order: 100, title: 'Кейс 10. Production incident: исправили данные и повторили событие', description: 'Практический сценарий поддержки: failed event, диагностика, fix, replay, audit.',
    businessGoal: 'Поддержка должна восстановить интеграцию без прямой правки БД и без потери исходной ошибки.',
    actors: ['Support engineer.', 'Timeline/Artifacts.', 'DLQ/Replay.', 'Config Versions/Audit.'],
    flow: 'Failed event -> Timeline -> identify root cause -> fix data/config -> replay -> completed -> audit record',
    inbound: '{\n  "event_id": "failed-event-id",\n  "symptom": "Required OData lookup returned empty"\n}',
    exampleId: 'onec.error_missing_contractor',
    setup: ['Откройте failed event.', 'Скачайте или просмотрите artifacts.', 'Определите, ошибка в данных, credentials, resource или target.', 'Исправьте источник: 1C справочник, OData profile или flow config.', 'Сделайте replay/retry.', 'Проверьте новый run и audit log.'],
    odata: ['Если lookup empty, сначала повторите filter в OData Explorer.', 'Если 401, проверьте OData profile credentials.', 'Если 404, проверьте resource name и публикацию OData в 1C.', 'Если timeout, уменьшите $select/$top или проверьте индекс/фильтр.'],
    timeline: ['Старый run остается failed.', 'Новый run имеет mode replay или retry.', 'Artifacts показывают разницу результата.', 'Audit log фиксирует config/data action если было изменение.'],
    risks: ['Не нажимайте retry много раз на deterministic mapping error.', 'Не удаляйте DLQ до root cause.', 'Не правьте payload так, чтобы потерять исходные данные.']
  }),
];

type RequestExampleConfig = {
  slug: string;
  order: number;
  title: string;
  description: string;
  endpoint: string;
  headers: string;
  body: string;
  onecCode?: string;
  odataFilter?: string;
  exampleId?: string;
  notes: string[];
};

function requestExample(config: RequestExampleConfig): PageSeed {
  return page('request-examples', config.slug, config.title, config.description, config.order, md(`
# ${config.title}

## Endpoint
\`\`\`text
${config.endpoint}
\`\`\`

## Headers
\`\`\`text
${config.headers}
\`\`\`

## Body
\`\`\`json
${config.body}
\`\`\`

${config.exampleId ? `::example{exampleId="${config.exampleId}"}` : ''}

${config.odataFilter ? `## OData filter или lookup\n\`\`\`text\n${config.odataFilter}\n\`\`\`` : ''}

${config.onecCode ? `## 1C код отправки\n\`\`\`1c\n${config.onecCode}\n\`\`\`` : ''}

## На что обратить внимание
${config.notes.map((item) => `- ${item}`).join('\n')}

::checklist{id="request-${config.slug}" items="Скопировал endpoint|Проверил headers|Отправил body|Открыл Timeline|Сравнил expected response"}
`));
}

const basicOneCPost = `HTTP = Новый HTTPСоединение("omh.example.local", 443,,,, Новый ЗащищенноеСоединениеOpenSSL);
Запрос = Новый HTTPЗапрос("/api/bus/in/<endpoint-slug>");
Запрос.Заголовки.Вставить("Content-Type", "application/json");
Запрос.Заголовки.Вставить("X-OMH-Token", "<token>");
Запрос.УстановитьТелоИзСтроки(ТелоЗапроса, КодировкаТекста.UTF8);
Ответ = HTTP.ОтправитьДляОбработки(Запрос);
Если Ответ.КодСостояния >= 300 Тогда
  ВызватьИсключение Ответ.ПолучитьТелоКакСтроку();
КонецЕсли;`;

export const requestExamplePages: PageSeed[] = [
  requestExample({ slug: 'request-01-customer-lookup', order: 10, title: 'Запрос 1. Проверить контрагента по ИНН', description: 'Минимальный POST, который учит искать контрагента и читать lookup artifacts.', endpoint: 'POST /api/bus/in/onec-customer-lookup', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "inn": "7707083893",\n  "source_document": "Order SO-1001"\n}', onecCode: basicOneCPost, odataFilter: 'Resource: Catalog_Контрагенты\n$filter: ИНН eq \'7707083893\'\n$select: Ref_Key,Description,ИНН', exampleId: 'onec.customer_lookup_by_inn', notes: ['Если lookup empty, откройте тот же фильтр в OData Explorer.', 'Если INN хранится без лидирующих нулей, нормализуйте значение transform step.', 'Для филиалов добавьте KPP.'] }),
  requestExample({ slug: 'request-02-product-lookup', order: 20, title: 'Запрос 2. Проверить номенклатуру по артикулу', description: 'Payload для поиска товара и передачи product_uuid в следующий step.', endpoint: 'POST /api/bus/in/onec-product-lookup', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "article": "A-100",\n  "barcode": "04601234567890",\n  "warehouse": "MAIN"\n}', odataFilter: 'Resource: Catalog_Номенклатура\n$filter: Артикул eq \'A-100\'\n$select: Ref_Key,Description,Артикул', exampleId: 'onec.product_lookup_by_article', notes: ['Артикул может называться Article, Артикул или Код в разных публикациях.', 'Проверяйте $select по metadata, а не по памяти.', 'Barcode лучше нормализовать до строки.'] }),
  requestExample({ slug: 'request-03-two-lookups-order', order: 30, title: 'Запрос 3. Заказ с двумя lookup: контрагент и товар', description: 'Основной пример для 1C POST -> OData -> JSON -> endpoint.', endpoint: 'POST /api/bus/in/onec-enrich-order', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "inn": "7707083893",\n  "product_code": "A-100",\n  "quantity": 12,\n  "external_order_id": "SO-1001"\n}', odataFilter: 'Lookup 1: Catalog_Контрагенты by ИНН\nLookup 2: Catalog_Номенклатура by Артикул or Код', exampleId: 'onec.two_odata_to_json_endpoint', notes: ['У lookup должны быть разные save_as: contractor и product.', 'Required включайте на обоих, если target API не принимает null.', 'В Timeline должно быть два odata_query_request.json.'] }),
  requestExample({ slug: 'request-04-xml-inn', order: 40, title: 'Запрос 4. XML с INN и номером документа', description: 'Пример для старого XML обмена и нового JSON target.', endpoint: 'POST /api/bus/in/onec-xml-inn-to-api', headers: 'Content-Type: application/xml\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "body_text": "<Request><INN>7707083893</INN><Document>UPD-1001</Document></Request>"\n}', odataFilter: 'Extract INN from XML -> Catalog_Контрагенты by ИНН', exampleId: 'onec.xml_inn_to_api', notes: ['Для XML в Test Console используйте body_text/input_mode xml.', 'Raw XML artifact должен сохраниться до parse step.', 'Namespace в XML проверяйте отдельно.'] }),
  requestExample({ slug: 'request-05-wms-stock', order: 50, title: 'Запрос 5. WMS отправляет остаток в 1C', description: 'Внешний складской факт, resolver и вызов 1C HTTP service.', endpoint: 'POST /api/bus/in/wms-stock-balance-to-1c', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: wms', body: '{\n  "sku": "A-100",\n  "warehouse_code": "MAIN",\n  "quantity": 125.5,\n  "moment": "2026-07-05T10:00:00Z"\n}', exampleId: 'onec.stock_balance_update', notes: ['Этот запрос не из 1C, но target — 1C.', 'Resolver errors должны быть отделены от 1C target errors.', 'Количество приводите к number до target call.'] }),
  requestExample({ slug: 'request-06-site-status', order: 60, title: 'Запрос 6. Сайт отправляет статус заказа', description: 'Website/API -> OMH -> 1C HTTP service.', endpoint: 'POST /api/bus/in/site-order-status-to-1c', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: site', body: '{\n  "external_order_id": "WEB-9001",\n  "status": "paid",\n  "paid_at": "2026-07-05T11:10:00Z",\n  "amount": 12990\n}', exampleId: 'onec.order_status_to_1c', notes: ['Business rules должны явно маппить paid/shipped/cancelled.', 'Unknown status лучше остановить бизнес-ошибкой.', 'Для сайта часто удобен sync_response с event_id.'] }),
  requestExample({ slug: 'request-07-print-sscc', order: 70, title: 'Запрос 7. Печать SSCC этикетки', description: '1C отправляет задание печати на Printer Package.', endpoint: 'POST /api/bus/in/onec-print-sscc-label', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "printer_id": "zebra-warehouse-1",\n  "template": "sscc-pallet-v1",\n  "variables": {\n    "sscc": "046012345678901234",\n    "order": "SO-1001",\n    "pallet": "PAL-07"\n  }\n}', exampleId: 'onec.printer_sscc_label', notes: ['Проверяйте printer_id до генерации ZPL.', 'Повторный запрос может напечатать дубль: добавьте idempotency key.', 'Printer offline retryable, invalid ZPL не retryable.'] }),
  requestExample({ slug: 'request-08-negative-missing-contractor', order: 80, title: 'Запрос 8. Негативный тест: контрагент не найден', description: 'Проверка Required lookup, ошибки и DLQ/replay.', endpoint: 'POST /api/bus/in/onec-customer-lookup', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "inn": "0000000000",\n  "source_document": "Bad document"\n}', odataFilter: 'Catalog_Контрагенты where ИНН eq \'0000000000\' -> expected empty', exampleId: 'onec.error_missing_contractor', notes: ['Это не success path, он нужен для проверки понятной ошибки.', 'Expected failure: ODATA_RESULT_EMPTY или business validation.', 'После добавления контрагента можно replay.'] }),
];

type ErrorPlaybookConfig = {
  slug: string;
  order: number;
  title: string;
  description: string;
  symptom: string;
  likelyCauses: string[];
  whereToLook: string[];
  fix: string[];
  prevent: string[];
};

function errorPlaybook(config: ErrorPlaybookConfig): PageSeed {
  return page('error-playbooks', config.slug, config.title, config.description, config.order, md(`
# ${config.title}

## Симптом
${config.symptom}

## Вероятные причины
${config.likelyCauses.map((item) => `- ${item}`).join('\n')}

## Где смотреть в OMH
${config.whereToLook.map((item) => `- ${item}`).join('\n')}

## Как исправить
${config.fix.map((item, index) => `${index + 1}. ${item}`).join('\n')}

## Как предотвратить
${config.prevent.map((item) => `- ${item}`).join('\n')}

::checklist{id="playbook-${config.slug}" items="Нашел failed event|Открыл artifacts|Понял root cause|Исправил data/config|Сделал retry/replay|Проверил новый run"}
`));
}

export const errorPlaybookPages: PageSeed[] = [
  errorPlaybook({ slug: 'odata-401-auth', order: 10, title: 'Playbook 1. OData вернула 401 Unauthorized', description: 'Что делать, если OData profile не проходит auth.', symptom: 'Test $metadata или OData step возвращает 401, а входной запрос в OMH при этом принят.', likelyCauses: ['Неверный username/password в OData Connection.', 'Secret не создан в текущем окружении.', 'Пользователь 1C не имеет прав на OData publication.', 'Перепутали inbound token и OData credentials.'], whereToLook: ['OData Connections -> selected profile -> Test $metadata.', 'Timeline -> odata_query_response.json.', 'Secrets Store -> secret exists and enabled.', 'Audit log -> кто менял profile.'], fix: ['Проверьте логин/пароль в 1C вручную.', 'Если используется $secret, убедитесь, что secret существует в этом environment.', 'Обновите OData profile и повторите Test $metadata.', 'Повторите failed event только после успешного metadata test.'], prevent: ['Используйте named secrets per environment.', 'Не храните production пароль в description.', 'Добавьте healthcheck OData profile в production checklist.'] }),
  errorPlaybook({ slug: 'odata-404-resource', order: 20, title: 'Playbook 2. OData resource не найден', description: '404/invalid resource при запросе Catalog или Document.', symptom: 'OData step падает с 404 или ONEC_ODATA_ERROR, хотя connection metadata работает.', likelyCauses: ['Ресурс называется иначе в этой базе.', 'Объект не опубликован в OData 1C.', 'Использовано русское имя справочника вместо technical OData name.', 'Base URL указывает не на ту информационную базу.'], whereToLook: ['OData Explorer resources list.', 'Timeline -> odata_query_request.json url/resource.', '1C publication settings.', 'OData profile base_url.'], fix: ['Откройте OData Explorer и загрузите resources.', 'Выберите ресурс из списка, не набирайте по памяти.', 'Проверьте публикацию OData в 1C.', 'Обновите flow step resource и сохраните draft/publish.'], prevent: ['В docs flow фиксируйте exact resource name.', 'Добавляйте screenshots/resources examples для клиента.', 'Проверяйте resource после обновления 1C конфигурации.'] }),
  errorPlaybook({ slug: 'odata-empty-required', order: 30, title: 'Playbook 3. Required OData lookup пустой', description: 'Lookup не нашел строку и flow остановился.', symptom: 'Timeline показывает ODATA_RESULT_EMPTY или бизнес-ошибку “required lookup returned no rows”.', likelyCauses: ['Неверный field/operator/value source.', 'Входное значение не нормализовано: пробелы, регистр, лидирующие нули.', 'Данные еще не заведены в 1C.', 'Фильтр требует KPP/warehouse/date, а передан только INN/SKU.'], whereToLook: ['Timeline -> odata_query_request.json.', 'Timeline -> incoming.request.', 'OData Explorer с тем же filter.', 'Transform output до lookup.'], fix: ['Скопируйте filter из artifact в OData Explorer.', 'Проверьте фактическое значение из incoming.request.', 'Добавьте transform trim/remove_spaces/normalize.', 'Если данные отсутствуют, заведите их в 1C и сделайте replay.'], prevent: ['Проверяйте negative examples до production.', 'Документируйте required fields.', 'Для неоднозначных ключей используйте resolver вместо прямого lookup.'] }),
  errorPlaybook({ slug: 'target-timeout', order: 40, title: 'Playbook 4. Target API timeout', description: 'Что делать, если внешний API или 1C HTTP service не отвечает вовремя.', symptom: 'Flow падает по timeout на target call или 1C форма ждет слишком долго.', likelyCauses: ['Target API медленный или недоступен.', 'Слишком короткий timeout.', 'Сценарий должен быть async, но выбран proxy_response.', '1C проводит документ синхронно и блокирует объект.'], whereToLook: ['Timeline -> target.request.', 'External error record.', 'Connector timeout_seconds.', 'Response mode flow.'], fix: ['Проверьте target доступность вне OMH.', 'Если операция долгая, смените response_mode на accepted_event.', 'Настройте retry policy для timeout/5xx.', 'Не retry 4xx validation errors.'], prevent: ['Для user-facing 1C кнопок держите короткий timeout.', 'Для фоновых операций используйте queue.', 'Согласуйте SLA target API.'] }),
  errorPlaybook({ slug: 'xml-parse-failed', order: 50, title: 'Playbook 5. XML не парсится или потерялась кодировка', description: 'Ошибки XML input, namespace и encoding.', symptom: 'XML Tools или flow parse step показывает invalid XML, пустые поля или кракозябры.', likelyCauses: ['Content-Type не application/xml.', 'Кодировка body не совпадает с XML declaration.', 'XML namespace не учтен в path.', '1C отправила не XML, а строку с escaped XML.'], whereToLook: ['incoming.request raw text.', 'XML Tools parse/hash.', 'Headers artifact.', 'xml.parse.result.'], fix: ['Сохраните raw body и проверьте encoding.', 'Проверьте Content-Type и XML declaration.', 'Для namespace используйте корректный XPath или local-name.', 'Если XML escaped внутри JSON, сначала извлеките строку.'], prevent: ['Всегда храните raw XML artifact.', 'Добавьте XML negative test.', 'Документируйте пример XML из реальной 1C.'] }),
  errorPlaybook({ slug: 'business-rule-stopped', order: 60, title: 'Playbook 6. Business rule остановил событие', description: 'Событие не дошло до target из-за правила.', symptom: 'Flow завершился как failed/skipped на evaluate_rules step.', likelyCauses: ['Статус/source value не входит в разрешенный список.', 'Правило настроено как fail вместо skip.', 'Поле до rule не было прочитано или трансформировано.', 'Порядок правил приводит к первому неверному match.'], whereToLook: ['Timeline -> business_rule result.', 'Rule set page.', 'Transform output до rule.', 'Sample request в builder preview.'], fix: ['Проверьте входное значение.', 'Прогоните rule set test.', 'Исправьте порядок правил.', 'Опубликуйте config version и replay событие.'], prevent: ['Пишите explicit fallback rule.', 'Добавляйте examples на каждый статус.', 'Не меняйте rule set без preview.'] }),
  errorPlaybook({ slug: 'duplicate-events', order: 70, title: 'Playbook 7. Дубликаты событий или повторная печать', description: 'Как разбирать repeated POST, retry и idempotency.', symptom: 'Target получает повторный заказ, документ или print job.', likelyCauses: ['1C повторила POST после timeout.', 'Нет idempotency key.', 'Retry настроен на ошибку, которая фактически создала объект.', 'Печать не защищена от дублей.'], whereToLook: ['Event Journal by correlation_id.', 'incoming.request idempotency fields.', 'target.response before timeout.', 'Print job list.'], fix: ['Добавьте idempotency key из source document/ref_key.', 'Проверьте target before retry.', 'Для print добавьте request_id и duplicate guard.', 'Не делайте blind replay, если target мог принять запрос.'], prevent: ['Документируйте idempotency key в каждом endpoint contract.', 'Для sync operations используйте external_order_id.', 'Для печати явно подтверждайте reprint.'] }),
  errorPlaybook({ slug: 'secret-missing-env', order: 80, title: 'Playbook 8. Secret есть в dev, но отсутствует в production', description: 'Config перенесли, а пароль не подставляется.', symptom: 'После promotion flow/profile падает auth/config validation, хотя в dev все работало.', likelyCauses: ['Secret reference перенесен без значения secret.', 'В production другое имя secret.', 'Auth package/Secrets package disabled.', 'Нет прав на чтение secret.'], whereToLook: ['Secrets page production environment.', 'Config version diff.', 'OData profile masked config.', 'Production doctor/checklist.'], fix: ['Создайте secret с тем же именем в production.', 'Повторите Test $metadata/connector healthcheck.', 'Запустите failed event replay.', 'Обновите release checklist.'], prevent: ['Используйте одинаковые secret names между окружениями.', 'Перед deploy запускайте production checklist.', 'Не называйте secrets вручную по-разному.'] }),
  errorPlaybook({ slug: 'wrong-response-mode', order: 90, title: 'Playbook 9. Неверный response mode', description: '1C ждет ответ, но получила event id, или наоборот.', symptom: 'Пользователь 1C не видит номер документа, либо форма висит до timeout.', likelyCauses: ['Для синхронной операции выбран accepted_event.', 'Для долгой операции выбран proxy_response.', '1C код не обрабатывает 202.', 'Target response не маппится в return_response.'], whereToLook: ['Flow input.response_mode.', 'Test Console response.', '1C HTTP code.', 'Timeline return_response artifact.'], fix: ['Определите, нужен ли бизнес-ответ сразу.', 'Для quick target выберите proxy_response/sync_response.', 'Для long-running выберите accepted_event.', 'Обновите 1C code handling 200/202/4xx.'], prevent: ['Фиксируйте response contract в docs flow.', 'Проверяйте 1C код не только happy path.', 'Не используйте proxy_response для нестабильного target.'] }),
  errorPlaybook({ slug: 'flow-config-drift', order: 100, title: 'Playbook 10. Flow config drift после ручных изменений', description: 'Почему вчера работало, а сегодня OData step выбирает не тот profile.', symptom: 'После изменений flow начал ходить в другую базу или собирать другой JSON.', likelyCauses: ['Опубликован draft без проверки diff.', 'Изменен OData profile name, а flow хранит connection name.', 'Rollback вернул старый builder JSON.', 'Change set применен не в то environment.'], whereToLook: ['Config History flow.', 'Audit log object integration_flow.', 'OData Connections updated_at.', 'Change Sets.'], fix: ['Откройте diff последней версии.', 'Проверьте connection_id/connection в OData step.', 'Если нужно, rollback на рабочую версию.', 'Повторите preview и replay тестового события.'], prevent: ['Пишите publish comments.', 'Не переименовывайте profiles без проверки flow.', 'Держите smoke examples на критичные routes.'] }),
];

export const decisionPages: PageSeed[] = [
  page('decisions', 'how-to-choose-input-mode', 'Как выбрать input mode', 'JSON, XML или raw text для входящего запроса 1C.', 10, md(`
# Как выбрать input mode

## JSON
Выбирайте JSON, если вы можете изменить код 1C и отправлять структурированный объект. Это лучший вариант для новых интеграций: проще тестировать, проще писать templates, проще читать Timeline.

## XML
Выбирайте XML, если конфигурация 1C уже отдает XML, есть XDTO или старый обмен, который нельзя быстро переписать. В этом режиме важно сразу проверить encoding и XPath/field extraction.

## Raw text
Выбирайте raw text только для специфичных форматов: готовый ZPL, CSV, фиксированная строка или legacy payload. Для бизнес-интеграций raw text хуже диагностируется.

## Практическое правило
- Новый проект: JSON.
- Старый обмен 1C: XML.
- Печать или legacy формат: raw text.
- Если сомневаетесь, выбирайте JSON и документируйте schema.

::checklist{id="decision-input-mode" items="Понял формат источника|Проверил encoding|Выбрал JSON/XML/raw|Создал sample request"}
`)),
  page('decisions', 'how-to-choose-response-mode', 'Как выбрать response mode', 'Proxy response, accepted event или sync response.', 20, md(`
# Как выбрать response mode

## proxy_response
Используйте, когда 1C должна получить ответ внешней системы сразу: номер созданной заявки, статус проверки, результат синхронной операции.

## accepted_event
Используйте, когда операция может быть долгой или нестабильной. 1C получает event id, а обработка идет через очередь, retry и DLQ.

## sync_response
Используйте, когда OMH сам собирает компактный ответ: validation result, найденный объект, вычисленный статус.

## Матрица выбора
| Условие | Режим |
| --- | --- |
| Нужен ответ target API сейчас | proxy_response |
| Операция долгая | accepted_event |
| Нужно вернуть свой JSON | sync_response |
| Target может падать, но событие нельзя потерять | accepted_event |

::checklist{id="decision-response-mode" items="Понял ожидание 1C|Оценил длительность target|Выбрал режим|Проверил HTTP status"}
`)),
  page('decisions', 'odata-lookup-vs-resolver', 'OData lookup или Resolver', 'Когда использовать прямой OData step, а когда бизнес-объект resolver.', 30, md(`
# OData lookup или Resolver

## OData lookup
Используйте OData lookup, когда нужно один раз прочитать ресурс в конкретном flow: найти контрагента по ИНН, товар по артикулу, документ по номеру.

## Resolver
Используйте Resolver, когда один и тот же бизнес-объект нужен во многих flow, нужна cache, есть несколько источников или нужно централизованно описать правило поиска.

## Примеры
- Один flow ищет Catalog_Контрагенты по ИНН: OData lookup.
- Десять flow ищут Product по SKU и GTIN: Resolver.
- Нужно fallback: сначала ERP, потом WMS: Resolver.
- Нужно быстро проверить ресурс: OData Explorer и OData lookup.

::checklist{id="decision-lookup-resolver" items="Оценил повторяемость поиска|Понял нужен ли cache|Выбрал lookup или resolver|Проверил результат в Timeline"}
`)),
  page('decisions', 'flow-vs-workflow', 'Flow или Workflow', 'Когда внедренцу достаточно Visual Flow Builder, а когда нужен low-level workflow.', 40, md(`
# Flow или Workflow

## Integration Flow
Это основной путь для внедренца. Используйте его для endpoint, matchers, OData lookup, transformations, business rules, target call и response. Он понятнее, версионируется и лучше подходит для документации клиента.

## Workflow
Workflow нужен разработчику, когда требуется низкоуровневый runtime control, кастомные шаги или сложная оркестрация, которую пока нельзя выразить в Visual Flow Builder.

## Практическое правило
- Можно собрать из блоков: Flow.
- Нужен кастомный execution step: Workflow.
- Нужно объяснить клиенту и поддержке: Flow.
- Нужно расширять SDK: Workflow.

::checklist{id="decision-flow-workflow" items="Попробовал собрать через Flow|Понял ограничение|Выбрал Flow или Workflow|Описал решение в docs"}
`)),
];
