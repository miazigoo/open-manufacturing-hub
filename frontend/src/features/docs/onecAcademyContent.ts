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

::lesson-page{label="1C Integration Academy"}

::concept-callout{title="Golden Scenario" body="${goldenScenarioIntro.replace(/"/g, '&quot;').replace(/\n/g, ' ')}"}

## What you will build
${config.build}

## Why this matters
${config.why}

## Before you start
${config.before.map((item) => `- ${item}`).join('\n')}

## Step-by-step
${config.steps.map((item, index) => `${index + 1}. ${item}`).join('\n')}

## Example values
${config.example}

## What should happen
::expected-result{items="${config.expected.join('|')}"}

## Check yourself
::checklist{id="${config.slug}" items="${config.checklist.join('|')}"}

## Common mistakes
::common-mistakes{items="${config.mistakes.join('|')}"}

## Next lesson
${nextBlock}
`));
}

const defaultBefore = [
  'Пакет 1C установлен и enabled в Plugin Store.',
  'Вы открыли веб-интерфейс OMH и можете перейти в OData Connections, OData Explorer, Integration Flows, Test Console и Event Timeline.',
  'Для OData уроков опубликован OData сервис 1C и известен URL вида http://server/base/odata/standard.odata.',
];

export const academyPackAPages: PageSeed[] = [
  page('academy', 'create-odata-connection', 'Create OData Connection', 'Подробный урок: создать OData ERP connection, понять поля формы, secrets и healthcheck.', 21, mdLines(
    '# Create OData Connection',
    '',
    '::lesson-page{label="Lesson Pack A · OData basics"}',
    '',
    '## What you will build',
    'Вы создадите OData Connection `OData ERP`. Это сохраненное подключение к конкретной базе 1C, через которое OMH будет читать контрагентов, товары и документы.',
    '',
    '## Why this matters',
    'OData connection is a saved connection to a concrete 1C base.',
    '',
    'OData Connection — это не generic Connector. Generic Connector может описывать REST API, принтер или другой внешний сервис. OData Connection всегда отвечает на вопрос: **в какую базу 1C OMH идет за данными**. В Golden Scenario OMH выбирает `OData ERP`, ищет контрагента по ИНН, потом ищет товар по артикулу.',
    '',
    '## Before you start',
    '- Пакет 1C установлен и enabled.',
    '- Администратор 1C опубликовал OData: обычно URL заканчивается на `/odata/standard.odata`.',
    '- У вас есть пользователь 1C для обмена, например `exchange_user`.',
    '- Если это production, пароль уже создан в Secrets Store.',
    '',
    '## Where to click',
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
    '## Field table',
    '| Field | Example | Meaning | Where to get |',
    '| --- | --- | --- | --- |',
    '| Name | OData ERP | Человеческое имя подключения, которое потом видно в Explorer и Flow Builder | Вы выбираете сами |',
    '| Base URL | http://1c-server/erp/odata/standard.odata | Адрес публикации 1C OData | 1C admin или web server publication |',
    '| Username | exchange_user | Пользователь 1C, от имени которого OMH читает OData | 1C admin |',
    '| Password | secret | Пароль пользователя 1C или secret reference | Secrets Store / 1C admin |',
    '| Timeout | 20 | Сколько секунд ждать ответа 1C | 20 обычно достаточно для первого теста |',
    '| Verify SSL | false | Проверять HTTPS certificate | false для локального HTTP, true для нормального HTTPS |',
    '',
    '## Example values',
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
    '## What should happen',
    '::expected-result{items="В списке появилась connection OData ERP|Healthcheck/Test $metadata вернул OK или понятную ошибку 1C|Connection можно выбрать в OData Explorer|Пользователь понимает, что это подключение к конкретной базе 1C, а не generic connector"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-a-create-odata-connection" items="Открыл OData Connections|Заполнил Name|Заполнил Base URL с /odata/standard.odata|Указал username|Использовал secret для production password|Нажал Create connection|Нажал Test $metadata"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Wrong base URL: указан адрес web-клиента 1C вместо OData publication|Пропущен хвост /odata/standard.odata|OData в 1C не опубликована|Неверный user/password|Пользователь 1C не имеет прав читать справочники|Создали generic Connector и не понимают, почему его неудобно выбрать в OData Explorer"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Test OData in OData Explorer" href="/docs/onec/academy/test-odata-explorer"}',
  )),
  page('academy', 'test-odata-explorer', 'Test OData in OData Explorer', 'Подробный урок: выбрать OData ERP, загрузить resources и выполнить первый безопасный query.', 31, mdLines(
    '# Test OData in OData Explorer',
    '',
    '::lesson-page{label="Lesson Pack A · OData basics"}',
    '',
    '## What you will build',
    'Вы проверите, что OMH действительно может читать данные из 1C через созданную connection `OData ERP`.',
    '',
    '## Why this matters',
    'Если простой запрос `Catalog_Контрагенты?$top=5` не работает в OData Explorer, не нужно строить pipeline. Сначала чините connection, публикацию OData, права пользователя или имя ресурса.',
    '',
    '## Before you start',
    '- Создана OData Connection `OData ERP`.',
    '- `Test $metadata` возвращает OK.',
    '- В 1C есть хотя бы несколько контрагентов, доступных пользователю `exchange_user`.',
    '',
    '## Step-by-step',
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
    '## Example request',
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
    '## What each field means',
    '| Field | What to enter | Why it is needed |',
    '| --- | --- | --- |',
    '| OData connection | OData ERP | OMH должен знать, из какой 1C базы читать данные |',
    '| Resource | Catalog_Контрагенты | Это техническое имя справочника в OData, не заголовок формы 1C |',
    '| $top | 5 | Безопасный лимит, чтобы не читать весь справочник |',
    '| $select | Ref_Key,Description,ИНН | Вернуть только поля, которые нужны для проверки и будущего lookup |',
    '',
    '## What should happen',
    '::expected-result{items="В Query result видны несколько контрагентов|У каждой строки есть Ref_Key и Description|OMH показывает request и response без скрытого ручного кода|Пользователь понимает: если это работает, OMH может читать данные из 1C"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-a-test-odata-explorer" items="Открыл OData Explorer|Выбрал OData ERP|Загрузил resources|Выбрал Catalog_Контрагенты|Поставил $top=5|Нажал Run query|Увидел несколько контрагентов"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Выбрана не та OData connection, например WMS вместо ERP|Resource введен по памяти и не совпадает с metadata|$top пустой или слишком большой|Пользователь 1C видит metadata, но не имеет прав на сам справочник|Путают Query result с уже настроенным pipeline"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Find Contractor by INN" href="/docs/onec/academy/find-contractor-by-inn"}',
  )),
  page('academy', 'find-contractor-by-inn', 'Find Contractor by INN', 'Подробный урок: найти контрагента по ИНН, понять Ref_Key и подготовить lookup для pipeline.', 41, mdLines(
    '# Find Contractor by INN',
    '',
    '::lesson-page{label="Lesson Pack A · OData basics"}',
    '',
    '## What you will build',
    'Вы выполните конкретный lookup: OMH берет ИНН `7707083893`, отправляет OData filter в `Catalog_Контрагенты` и получает `Ref_Key`, `Description`, `ИНН`.',
    '',
    '## Why this matters',
    'В 1C человек видит контрагента по названию и ИНН, но внутренние операции часто требуют `Ref_Key`. `Ref_Key` — это UUID, которым 1C обычно идентифицирует объект внутри базы. Именно его часто нужно передавать в следующий OData запрос, HTTP-сервис 1C или внешний API.',
    '',
    '## Before you start',
    '- Запрос `Catalog_Контрагенты?$top=5` уже работает.',
    '- Вы знаете точное имя поля ИНН в вашей 1C publication. В типовом учебном примере это `ИНН`.',
    '- В базе есть контрагент с ИНН `7707083893` или вы заменили значение на реальный ИНН из вашей базы.',
    '',
    '## Step-by-step',
    '1. Откройте `OData Explorer`.',
    '2. Выберите `OData ERP`.',
    '3. Resource: `Catalog_Контрагенты`.',
    '4. В filter builder укажите Field: `ИНН`.',
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
    '## Example values',
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
    '## Ref_Key in plain language',
    'Ref_Key — это внутренний UUID объекта 1C.',
    '`Ref_Key` — это внутренний UUID объекта 1C. Название `ООО Ромашка` удобно человеку, но интеграции часто должны работать со стабильным ключом. Если следующий шаг создает документ в 1C или отправляет данные в API, чаще всего ему нужен именно `Ref_Key`, а не только ИНН.',
    '',
    '## What should happen',
    '::expected-result{items="Query result содержит одну строку контрагента|В строке есть Ref_Key, Description и ИНН|Вы понимаете, какой field mapping сохранить для pipeline|Если строка не найдена, ошибка считается понятной бизнес-проверкой, а не поломкой OMH"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-a-find-contractor-by-inn" items="Выбрал OData ERP|Указал Catalog_Контрагенты|Ввел filter по ИНН|Поставил $top=1|Указал $select|Увидел Ref_Key|Понял зачем Ref_Key нужен дальше"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="INN содержит пробелы или невидимые символы|Неверное имя поля: в вашей базе это может быть ИНН, INN или другое metadata name|Выбран wrong catalog или wrong OData base|Контрагент находится в другой 1C базе|OData user не имеет прав видеть справочник|Ищут по Description, хотя в Golden Scenario входной ключ — INN"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Create inbound endpoint for 1C POST" href="/docs/onec/academy/lesson-04-create-inbound-endpoint-for-1c-post"}',
  )),
];

export const academyPackBPages: PageSeed[] = [
  page('academy', 'create-inbound-endpoint', 'Create Inbound Endpoint for 1C POST', 'Создать URL, куда 1C отправляет Golden Scenario payload.', 51, mdLines(
    '# Create Inbound Endpoint for 1C POST',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы создадите inbound endpoint `onec-pool-to-dnp`. Это URL в OMH, куда 1C отправляет POST request с `inn`, `product_code`, `pool_id` и `codes`.',
    '',
    '## Why this matters',
    'Endpoint is the URL where 1C sends request. Без endpoint у 1C нет стабильного адреса, а у OMH нет понятного контракта: какой метод, какой body type, какой response mode и нужна ли защита token.',
    '',
    '## Before you start',
    '- Пакет 1C установлен и enabled.',
    '- Вы понимаете training payload из Start in 15 minutes.',
    '- Для production решено, нужен ли static token.',
    '- Если flow уже существует, откройте его в Integration Flow Builder.',
    '',
    '## Step-by-step',
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
    '## Field table',
    '| Field | Example | Meaning |',
    '| --- | --- | --- |',
    '| Name | 1C pool to DNP | Человеческое имя сценария в UI |',
    '| Slug | onec-pool-to-dnp | Часть URL после `/api/bus/in/` |',
    '| Input mode | JSON | Тип тела request, который 1C отправляет в OMH |',
    '| Response mode | accepted_event | 1C быстро получает event_id, а OMH обрабатывает дальше |',
    '| Auth | static token or none | Защита endpoint от чужих запросов |',
    '',
    '## Example values',
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
    '## What should happen',
    '::expected-result{items="Endpoint появился в списке inbound routes|URL заканчивается на /api/bus/in/onec-pool-to-dnp|Test Console может выбрать этот endpoint|При accepted_event response содержит event_id и timeline_url"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-create-inbound-endpoint" items="Создал endpoint|Указал slug onec-pool-to-dnp|Выбрал JSON input mode|Выбрал accepted_event|Понял token auth|Скопировал endpoint URL"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Путать endpoint slug и flow name|Выбрать XML input mode для JSON payload|Оставить auth none в production|Ждать business response от accepted_event|Не передать Content-Type application/json из 1C"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Read Values from Incoming Request" href="/docs/onec/academy/read-request-fields"}',
  )),
  page('academy', 'read-request-fields', 'Read Values from Incoming Request', 'Прочитать inn, product_code, pool_id и codes из request.body.', 61, mdLines(
    '# Read Values from Incoming Request',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы добавите read-field шаги, чтобы flow получил named values: `inn`, `product_code`, `pool_id`, `codes`.',
    '',
    '## Why this matters',
    'OData query и JSON Builder не должны каждый раз разбирать сырой request. Flow сначала читает значения из `request.body`, дает им понятные имена и только потом использует их в OData filters и target JSON.',
    '',
    '## Before you start',
    '- Endpoint `onec-pool-to-dnp` создан.',
    '- В Visual Flow Builder открыт sample request.',
    '- Вы знаете, что request body является JSON object.',
    '',
    '## Input JSON',
    '```json',
    '{',
    '  "inn": "7707083893",',
    '  "product_code": "ABC-123",',
    '  "pool_id": "POOL-001",',
    '  "codes": ["code1", "code2"]',
    '}',
    '```',
    '',
    '## Step-by-step',
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
    '## Field mapping table',
    '| Value | Path | Example |',
    '| --- | --- | --- |',
    '| INN | request.body.inn | 7707083893 |',
    '| Product code | request.body.product_code | ABC-123 |',
    '| Pool ID | request.body.pool_id | POOL-001 |',
    '| Codes | request.body.codes | ["code1","code2"] |',
    '',
    '## Variables',
    '```text',
    'inn = request.body.inn',
    'product_code = request.body.product_code',
    'pool_id = request.body.pool_id',
    'codes = request.body.codes',
    '```',
    '',
    '## What should happen',
    '::expected-result{items="Preview показывает inn=7707083893|Preview показывает product_code=ABC-123|codes остается массивом, а не строкой|Следующие OData steps могут использовать эти values"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-read-request-fields" items="Вставил sample JSON|Добавил inn path|Добавил product_code path|Добавил pool_id path|Добавил codes path|Проверил Preview variables"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Писать inn вместо request.body.inn|Сохранить product_code как product|Сделать codes строкой вместо array|Не включить required и получить пустой OData filter|Использовать старый sample request без pool_id"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Add First OData Query" href="/docs/onec/academy/first-odata-query-contractor"}',
  )),
  page('academy', 'first-odata-query-contractor', 'Add First OData Query: Contractor by INN', 'Настроить первый OData Query step и сохранить результат как contractor.', 71, mdLines(
    '# Add First OData Query: Contractor by INN',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы добавите OData query #1: OMH берет `request.body.inn`, ищет контрагента в `Catalog_Контрагенты` и сохраняет найденную строку как `contractor`.',
    '',
    '## Why this matters',
    '`Save result as` превращает ответ OData в named variable. После этого JSON Builder сможет взять `contractor.Ref_Key` и `contractor.Description`, не обращаясь снова к raw OData response.',
    '',
    '## Before you start',
    '- Создана OData Connection `OData ERP`.',
    '- В OData Explorer работает query contractor by INN.',
    '- В flow уже прочитан `inn` из `request.body.inn`.',
    '',
    '## Step config',
    '```text',
    'Step type: OData Query',
    'OData connection: OData ERP',
    'Resource: Catalog_Контрагенты',
    'Filter:',
    '  Field: ИНН',
    '  Operator: equals',
    '  Value source: request.body.inn',
    'Top: 1',
    'Save result as: contractor',
    'Required: yes',
    '```',
    '',
    '## Step-by-step',
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
    '## Compiled OData',
    '```text',
    "Catalog_Контрагенты?$filter=ИНН eq '7707083893'&$top=1",
    '```',
    '',
    '## Expected variable',
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
    '## Field-by-field explanation',
    '| Field | Value | Why it matters |',
    '| --- | --- | --- |',
    '| OData connection | OData ERP | Выбирает базу 1C, где лежит справочник контрагентов |',
    '| Resource | Catalog_Контрагенты | Техническое имя справочника из metadata |',
    '| Field | ИНН | Поле, по которому ищем контрагента |',
    '| Value source | request.body.inn | Берем ИНН из входного запроса 1C |',
    '| Top | 1 | Golden Scenario ожидает одного контрагента |',
    '| Save result as | contractor | Имя variable для следующих steps |',
    '| Required | yes | Без контрагента нельзя строить корректный target JSON |',
    '',
    '## What should happen',
    '::expected-result{items="Preview показывает contractor.Ref_Key|Timeline later сохранит odata_query contractor|Если контрагент не найден, flow остановится понятной business error|JSON Builder сможет использовать contractor.Ref_Key"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-first-odata-query-contractor" items="Выбрал OData Query|Выбрал OData ERP|Указал Catalog_Контрагенты|Настроил filter by ИНН|Top=1|Save result as contractor|Required=yes|Preview показывает contractor"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Save result as пустой или назван customer, а JSON Builder ожидает contractor|Required выключен и target JSON получает null|Value source указан как product_code|$select не содержит Ref_Key|Не проверили этот filter в OData Explorer"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Add Second OData Query" href="/docs/onec/academy/second-odata-query-product"}',
  )),
  page('academy', 'second-odata-query-product', 'Add Second OData Query: Product by Article', 'Настроить второй OData Query step и сохранить результат как product.', 81, mdLines(
    '# Add Second OData Query: Product by Article',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы добавите OData query #2: OMH берет `request.body.product_code`, ищет товар в `Catalog_Номенклатура` и сохраняет найденную строку как `product`.',
    '',
    '## Why this matters',
    'Second OData connection can be different. Например, contractor может жить в ERP, а product — в WMS или УСП. Поэтому второй OData step должен явно показывать, какую базу он использует.',
    '',
    '## Before you start',
    '- Первый OData query сохраняет `contractor`.',
    '- В flow уже есть `product_code`.',
    '- В OData Explorer проверен resource номенклатуры и field `Артикул`.',
    '',
    '## Step config',
    '```text',
    'Step type: OData Query',
    'OData connection: OData ERP or OData WMS',
    'Resource: Catalog_Номенклатура',
    'Filter:',
    '  Field: Артикул',
    '  Operator: equals',
    '  Value source: request.body.product_code',
    'Top: 1',
    'Save result as: product',
    'Required: yes',
    '```',
    '',
    '## Step-by-step',
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
    '## Expected variable',
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
    '## Field-by-field explanation',
    '| Field | Value | Why it matters |',
    '| --- | --- | --- |',
    '| OData connection | OData ERP or OData WMS | Product может быть в другой базе, не там же где contractor |',
    '| Resource | Catalog_Номенклатура | Technical OData resource для товаров |',
    '| Field | Артикул | Поле для поиска по product_code |',
    '| Value source | request.body.product_code | Берем article из входного request 1C |',
    '| Save result as | product | Имя variable для JSON Builder |',
    '| Required | yes | Без товара target API получит неполный payload |',
    '',
    '## What should happen',
    '::expected-result{items="Preview показывает product.Ref_Key|В preview одновременно есть contractor и product|Timeline later сохранит odata_query product|JSON Builder сможет использовать product.Ref_Key и product.Description"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-second-odata-query-product" items="Добавил второй OData Query|Выбрал правильную OData connection|Указал Catalog_Номенклатура|Настроил filter by Артикул|Save result as product|Required=yes|Preview показывает product"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Случайно сохранить второй результат как contractor и перезаписать первый lookup|Искать product в ERP, хотя он лежит в WMS|Использовать field Code вместо Артикул без проверки metadata|Не включить Required|Не ограничить $select"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Build Target JSON" href="/docs/onec/academy/build-target-json"}',
  )),
  page('academy', 'build-target-json', 'Build Target JSON', 'Собрать target_payload из request fields, contractor и product.', 91, mdLines(
    '# Build Target JSON',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы соберете `target_payload` для DNP API. В нем `pool_id` и `codes` приходят из 1C request, contractor fields приходят из первого OData query, product fields — из второго OData query.',
    '',
    '## Why this matters',
    'JSON Builder фиксирует contract внешнего API. Он не должен отправлять наружу весь raw request или весь raw OData response. Он должен собрать ровно те поля, которые target API ожидает.',
    '',
    '## Before you start',
    '- Есть variables `contractor` и `product`.',
    '- Есть request fields `pool_id` и `codes`.',
    '- Известна схема target API.',
    '',
    '## Field mapping table',
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
    '## Step-by-step',
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
    '## Final JSON',
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
    '## Constants, arrays and missing variables',
    '- Constant — значение, которое не берется из request или OData. Например `source_system = "1C"`.',
    '- Array — массив должен остаться массивом. `codes` нельзя склеивать в строку `code1,code2`, если target API ожидает JSON array.',
    '- Missing variable — если `contractor.Ref_Key` не найден, Preview должен показать ошибку до отправки в target API.',
    '- Preview — обязательный шаг перед Send. Он показывает target JSON без реального вызова target API.',
    '',
    '## What should happen',
    '::expected-result{items="Preview показывает target_payload|codes остается JSON array|source_system равен 1C|Если contractor/product missing, Preview показывает ошибку до target call"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-build-target-json" items="Добавил Build JSON step|Save result as target_payload|Сопоставил contractor fields|Сопоставил product fields|Передал codes как array|Добавил constant source_system|Проверил Preview"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Отправить весь contractor object вместо contractor_uuid|Потерять codes array при ручной строковой сборке|Использовать product.uuid, хотя OData вернул Ref_Key|Не проверить Preview|Не описать target contract для владельца API"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Send to External API" href="/docs/onec/academy/send-to-external-api"}',
  )),
  page('academy', 'send-to-external-api', 'Send to External API', 'Отправить target_payload во внешний DNP/API endpoint.', 101, mdLines(
    '# Send to External API',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы добавите target step: OMH отправляет `target_payload` методом POST во внешний сервис `DNP Service`.',
    '',
    '## Why this matters',
    'Flow должен не только собрать JSON, но и отправить его контролируемо: с base URL, headers, token secret, timeout, target.request artifact и target.response artifact.',
    '',
    '## Before you start',
    '- Создан REST connector или target connector `DNP Service`.',
    '- Target API path известен: `/api/marking/pools`.',
    '- Secret для token создан, если API требует Authorization.',
    '- `target_payload` проходит Preview.',
    '',
    '## Target config',
    '```text',
    'Connector: DNP Service',
    'Method: POST',
    'Path: /api/marking/pools',
    'Body: target_payload',
    '```',
    '',
    '## Step-by-step',
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
    '## Connector fields explained',
    '| Field | Example | Meaning |',
    '| --- | --- | --- |',
    '| Base URL | http://dnp.local | Корневой адрес target API |',
    '| Headers | Content-Type: application/json | Что target API ожидает получить |',
    '| Token secret | $secret:dnp.api.token | Секретный токен, не raw value в config |',
    '| Timeout | 20 | Сколько ждать target API |',
    '',
    '## Outgoing request',
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
    '## What should happen',
    '::expected-result{items="Flow показывает target step after build_json|target.request artifact содержит POST /api/marking/pools|target.response artifact сохраняет status и body|Ошибки target API видны без потери оригинального текста"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-send-to-external-api" items="Создал DNP Service connector|Выбрал POST|Указал path /api/marking/pools|Body source target_payload|Настроил token secret|Настроил timeout|Включил request/response artifacts"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Хранить target token raw в flow config|Отправлять request.body вместо target_payload|Не указывать Content-Type application/json|Слишком длинный sync timeout для 1C пользователя|Не сохранять target.response artifact"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Test Full Flow" href="/docs/onec/academy/test-full-flow"}',
  )),
  page('academy', 'test-full-flow', 'Test Full Flow', 'Прогнать весь flow: Test Console, Dry Run, Send и Timeline.', 111, mdLines(
    '# Test Full Flow',
    '',
    '::lesson-page{label="Lesson Pack B · Flow Builder"}',
    '',
    '## What you will build',
    'Вы выполните end-to-end test Golden Scenario: 1C POST payload проходит read fields, two OData queries, JSON Builder, target API call и Timeline.',
    '',
    '## Why this matters',
    'Настройка считается понятной только когда пользователь может сам отправить test request, увидеть target JSON preview, открыть Timeline и объяснить artifacts каждого шага.',
    '',
    '## Before you start',
    '- Endpoint создан.',
    '- Read fields настроены.',
    '- Contractor OData query настроен.',
    '- Product OData query настроен.',
    '- Build JSON настроен.',
    '- Target API step настроен.',
    '',
    '## Step-by-step',
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
    '## Test request',
    '```json',
    '{',
    '  "inn": "7707083893",',
    '  "product_code": "ABC-123",',
    '  "pool_id": "POOL-001",',
    '  "codes": ["code1", "code2"]',
    '}',
    '```',
    '',
    '## Timeline should show',
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
    '## Artifacts by step',
    '| Step | Artifact | What to check |',
    '| --- | --- | --- |',
    '| receive | incoming.request.json | Исходный JSON от 1C не потерян |',
    '| match_route | route.match.json | Выбран endpoint onec-pool-to-dnp |',
    '| odata_query contractor | odata.contractor.request.json / response.json | Filter by INN и найденный contractor.Ref_Key |',
    '| odata_query product | odata.product.request.json / response.json | Filter by article и найденный product.Ref_Key |',
    '| build_json | target_payload.json | Финальный JSON совпадает с target contract |',
    '| call_endpoint | target.request.json / target.response.json | Что ушло в DNP Service и что вернул target API |',
    '| handle_response | return_response.json | Что 1C получила в ответ: accepted event или business result |',
    '',
    '## What should happen',
    '::expected-result{items="Dry Run показывает target JSON preview|Send создает event_id|Timeline содержит receive, match_route, two OData queries, build_json, call_endpoint, handle_response|Artifacts позволяют объяснить результат без чтения кода"}',
    '',
    '## Check yourself',
    '::checklist{id="pack-b-test-full-flow" items="Открыл Test Console|Выбрал endpoint|Вставил JSON|Запустил Dry Run|Проверил target JSON preview|Нажал Send|Открыл Timeline|Проверил artifacts каждого шага"}',
    '',
    '## Common mistakes',
    '::common-mistakes{items="Нажать Send без Dry Run|Проверить только HTTP response и не открыть Timeline|Не проверить target_payload artifact|Не проверить оба OData response|Делать retry, не поняв failed step"}',
    '',
    '## Next lesson',
    '::next-lesson{label="Read Timeline and artifacts" href="/docs/onec/academy/lesson-11-read-timeline-and-artifacts"}',
  )),
];

export const academyPages: PageSeed[] = [
  lesson({
    slug: 'lesson-01-what-is-omh-for-1c-users',
    order: 10,
    title: 'Lesson 01 — What is OMH for 1C users',
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
    next: '[Lesson 02 — Create OData connection](/docs/onec/academy/lesson-02-create-odata-connection).'
  }),
  lesson({
    slug: 'lesson-02-create-odata-connection',
    order: 20,
    title: 'Lesson 02 — Create OData connection',
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
    next: '[Lesson 03 — Test OData in OData Explorer](/docs/onec/academy/lesson-03-test-odata-in-odata-explorer).'
  }),
  lesson({
    slug: 'lesson-03-test-odata-in-odata-explorer',
    order: 30,
    title: 'Lesson 03 — Test OData in OData Explorer',
    description: 'Проверка resource, filter, select и sample response до настройки flow.',
    build: 'Вы выполните первый запрос к `Catalog_Контрагенты` и сохраните точные поля, которые потом нужны для contractor lookup.',
    why: 'Flow не должен быть местом угадывания имен ресурсов. Сначала пользователь проверяет запрос в Explorer и только потом переносит его в builder.',
    before: ['Пройден Lesson 02.', 'Есть OData connection `OData ERP training`.', 'Пользователь 1C имеет права читать справочник контрагентов.'],
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
    next: '[Lesson 04 — Create inbound endpoint for 1C POST](/docs/onec/academy/lesson-04-create-inbound-endpoint-for-1c-post).'
  }),
  lesson({
    slug: 'lesson-04-create-inbound-endpoint-for-1c-post',
    order: 40,
    title: 'Lesson 04 — Create inbound endpoint for 1C POST',
    description: 'Создание входной точки, куда 1C отправит Golden Scenario payload.',
    build: 'Вы создадите endpoint `/api/bus/in/onec-pool-to-dnp` с JSON input и optional static token.',
    why: 'Endpoint фиксирует контракт между 1C и OMH: URL, method, headers, content type и поведение при ошибке auth.',
    before: ['Пройден Lesson 01.', 'Вы знаете, какой JSON 1C будет отправлять.', 'Решено, нужен ли inbound token для учебного стенда.'],
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
    next: '[Lesson 05 — Read values from incoming request](/docs/onec/academy/lesson-05-read-values-from-incoming-request).'
  }),
  lesson({
    slug: 'lesson-05-read-values-from-incoming-request',
    order: 50,
    title: 'Lesson 05 — Read values from incoming request',
    description: 'Извлечение INN, product_code, pool_id и codes из входного JSON.',
    build: 'Вы настроите первые шаги flow: прочитать поля из \`request.body\` и сохранить их как понятные variables.',
    why: 'Следующие OData lookup не должны читать сырой JSON руками. Им нужны named variables: \`inn\`, \`product_code\`, `pool_id`, `codes`.',
    before: ['Создан endpoint из Lesson 04.', 'Есть sample payload Golden Scenario.', 'Открыт Visual Flow Builder.'],
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
    next: '[Lesson 06 — First OData lookup: contractor by INN](/docs/onec/academy/lesson-06-first-odata-lookup-contractor-by-inn).'
  }),
  lesson({
    slug: 'lesson-06-first-odata-lookup-contractor-by-inn',
    order: 60,
    title: 'Lesson 06 — First OData lookup: contractor by INN',
    description: 'Первый lookup Golden Scenario: найти контрагента в 1C ERP по ИНН.',
    build: 'Вы добавите OData step, который берет variable \`inn\`, ищет контрагента и сохраняет результат как `contractor`.',
    why: 'DNP API не должен получать только ИНН, если ему нужен UUID/Ref_Key контрагента. OMH дочитывает данные из 1C и сохраняет artifact запроса.',
    before: ['Пройден Lesson 05.', 'В OData Explorer проверен filter для `Catalog_Контрагенты`.', 'В flow есть variable \`inn\`.'],
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
    next: '[Lesson 07 — Second OData lookup: product by article](/docs/onec/academy/lesson-07-second-odata-lookup-product-by-article).'
  }),
  lesson({
    slug: 'lesson-07-second-odata-lookup-product-by-article',
    order: 70,
    title: 'Lesson 07 — Second OData lookup: product by article',
    description: 'Второй lookup Golden Scenario: найти товар по product_code.',
    build: 'Вы добавите второй OData lookup, который ищет номенклатуру в ERP или WMS и сохраняет результат как `product`.',
    why: 'Один flow может использовать несколько OData sources. Главное — явно назвать connection и save_as, чтобы следующий step не перепутал contractor и product.',
    before: ['Пройден Lesson 06.', 'В OData Explorer проверен resource номенклатуры.', 'В flow есть variable \`product_code\`.'],
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
    next: '[Lesson 08 — Build target JSON](/docs/onec/academy/lesson-08-build-target-json).'
  }),
  lesson({
    slug: 'lesson-08-build-target-json',
    order: 80,
    title: 'Lesson 08 — Build target JSON',
    description: 'Сборка финального JSON для DNP API из входных данных и OData результатов.',
    build: 'Вы соберете `target_payload`, где pool_id и codes приходят из 1C, а contractor/product UUID и names приходят из OData.',
    why: 'Целевой API должен получить стабильную схему, а не случайный сырой ответ 1C OData. JSON Builder делает контракт явным и тестируемым.',
    before: ['Пройдены Lesson 06 и Lesson 07.', 'В preview есть `contractor` и `product`.', 'Известна схема DNP API.'],
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
    next: '[Lesson 09 — Send JSON to external API](/docs/onec/academy/lesson-09-send-json-to-external-api).'
  }),
  lesson({
    slug: 'lesson-09-send-json-to-external-api',
    order: 90,
    title: 'Lesson 09 — Send JSON to external API',
    description: 'Отправка target_payload во внешний DNP/internal API.',
    build: 'Вы добавите target call: POST JSON на внутренний DNP API с timeout, headers и response handling.',
    why: 'Интеграция заканчивается не сборкой JSON, а контролируемым вызовом внешней системы с artifacts, timeout и понятной ошибкой.',
    before: ['Пройден Lesson 08.', 'Создан REST connector или endpoint для DNP API.', 'Известен path и auth target API.'],
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
    next: '[Lesson 10 — Test full flow](/docs/onec/academy/lesson-10-test-full-flow).'
  }),
  lesson({
    slug: 'lesson-10-test-full-flow',
    order: 100,
    title: 'Lesson 10 — Test full flow',
    description: 'Полный прогон Golden Scenario через Test Console и curl.',
    build: 'Вы отправите учебный POST, проверите response, event id и убедитесь, что все шаги flow прошли в правильном порядке.',
    why: 'Настройка считается рабочей только после полного end-to-end теста. Отдельный OData success не доказывает, что target JSON и DNP call настроены правильно.',
    before: ['Пройдены Lesson 01-09.', 'Flow сохранен как draft или опубликован.', 'DNP target доступен или заменен mock endpoint.'],
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
    next: '[Lesson 11 — Read Timeline and artifacts](/docs/onec/academy/lesson-11-read-timeline-and-artifacts).'
  }),
  lesson({
    slug: 'lesson-11-read-timeline-and-artifacts',
    order: 110,
    title: 'Lesson 11 — Read Timeline and artifacts',
    description: 'Как читать результат выполнения без доступа к коду.',
    build: 'Вы откроете event Timeline и научитесь находить входной JSON, OData requests, OData responses, target JSON и ошибку внешней системы.',
    why: 'Timeline превращает “не работает” в конкретный факт: какой шаг упал, какой request ушел, какой response вернулся и что можно повторить.',
    before: ['Пройден Lesson 10.', 'Есть event id успешного или ошибочного теста.', 'Доступен Event Journal.'],
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
    next: '[Lesson 12 — Fix common errors](/docs/onec/academy/lesson-12-fix-common-errors).'
  }),
  lesson({
    slug: 'lesson-12-fix-common-errors',
    order: 120,
    title: 'Lesson 12 — Fix common errors',
    description: 'Первые действия при 401, resource not found, empty lookup, target error и DLQ.',
    build: 'Вы получите короткий алгоритм исправления Golden Scenario без паники: где смотреть, что менять и когда делать replay.',
    why: 'В production важна не только настройка happy path. Пользователь должен понимать, какие ошибки исправляются данными, какие конфигурацией, а какие retry.',
    before: ['Пройден Lesson 11.', 'Есть доступ к Timeline, OData Connections, OData Explorer и DLQ.', 'Пользователь понимает разницу inbound token, OData credentials и target API auth.'],
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
  page('troubleshooting', 'onec-returned-401', 'Troubleshooting — 1C returned 401', 'Как отличить входной 401 от OData/target 401.', 10, md(`# Troubleshooting — 1C returned 401

## Что проверить
1. Если 401 вернул endpoint OMH, проверьте \`X-OMH-Token\`.
2. Если 401 вернула OData 1C, проверьте OData Connection username/password/secret.
3. Если 401 вернул target API, проверьте REST connector auth.

## Где смотреть
Timeline -> failed step -> response artifact.
`)),
  page('troubleshooting', 'odata-resource-not-found', 'Troubleshooting — OData resource not found', 'Resource не найден в OData publication.', 20, md(`# Troubleshooting — OData resource not found

Откройте OData Explorer, загрузите metadata и выберите resource из списка. Не вводите имя справочника по памяти.

Если resource отсутствует, проверьте публикацию OData в 1C и base URL выбранной базы.
`)),
  page('troubleshooting', 'contractor-not-found-by-inn', 'Troubleshooting — Contractor not found by INN', 'Lookup контрагента по ИНН вернул пустой результат.', 30, md(`# Troubleshooting — Contractor not found by INN

1. Откройте incoming.request и проверьте фактический \`inn\`.
2. Откройте odata.contractor.request и скопируйте filter.
3. Повторите filter в OData Explorer.
4. Проверьте пробелы, кавычки, лидирующие нули и права пользователя 1C.
5. После исправления данных сделайте replay.
`)),
  page('troubleshooting', 'product-not-found', 'Troubleshooting — Product not found', 'Lookup товара по product_code не нашел номенклатуру.', 40, md(`# Troubleshooting — Product not found

Проверьте, что \`product_code\` читается из входного JSON, а filter использует правильное поле: \`Артикул\`, \`Code\`, \`SKU\` или поле вашей конфигурации.

Если товар лежит в WMS, выберите OData WMS connection, а не ERP.
`)),
  page('troubleshooting', 'target-api-returned-error', 'Troubleshooting — Target API returned error', 'Внешний DNP/API вернул 4xx/5xx.', 50, md(`# Troubleshooting — Target API returned error

Откройте \`target.request\` и \`target.response\`. Сравните JSON с контрактом target API.

- 400/422 обычно означает ошибку данных или mapping.
- 401/403 означает auth target connector.
- 5xx/timeout можно отправлять в retry, если target operation idempotent.
`)),
  page('troubleshooting', 'xml-parse-error', 'Troubleshooting — XML parse error', 'XML не парсится или потерялась кодировка.', 60, md(`# Troubleshooting — XML parse error

Проверьте raw incoming.request, Content-Type, XML declaration и encoding. Если XML пришел escaped строкой внутри JSON, сначала извлеките строку, потом парсите XML.
`)),
  page('troubleshooting', 'printer-unavailable', 'Troubleshooting — Printer unavailable', 'Printer package не может отправить job на принтер.', 70, md(`# Troubleshooting — Printer unavailable

Проверьте IP, port, network route из backend host/container, статус printer connector и print job artifacts. Не делайте blind replay, если есть риск повторной печати.
`)),
  page('troubleshooting', 'event-moved-to-dlq', 'Troubleshooting — Event moved to DLQ', 'Что делать, когда событие ушло в Dead Letter Queue.', 80, md(`# Troubleshooting — Event moved to DLQ

1. Откройте DLQ event.
2. Прочитайте original error.
3. Откройте artifacts failed step.
4. Исправьте данные, credentials или config.
5. Используйте Replay from DLQ только после исправления причины.
`)),
];

type RecipeConfig = {
  slug: string;
  order: number;
  title: string;
  description: string;
  when: string;
  flow: string;
  input: string;
  setup: string[];
  diagnostics: string[];
};

function recipe(config: RecipeConfig): PageSeed {
  return page('recipes', config.slug, config.title, config.description, config.order, md(`
# ${config.title}

## Когда использовать
${config.when}

## Схема
~~~text
${config.flow}
~~~

## Входной пример
~~~json
${config.input}
~~~

## Настройка в UI
${config.setup.map((item, index) => `${index + 1}. ${item}`).join('\n')}

## Что проверить в Timeline
${config.diagnostics.map((item) => `- ${item}`).join('\n')}

## Endpoint contract для 1C
- Method: POST.
- Content-Type: application/json, если рецепт не говорит XML.
- Header X-OMH-Token используется, если endpoint закрыт token auth.
- 1C должна обрабатывать не только 200, но и 202, 400, 401, 422, 500.

## Типовая ошибка и исправление
- Если OMH вернул 401, проверьте inbound token, а не OData пароль.
- Если OData вернула 404, откройте OData Explorer и проверьте resource.
- Если lookup пустой, проверьте field, operator и value source.
- Если target API вернул 5xx, откройте target.response и решите retry или исправление данных.

::checklist{id="${config.slug}" items="Создан endpoint|Проверен OData profile|Проверен sample request|Проверен Timeline|Описан response contract"}
`));
}

export const recipePages: PageSeed[] = [
  recipe({ slug: 'recipe-01-onec-post-odata-json-endpoint', order: 10, title: 'Рецепт 1. 1C POST -> OData -> JSON -> endpoint', description: 'Базовый промышленный маршрут с OData lookup и REST target.', when: '1C отправляет минимум данных, а OMH должен найти контрагента/номенклатуру в OData и отправить обогащенный JSON во внешний сервис.', flow: '1C -> OMH endpoint -> OData ERP lookup -> Build JSON -> REST endpoint -> Timeline', input: '{\n  "inn": "1234567890",\n  "product_code": "ABC-123",\n  "pool_id": "POOL-001"\n}', setup: ['Создайте OData ERP connection.', 'Проверьте Catalog_Контрагенты в OData Explorer.', 'Создайте Integration Flow с source 1C и target REST.', 'Добавьте OData step с required result.', 'Соберите target JSON и выполните Preview.'], diagnostics: ['incoming.request содержит исходный payload 1C.', 'lookup.request показывает resource и $filter.', 'transform.output содержит customer_uuid.', 'target.response хранит ответ REST API.'] }),
  recipe({ slug: 'recipe-02-onec-post-two-odata-lookups', order: 20, title: 'Рецепт 2. 1C POST -> два OData lookup -> endpoint', description: 'Контрагент и номенклатура из разных ресурсов OData.', when: 'Входной запрос содержит INN и артикул, а target API требует UUID контрагента и UUID товара.', flow: '1C -> Read INN/article -> OData Контрагенты -> OData Номенклатура -> Build JSON -> API', input: '{\n  "inn": "1234567890",\n  "article": "A-100",\n  "quantity": 5\n}', setup: ['Создайте один OData ERP profile или два профиля, если контрагент и товар лежат в разных базах.', 'В Explorer проверьте оба фильтра отдельно.', 'В Builder добавьте два OData step: contractor и product.', 'В Build JSON используйте оба результата.', 'Required включите на обоих lookup, если без них target payload невалиден.'], diagnostics: ['Два lookup step должны иметь разные save_as.', 'Пустой product lookup не должен тихо отправлять null.', 'Timeline должен показывать оба OData request.'] }),
  recipe({ slug: 'recipe-03-onec-xml-to-odata-json', order: 30, title: 'Рецепт 3. 1C XML -> OData -> JSON endpoint', description: '1C отправляет XML, OMH читает поля и обогащает JSON.', when: 'Старая конфигурация 1C уже умеет отправлять XML, но новая внешняя система принимает JSON.', flow: '1C XML -> XML parse -> OData lookup -> JSON template -> REST endpoint', input: '{\n  "xml": "<Request><Inn>1234567890</Inn><Order>SO-1</Order></Request>"\n}', setup: ['Выберите input_mode XML.', 'Опишите XPath или XML field extraction в первом шаге.', 'Сохраните INN как переменную.', 'Проверьте OData lookup по этой переменной.', 'Соберите JSON template для target API.'], diagnostics: ['incoming.request должен сохранить XML без потери.', 'parse step должен показать извлеченные поля.', 'Если XML invalid, ошибка должна остановить flow до OData.'] }),
  recipe({ slug: 'recipe-04-website-api-to-onec-http-service', order: 40, title: 'Рецепт 4. Website/API -> OMH -> 1C HTTP service', description: 'Внешний сайт вызывает 1C через контролируемый endpoint OMH.', when: 'Нужно не открывать 1C напрямую в интернет, а принимать запросы через OMH с audit, retry и timeline.', flow: 'Website -> OMH endpoint -> Validate JSON -> 1C HTTP service -> Response', input: '{\n  "order_id": "WEB-1001",\n  "status": "paid"\n}', setup: ['Создайте 1C HTTP service connector или connection profile.', 'Создайте flow с source webhook/API и target 1C.', 'Настройте auth входного endpoint.', 'Соберите payload для HTTP service 1C.', 'Выберите response mode proxy_response или accepted_event.'], diagnostics: ['target.request показывает путь HTTP service 1C.', '401 от 1C означает target credentials, не inbound token.', 'Timeout стоит обрабатывать через queue/retry.'] }),
  recipe({ slug: 'recipe-05-onec-to-printer-with-odata-enrichment', order: 50, title: 'Рецепт 5. 1C -> OData -> печать этикетки', description: 'Печать с дополнительными данными из OData.', when: '1C передает код товара, а на этикетке нужны название, серия, GTIN или складские атрибуты из OData.', flow: '1C -> OData Номенклатура -> Build ZPL/JSON -> Printer package -> Timeline', input: '{\n  "product_code": "ABC-123",\n  "label_count": 2,\n  "printer": "Zebra-01"\n}', setup: ['Установите Printer package.', 'Создайте OData profile для базы с номенклатурой.', 'Проверьте lookup товара.', 'Создайте flow с target printer.', 'Проверьте print job и printer logs.'], diagnostics: ['lookup.result содержит данные этикетки.', 'print job status виден в Printing.', 'Ошибки принтера не должны теряться в общей ошибке flow.'] }),
  recipe({ slug: 'recipe-06-onec-odata-polling-to-target', order: 60, title: 'Рецепт 6. Polling OData 1C -> target system', description: 'OMH сам опрашивает 1C OData и отправляет изменения наружу.', when: '1C не может отправлять HTTP POST, но можно регулярно читать опубликованные документы через OData.', flow: 'Polling job -> OData Документы -> cursor -> Build payload -> Target API', input: '{\n  "since": "last_successful_cursor",\n  "top": 100\n}', setup: ['Создайте OData profile.', 'Создайте polling job с resource Document_ЗаказПокупателя.', 'Настройте cursor field, например Date или Ref_Key.', 'Ограничьте page size.', 'Отправляйте каждую запись в target flow или API.'], diagnostics: ['source cursor обновляется только после успешной обработки.', 'Повторный запуск не должен дублировать уже обработанные документы.', 'DLQ должен хранить конкретную запись, а не весь polling batch.'] }),
  recipe({ slug: 'recipe-07-wms-to-onec-with-resolver', order: 70, title: 'Рецепт 7. WMS/API -> resolver -> 1C', description: 'Внешний WMS отправляет складскую операцию, OMH резолвит бизнес-объекты и вызывает 1C.', when: 'WMS знает SKU или внешний складской код, а 1C требует Ref_Key или внутренний UUID.', flow: 'WMS -> OMH -> Resolver cache -> OData/Business object -> 1C HTTP service', input: '{\n  "sku": "ABC-123",\n  "warehouse": "MAIN",\n  "qty": 10\n}', setup: ['Создайте resolver Product by SKU.', 'Настройте resolver на OData profile.', 'Добавьте Resolve Business Object step.', 'В payload 1C передайте найденный Ref_Key.', 'Включите cache, если справочник большой.'], diagnostics: ['resolver cache показывает hits.', 'Если объект не найден, ошибка должна быть бизнес-понятной.', 'Timeline должен отделять resolver error от 1C target error.'] }),
  recipe({ slug: 'recipe-08-onec-marking-pool-to-dnp', order: 80, title: 'Рецепт 8. 1C маркировка -> DNP/API', description: 'Маркировочный пул из 1C обогащается и отправляется в DNP сервис.', when: '1C хранит пул и номенклатуру, а внешний DNP/API требует нормализованный JSON с UUID, GTIN и списком кодов.', flow: '1C -> Normalize codes -> OData product -> Business rules -> DNP API', input: '{\n  "pool_id": "POOL-001",\n  "product_code": "ABC-123",\n  "codes": ["code1", "code2"]\n}', setup: ['Добавьте transform для кодов.', 'Добавьте OData product lookup.', 'Добавьте business rule для выбора target system.', 'Соберите JSON с codes как массивом, не строкой.', 'Проверьте response mode для 1C.'], diagnostics: ['transform.output сохраняет массив codes.', 'business rule показывает выбранный target.', 'target.response содержит id DNP операции.'] }),
  recipe({ slug: 'recipe-09-onec-correction-replay-from-dlq', order: 90, title: 'Рецепт 9. Исправление данных и replay из DLQ', description: 'Как восстановить событие после исправления справочника или target API.', when: 'Событие попало в DLQ из-за отсутствующего объекта, временной ошибки API или неверного mapping.', flow: 'DLQ event -> Inspect artifacts -> Fix data/config -> Replay -> Completed', input: '{\n  "event_id": "failed-event-id",\n  "reason": "Required OData lookup returned empty"\n}', setup: ['Откройте DLQ.', 'Откройте Timeline события.', 'Проверьте lookup.request и lookup.response.', 'Исправьте данные в 1C или config flow.', 'Нажмите Replay from DLQ.'], diagnostics: ['После replay создается новая attempt history.', 'Старый external error остается для аудита.', 'Если причина не исправлена, событие снова вернется в DLQ.'] }),
  recipe({ slug: 'recipe-10-dev-stage-prod-odata-profiles', order: 100, title: 'Рецепт 10. Dev/Stage/Prod OData profiles', description: 'Как держать одинаковый flow и разные подключения по окружениям.', when: 'Один flow должен работать в dev, stage и production, но OData URL и secrets отличаются.', flow: 'Environment profile -> OData ERP dev/stage/prod -> same Flow -> promotion pipeline', input: '{\n  "environment": "production",\n  "odata_connection": "OData ERP production"\n}', setup: ['Создайте отдельные OData profiles для окружений.', 'Используйте одинаковые secret names или environment variables.', 'Проверьте flow в stage.', 'Создайте change set.', 'Promote в production только после checklist.'], diagnostics: ['Audit log показывает promotion.', 'Config version показывает выбранный profile.', 'Production secret не экспортируется в открытом виде.'] }),
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
  requestExample({ slug: 'request-08-negative-missing-contractor', order: 80, title: 'Запрос 8. Негативный тест: контрагент не найден', description: 'Проверка Required lookup, ошибки и DLQ/replay.', endpoint: 'POST /api/bus/in/onec-customer-lookup', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "inn": "0000000000",\n  "source_document": "Bad document"\n}', odataFilter: 'Catalog_Контрагенты where ИНН eq \'0000000000\' -> expected empty', exampleId: 'onec.error_missing_contractor', notes: ['Это не success path, он нужен для проверки понятной ошибки.', 'Expected error: ODATA_RESULT_EMPTY или business validation.', 'После добавления контрагента можно replay.'] }),
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
