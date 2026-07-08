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
  'Вы открыли веб-интерфейс OMH и можете перейти в OData Connections, OData Master, Integration Flows, Test Console и Event Timeline.',
  'Для OData уроков опубликован OData сервис 1C и известен URL вида http://server/base/odata/standard.odata.',
];

const academySelfCheckQuestions: Record<string, string[]> = {
  'create-odata-connection': [
    'Чем OData Connection отличается от Endpoint?',
    'Где хранится пароль 1C: в JSON flow или в secret reference?',
    'Что должен подтвердить Test metadata перед настройкой flow?',
  ],
  'test-odata-explorer': [
    'Зачем сначала выполнить `Catalog_Контрагенты?$top=5` без сложного фильтра?',
    'Где вы увидите точный resource name из metadata?',
    'Почему OData Master должен использовать ту же connection, что и будущий flow?',
  ],
  'find-contractor-by-inn': [
    'Что обычно означает `Ref_Key` в ответе 1C OData?',
    'Где проверить точный `$filter`, если поиск по ИНН вернул пустой результат?',
    'Какие причины кроме “контрагента нет” могут дать `{ "value": [] }`?',
  ],
  'create-inbound-endpoint': [
    'Чем inbound token endpoint отличается от логина/пароля OData?',
    'Какой путь должен вызвать 1C: `/api/bus/in/{slug}` или страницу документации?',
    'Где скопировать правильный endpoint URL перед передачей разработчику 1C?',
  ],
  'read-request-fields': [
    'Почему `request.body.inn` отличается от `request.inn`?',
    'Какие поля Golden Scenario нужно прочитать из входного JSON?',
    'Где в Preview проверить, что `codes` остался массивом?',
  ],
  'first-odata-query-contractor': [
    'Какой input value должен попасть в фильтр `ИНН eq ...`?',
    'Почему результат сохраняется как `contractor`?',
    'Какие artifacts нужно открыть при ошибке первого OData lookup?',
  ],
  'second-odata-query-product': [
    'Почему второй lookup нельзя сохранить снова как `contractor`?',
    'Как выбрать между `OData ERP` и `OData WMS` для номенклатуры?',
    'Какие поля нужно вернуть через `$select`, чтобы JSON Builder не упал?',
  ],
  'build-target-json': [
    'Почему во внешний API не нужно отправлять весь OData response?',
    'Откуда берется `contractor_uuid` в target JSON?',
    'Как проверить, что `codes` не превратился в строку?',
  ],
  'send-to-external-api': [
    'Где посмотреть реальный body, который OMH отправил во внешний API?',
    'Какие ошибки target API нельзя просто бесконечно retry?',
    'Чем `target.request.json` отличается от `target.response.json`?',
  ],
  'full-flow-click-by-click': [
    'Какие шаги должен показать Expected Timeline полного сценария?',
    'Почему Dry Run нужно выполнить до реального Send?',
    'Где найти оба OData request preview и target request preview?',
  ],
  'test-full-flow': [
    'Что подтверждает `event_id` после Send?',
    'Почему HTTP 200/accepted еще не доказывает успешную интеграцию?',
    'Какие artifacts нужно открыть после end-to-end теста?',
  ],
  'lesson-01-what-is-omh-for-1c-users': [
    'Что является входной точкой для POST из 1C?',
    'Почему Timeline важнее общего текста ошибки?',
    'Какой экран отвечает за сохраненные подключения к базам 1C?',
  ],
  'lesson-02-create-odata-connection': [
    'Какие поля обязательны для OData Connection?',
    'Что проверяет `$metadata`?',
    'Почему connection нужно называть по базе, например `OData ERP`?',
  ],
  'lesson-03-test-odata-in-odata-explorer': [
    'Где увидеть список ресурсов из metadata?',
    'Что означает пустой массив `value`?',
    'Почему сначала проверяют `$top`, а потом `$filter`?',
  ],
  'lesson-04-create-inbound-endpoint-for-1c-post': [
    'Какой URL должен использовать 1C для вызова OMH?',
    'Какие headers нужны для JSON POST?',
    'Где проверить, что endpoint создал событие?',
  ],
  'lesson-05-read-values-from-incoming-request': [
    'Какие четыре поля читает Golden Scenario из request body?',
    'Почему path должен совпадать с фактическим JSON?',
    'Как Preview помогает найти ошибку до publish?',
  ],
  'lesson-06-first-odata-lookup-contractor-by-inn': [
    'Где вы видите точный OData filter, который OMH отправил в 1C?',
    'Что обычно представляет `Ref_Key`?',
    'Что делать, если lookup вернул `{ "value": [] }`?',
  ],
  'lesson-07-second-odata-lookup-product-by-article': [
    'Какое поле входного JSON используется для поиска товара?',
    'Почему у товара может быть другая OData база?',
    'Какой artifact доказывает, что найден правильный продукт?',
  ],
  'lesson-08-build-target-json': [
    'Какие поля должны попасть в target JSON?',
    'Почему source path должен быть точным?',
    'Как JSON Builder показывает ошибку missing variable?',
  ],
  'lesson-09-send-json-to-external-api': [
    'Где хранить auth внешнего API?',
    'Какой artifact содержит оригинальный ответ target API?',
    'Когда retry может создать дубль операции?',
  ],
  'lesson-10-test-full-flow': [
    'Чем Dry Run отличается от Send?',
    'Как понять, что flow прошел оба OData lookup?',
    'Где увидеть response, который вернулся caller’у?',
  ],
  'lesson-11-read-timeline-and-artifacts': [
    'Как найти первый failed step?',
    'Какие artifacts показывают OData request и response?',
    'Почему исправлять нужно причину, а не последний статус?',
  ],
  'lesson-12-fix-common-errors': [
    'Как отличить inbound 401 от OData 401?',
    'Что проверять при 404 от OMH в 1C?',
    'Когда событие нужно возвращать из DLQ в retry?',
  ],
};

const defaultSelfCheckQuestions = [
  'Какой экран OMH вы откроете первым для проверки результата?',
  'Какой artifact доказывает, что шаг выполнился именно так?',
  'Что вы проверите перед тем, как нажать Send или Retry?',
];

function withSelfCheck(seed: PageSeed): PageSeed {
  if (seed.markdown.includes('## Вопросы для самопроверки')) return seed;
  const questions = academySelfCheckQuestions[seed.slug] ?? defaultSelfCheckQuestions;
  const block = ['', '## Вопросы для самопроверки', ...questions.map((item, index) => `${index + 1}. ${item}`), ''].join('\n');
  for (const marker of ['\n## Частые ошибки', '\n## Следующий урок']) {
    const index = seed.markdown.indexOf(marker);
    if (index >= 0) {
      return { ...seed, markdown: `${seed.markdown.slice(0, index)}${block}${seed.markdown.slice(index)}` };
    }
  }
  return { ...seed, markdown: `${seed.markdown}${block}` };
}

type PedagogyBlock = {
  short?: string[];
  intermediate: string[];
  variables: string[];
  artifacts: string[];
  shouldSee: string[];
  developer: string;
  fieldTable?: string[];
  errors?: string[];
};

const defaultPedagogyBlock: PedagogyBlock = {
  intermediate: [
    'Появляется проверяемый результат текущего шага, а не просто “настройка сохранена”.',
    'Следующий шаг должен явно использовать этот результат как переменную, field value или artifact.',
  ],
  variables: [
    '`request.body.*` — значения из тела входящего запроса 1C.',
    '`contractor.*`, `product.*`, `target_payload` — переменные, которые создают шаги интеграционного потока.',
  ],
  artifacts: [
    '`incoming.request.json` — тело входящего запроса.',
    '`step.result.json` — сохраненный результат шага.',
    '`step.error.json` — понятная ошибка, если шаг не выполнен.',
  ],
  shouldSee: [
    'У шага есть понятное имя.',
    'Preview или Timeline показывает результат без чтения backend logs.',
    'Понятно, что делать дальше при success и при ошибке.',
  ],
  developer: 'Держите контракт простым: 1C отправляет HTTP POST в OMH, а OMH уже выполняет выборки OData, сборку JSON и диагностику в Timeline. Писать Python-код в 1C не нужно.',
};

const pedagogyBySlug: Record<string, PedagogyBlock> = {
  'create-odata-connection': {
    intermediate: [
      'В списке OData Connections появляется подключение `OData ERP`.',
      'Проверка подключения (`Test $metadata`) показывает, может ли OMH прочитать структуру опубликованной базы 1C.',
    ],
    variables: [
      'Переменных потока пока нет. Вы создаете reusable connection, которую потом выберете в OData Master и Flow Builder.',
      'Имя `OData ERP` должно сразу отвечать пользователю: в какую базу 1C пойдет OMH.',
    ],
    artifacts: [
      '`odata_metadata_request` — какой `$metadata` URL проверял OMH.',
      '`odata_metadata_response` — что 1C вернула при проверке подключения.',
    ],
    shouldSee: [
      'OData connection появилась в списке.',
      'Test $metadata показывает success или понятную внешнюю ошибку 1C.',
      'Это подключение можно выбрать в OData Master.',
    ],
    fieldTable: [
      '| UI field | Пример | Что означает |',
      '| --- | --- | --- |',
      '| OData Connection | `OData ERP` | база 1C, где OMH будет искать данные |',
      '| Base URL | `/odata/standard.odata` | опубликованный OData endpoint 1C, не web-клиент |',
      '| Username | `exchange_user` | пользователь 1C для обмена |',
      '| Password | `$secret:secret_odata_erp_password` | пароль хранится в Secrets Store |',
      '| Test $metadata | кнопка проверки | проверяет URL, логин, пароль и права чтения metadata |',
    ],
    developer: 'Попросите администратора 1C создать отдельного пользователя обмена, например `exchange_user`. Не используйте основного администратора как рекомендованный вариант для production.',
    errors: [
      'Если `$metadata` не открывается, не переходите в Flow Builder.',
      'Если ошибка 401, проверяйте логин, пароль и права пользователя 1C.',
      'Если ошибка 404, почти всегда указан не OData URL, а другой адрес публикации.',
    ],
  },
  'test-odata-explorer': {
    intermediate: [
      'OMH показывает список ресурсов из metadata выбранной базы 1C.',
      'Первый запрос `$top=5` возвращает несколько строк без сложного фильтра.',
    ],
    variables: [
      'Переменных потока еще нет. Но вы уже узнаете точные имена resource и fields, которые потом попадут в OData Query step.',
      'Например: `Catalog_Контрагенты`, `Ref_Key`, `Description`, `ИНН`.',
    ],
    artifacts: [
      '`odata_explorer_request` — безопасный учебный запрос в 1C.',
      '`odata_explorer_response` — ответ 1C, по которому вы проверяете поля.',
    ],
    shouldSee: [
      'Resource list загрузился из metadata.',
      'В ответе есть `Ref_Key` и `Description`.',
      'Вы можете скопировать resource и field names в Flow Builder без угадывания.',
    ],
    fieldTable: [
      '| UI field | Пример | Что означает |',
      '| --- | --- | --- |',
      '| OData Connection | `OData ERP` | конкретная база 1C |',
      '| Resource | `Catalog_Контрагенты` | справочник/таблица из metadata |',
      '| `$select` | `Ref_Key,Description,ИНН` | какие поля вернуть |',
      '| `$top` | `5` | безопасный лимит строк |',
    ],
    developer: 'Для разработчика 1C это доказательство, что проблема не в коде POST из 1C: OMH уже умеет читать опубликованную базу через OData.',
  },
  'find-contractor-by-inn': {
    intermediate: [
      'OData Master возвращает одну строку контрагента.',
      'В этой строке есть `Ref_Key`, который дальше станет UUID контрагента в итоговом JSON.',
    ],
    variables: [
      'В учебном запросе переменная еще не создана, но именно этот результат позже будет сохранен как `contractor`.',
      'Следующие шаги смогут читать `contractor.Ref_Key`, `contractor.Description`, `contractor.ИНН`.',
    ],
    artifacts: [
      '`odata_query_request` — resource, filter, `$select`, `$top`.',
      '`odata_query_response` — raw ответ 1C.',
      '`odata_query_result` — первый найденный объект, сохраненный как переменная.',
    ],
    shouldSee: [
      'В результате есть `Ref_Key`.',
      'Фильтр использует точное поле `ИНН` из metadata.',
      'Если ответ `{ "value": [] }`, вы понимаете, что OMH дошел до 1C, но 1C не нашла строку.',
    ],
    developer: 'Если в 1C другое имя поля ИНН, передайте внедренцу точное OData имя из metadata. Не ориентируйтесь только на подпись поля в форме 1C.',
  },
  'create-inbound-endpoint': {
    intermediate: [
      'Появляется URL `/api/bus/in/onec-pool-to-dnp`, на который 1C сможет отправлять POST.',
      'OMH уже знает input mode, response mode и способ проверки входного token.',
    ],
    variables: [
      'После первого POST OMH создаст `request.body` — тело входящего запроса.',
      'Поля из JSON будут доступны как `request.body.inn`, `request.body.product_code`, `request.body.pool_id`, `request.body.codes`.',
    ],
    artifacts: [
      '`incoming.request.json` — исходное тело запроса от 1C.',
      '`incoming.request.headers` — headers с redaction секретов.',
      '`route.match.json` — как OMH сопоставил запрос с endpoint/flow.',
    ],
    shouldSee: [
      'Endpoint виден в Integration Bus или Flow Builder.',
      'Test Console может выбрать этот endpoint.',
      'Ошибочный frontend URL не используется вместо backend API URL.',
    ],
    fieldTable: [
      '| UI field | Пример | Что означает |',
      '| --- | --- | --- |',
      '| Slug | `onec-pool-to-dnp` | часть URL после `/api/bus/in/` |',
      '| Input mode | `JSON` | OMH ожидает JSON body |',
      '| Response mode | `accepted_event` | 1C быстро получает `event_id` |',
      '| Auth | `static token` | защита endpoint от чужих запросов |',
    ],
    developer: 'Для разработчика 1C нужен только HTTP POST на backend API URL. Внешний вид сайта и auth-пакет UI не меняют адрес интеграционного endpoint.',
    errors: [
      '404 от OMH: проверьте slug, `/api/bus/in/{slug}` и backend host.',
      '401/403 от OMH: проверьте `X-OMH-Token`, а не OData пароль.',
    ],
  },
  'read-request-fields': {
    intermediate: [
      'OMH разбирает входящий JSON и показывает поля, которые дальше можно использовать.',
      'Теперь есть значения `inn`, `product_code`, `pool_id`, `codes`.',
    ],
    variables: [
      '`request.body.inn` — ИНН контрагента.',
      '`request.body.product_code` — код товара.',
      '`request.body.pool_id` — номер/код пула.',
      '`request.body.codes` — массив кодов маркировки.',
    ],
    artifacts: [
      '`incoming.request.json` — исходный JSON от 1C.',
      '`read_fields.result.json` — извлеченные значения для следующих шагов.',
    ],
    shouldSee: [
      '`codes` остался массивом, а не строкой.',
      'Preview variables показывает все четыре поля.',
      'Следующий OData step может использовать `request.body.inn`.',
    ],
    developer: 'Если структура JSON меняется в 1C, сначала обновите paths чтения полей. Иначе OData filter будет пустым или неверным.',
  },
  'first-odata-query-contractor': {
    intermediate: [
      'После Preview появляется переменная `contractor`.',
      'Внутри нее есть `contractor.Ref_Key`, `contractor.Description`, `contractor.ИНН`.',
    ],
    variables: [
      '`contractor.Ref_Key` — UUID контрагента в 1C.',
      '`contractor.Description` — название контрагента.',
      '`contractor.ИНН` — проверочное значение, по которому нашли строку.',
    ],
    artifacts: [
      '`odata_query_request` — точный OData filter, который OMH отправил в 1C.',
      '`odata_query_response` — raw ответ 1C.',
      '`odata_query_result` — объект, сохраненный как `contractor`.',
    ],
    shouldSee: [
      'В Preview есть `contractor.Ref_Key`.',
      'В Timeline есть artifact `odata_query_response`.',
      'Переменная `contractor` доступна в следующих шагах.',
    ],
    fieldTable: [
      '| UI field | Example | Meaning |',
      '| --- | --- | --- |',
      '| OData Connection | `OData ERP` | 1C base where OMH will search data |',
      '| Resource | `Catalog_Контрагенты` | 1C catalog/table to query |',
      '| Filter field | `ИНН` | field in 1C resource |',
      '| Operator | `equals` | comparison type |',
      '| Value source | `request.body.inn` | where value comes from |',
      '| Save as | `contractor` | variable name for result |',
      '| Required | `yes` | fail if not found |',
    ],
    developer: 'Если в 1C есть пробелы или форматирование ИНН, лучше нормализовать значение до OData Query: trim/remove spaces.',
    errors: [
      'Пустой результат: проверьте connection, resource, field name, значение ИНН и права пользователя 1C.',
      '401: исправляйте логин/пароль OData connection.',
      'Resource not found: скопируйте имя из OData Master, а не из памяти.',
    ],
  },
  'second-odata-query-product': {
    intermediate: [
      'После Preview одновременно доступны `contractor` и `product`.',
      'Второй OData step не перезаписывает результат первого.',
    ],
    variables: [
      '`product.Ref_Key` — UUID товара/номенклатуры в 1C.',
      '`product.Description` — имя товара.',
      '`product.Артикул` — артикул, по которому нашли товар.',
    ],
    artifacts: [
      '`odata_query_request` для `get_product` — connection, resource и filter товара.',
      '`odata_query_response` — ответ выбранной OData базы.',
      '`odata_query_result` — объект, сохраненный как `product`.',
    ],
    shouldSee: [
      'Preview показывает `product.Ref_Key`.',
      'Переменные `contractor` и `product` существуют одновременно.',
      'В JSON Builder можно выбрать `product.Ref_Key`.',
    ],
    developer: 'Если номенклатура живет в WMS/УСП, выберите отдельную OData Connection. Не заставляйте ERP искать то, чего в ней нет.',
  },
  'build-target-json': {
    intermediate: [
      'Появляется переменная `target_payload` — итоговый JSON для внешнего API.',
      'В него попали только нужные поля: `pool_id`, UUID контрагента, UUID товара и `codes`.',
    ],
    variables: [
      '`target_payload.pool_id` берется из `request.body.pool_id`.',
      '`target_payload.contractor_uuid` берется из `contractor.Ref_Key`.',
      '`target_payload.product_uuid` берется из `product.Ref_Key`.',
      '`target_payload.codes` берется из `request.body.codes` и остается массивом.',
    ],
    artifacts: [
      '`json_builder_template` — правила сборки JSON.',
      '`json_builder_result` — итоговый JSON.',
      '`target_payload.json` — сохраненный payload для target call.',
    ],
    shouldSee: [
      'Preview показывает валидный JSON.',
      '`codes` не превратился в строку.',
      'Если `contractor.Ref_Key` отсутствует, ошибка появляется до отправки наружу.',
    ],
    fieldTable: [
      '| Target field | Source | Meaning |',
      '| --- | --- | --- |',
      '| `contractor_uuid` | `contractor.Ref_Key` | 1C UUID of contractor |',
      '| `product_uuid` | `product.Ref_Key` | 1C UUID of product |',
      '| `codes` | `request.body.codes` | marking codes from 1C request |',
      '| `source_system` | constant `"1C"` | fixed value |',
    ],
    developer: 'Если вы уже знаете структуру JSON внешнего API, укажите её в JSON Builder. В 1C не нужно вручную собирать этот итоговый JSON.',
  },
  'send-to-external-api': {
    intermediate: [
      'OMH готовит outgoing request: method, URL, headers и body `target_payload`.',
      'После запуска будет понятно, что именно ушло во внешний API и что он ответил.',
    ],
    variables: [
      '`target_payload` — body исходящего запроса.',
      '`target.response.status` и body ответа будут доступны в Timeline после вызова.',
    ],
    artifacts: [
      '`outgoing_request` или `target.request.json` — что OMH отправил во внешний API.',
      '`incoming_response` или `target.response.json` — что внешний API ответил.',
      '`external_error` — исходная ошибка target API без потери текста.',
    ],
    shouldSee: [
      'Target step использует `target_payload`, а не raw `request.body`.',
      'Headers не раскрывают secret values.',
      'При ошибке target API виден оригинальный status/body.',
    ],
    developer: 'Если внешний API возвращает бизнес-ошибку 400, не делайте бесконечный retry. Сначала исправьте данные или mapping.',
  },
  'full-flow-click-by-click': {
    short: [
      '1C отправляет JSON.',
      'OMH берет из него ИНН и код товара.',
      'OMH ищет контрагента и товар в OData.',
      'OMH собирает новый JSON.',
      'OMH отправляет JSON во внешний API.',
    ],
    intermediate: [
      'После полного Preview видны все ключевые данные: `request.body`, `contractor`, `product`, `target_payload` и target request preview.',
      'Dry Run показывает будущий результат без реального вызова внешнего API.',
    ],
    variables: [
      '`request.body.inn` -> `contractor` -> `target_payload.contractor_uuid`.',
      '`request.body.product_code` -> `product` -> `target_payload.product_uuid`.',
      '`request.body.codes` -> `target_payload.codes`.',
    ],
    artifacts: [
      '`incoming.request.json` — что пришло от 1C.',
      '`odata.get_contractor.request.json` и `.response.json`.',
      '`odata.get_product.request.json` и `.response.json`.',
      '`target_payload.json`.',
      '`target.request.json` и `target.response.json`.',
    ],
    shouldSee: [
      'Expected Timeline содержит receive, get_contractor, get_product, build_target_payload, send_to_dnp, handle_response.',
      'Dry Run не отправляет запрос во внешний API.',
      'После real Send есть `event_id` и открываемый Timeline.',
    ],
    developer: 'В коде 1C вам нужно отправить HTTP POST на endpoint OMH. OMH не требует, чтобы вы писали Python-код или вручную выполняли OData lookup из 1C.',
  },
  'test-full-flow': {
    intermediate: [
      'После Send появляется `event_id` и `timeline_url`.',
      'Timeline показывает фактический runtime, а не только конфигурацию.',
    ],
    variables: [
      'Проверяйте, что runtime получил те же variables, которые вы видели в Preview.',
      'Если variable отличается, сравните `incoming.request.json` и preview input.',
    ],
    artifacts: [
      '`incoming.request.json`.',
      '`odata.contractor.request.json` / `response.json`.',
      '`odata.product.request.json` / `response.json`.',
      '`target_payload.json`.',
      '`target.request.json` / `target.response.json`.',
    ],
    shouldSee: [
      'Send создал event id.',
      'Timeline содержит все ожидаемые steps.',
      'Artifacts позволяют объяснить результат без backend logs.',
    ],
    developer: 'HTTP accepted означает, что OMH принял событие. Финальный бизнес-результат проверяйте в Timeline.',
  },
  'lesson-11-read-timeline-and-artifacts': {
    intermediate: [
      'Вы находите первый failed step и открываете его request/response artifacts.',
      'Root cause формулируется по оригинальному ответу внешней системы или 1C.',
    ],
    variables: [
      'Timeline показывает, какие переменные были созданы до ошибки.',
      'Если переменная отсутствует, ошибка почти всегда в предыдущем step.',
    ],
    artifacts: [
      '`incoming.request.json`, `odata_query_request`, `odata_query_response`.',
      '`target_payload.json`, `target.request.json`, `target.response.json`.',
      '`error.json` с классификацией retryable/non-retryable.',
    ],
    shouldSee: [
      'Первый failed step найден.',
      'Оригинальная ошибка открыта как artifact.',
      'Понятно, делать retry, edit retry или менять конфигурацию.',
    ],
    developer: 'Не просите пользователя прислать только “ошибка”. Просите event id и artifacts первого failed step.',
  },
  'lesson-12-fix-common-errors': {
    intermediate: [
      'Каждая ошибка привязана к месту проверки: endpoint, OData connection, Flow Builder, Timeline или DLQ.',
      'Пользователь не чинит весь flow сразу, а исправляет первый доказанный сбой.',
    ],
    variables: [
      'При OData empty result проверяйте value source: `request.body.inn` или `request.body.product_code`.',
      'При JSON Builder missing variable проверяйте `contractor.Ref_Key`, `product.Ref_Key`, `target_payload`.',
    ],
    artifacts: [
      '`incoming.request.headers` для inbound auth.',
      '`odata_query_response` для 401/empty/resource errors.',
      '`target.response.json` для внешнего API.',
      '`dlq.reason.json` или attempt history для DLQ.',
    ],
    shouldSee: [
      'Понятно, где именно ошибка: вход, OData, JSON Builder, target API или runtime.',
      'Retry делается только после исправления причины.',
      'DLQ не очищается до разбора artifacts.',
    ],
    developer: 'Для каждого инцидента фиксируйте event id, failed step, artifact и действие: config fix, data fix, secret fix или retry.',
  },
};

function withPedagogicalPass(seed: PageSeed): PageSeed {
  if (seed.markdown.includes('## Промежуточный результат')) return seed;
  const note = pedagogyBySlug[seed.slug] ?? defaultPedagogyBlock;
  const block = mdLines(
    ...(note.short ? ['## Если совсем коротко', ...note.short.map((item, index) => `${index + 1}. ${item}`), ''] : []),
    '## Промежуточный результат',
    ...note.intermediate.map((item) => `- ${item}`),
    '',
    '## Как UI поля становятся переменными',
    ...note.variables.map((item) => `- ${item}`),
    '',
    ...(note.fieldTable ? ['## Таблица полей UI', ...note.fieldTable, ''] : []),
    '## Что появится в Timeline',
    ...note.artifacts.map((item) => `- ${item}`),
    '',
    '## Что вы должны увидеть',
    ...note.shouldSee.map((item) => `- ✓ ${item}`),
    '',
    '## Для разработчика 1С',
    note.developer,
    '',
    ...(note.errors ? ['## Практичная диагностика ошибок', ...note.errors.map((item, index) => `${index + 1}. ${item}`), ''] : []),
  );
  const marker = '\n## Частые ошибки';
  const index = seed.markdown.indexOf(marker);
  if (index >= 0) return { ...seed, markdown: `${seed.markdown.slice(0, index)}\n${block}\n${seed.markdown.slice(index)}` };
  return { ...seed, markdown: `${seed.markdown}\n\n${block}` };
}

export const academyPackAPages: PageSeed[] = [
  page('academy', 'training-sandbox-executable-docs', 'Учебный sandbox: запускаем уроки как реальные интеграции', 'Установить Training Sandbox, открыть готовые примеры в Test Console и разобрать Timeline без реальной 1С.', 19, mdLines(
    '# Учебный sandbox: запускаем уроки как реальные интеграции',
    '',
    '::lesson-page{label="Task 050 · Executable docs"}',
    '',
    '## Зачем это нужно',
    'Если пользователь только открыл OMH, ему рано настраивать production ERP. Сначала он должен увидеть рабочий путь: 1С присылает JSON, OMH делает OData-запросы, собирает JSON, вызывает DNP API, а затем показывает Timeline и artifacts.',
    '',
    'Training Sandbox ставит безопасные mock-системы:',
    '- `Training OData ERP` — справочники Контрагенты, Номенклатура, Склады и ЗаказКлиента.',
    '- `Training OData WMS` — склады, ячейки и остатки.',
    '- `Training DNP API` — принимает `POOL-001` и специально отклоняет `POOL-ERROR`.',
    '- `Training Printer` — печатает на `TRAINING-PRINTER-01` и специально падает на `TRAINING-OFFLINE`.',
    '',
    '::open-page{route="/training" label="Открыть Training Sandbox"}',
    '::open-page{route="/odata-explorer" label="Открыть OData Master"}',
    '',
    '## Быстрый запуск',
    '1. Откройте `/training`.',
    '2. Нажмите `Установить Training Sandbox`.',
    '3. Запустите пример `training.onec.post_two_odata_to_dnp`.',
    '4. Откройте ссылку `Открыть последнюю Timeline`.',
    '5. Посмотрите artifacts `odata_query_request`, `odata_query_response`, `json_builder_result`, `outgoing_request`, `incoming_response`.',
    '',
    '::example{exampleId="training.onec.post_two_odata_to_dnp"}',
    '',
    '## Как проверить OData отдельно',
    '1. Откройте `OData Master`.',
    '2. Если training connection еще нет, нажмите `Install Training Sandbox`.',
    '3. Нажмите `Use Training OData ERP`.',
    '4. Оставьте resource `Catalog_Контрагенты`.',
    '5. Запустите `$filter`: `ИНН eq \'7707083893\' and DeletionMark eq false`.',
    '6. В `$select` оставьте `Ref_Key,Description,ИНН` — так pipeline дальше получает только нужные поля.',
    '',
    '```http',
    'GET /api/training/mock-odata/erp/odata/standard.odata/Catalog_Контрагенты?$filter=ИНН eq \'7707083893\'&$select=Ref_Key,Description,ИНН&$top=1',
    '```',
    '',
    '::example{exampleId="training.onec.find_contractor_by_inn"}',
    '::example{exampleId="training.onec.find_product_by_article"}',
    '',
    '## Ошибки, которые нужно увидеть руками',
    'Не пропускайте негативные примеры. Они учат читать Timeline быстрее, чем сухая справка.',
    '',
    '::example{exampleId="training.errors.contractor_not_found"}',
    '::example{exampleId="training.errors.dnp_rejected"}',
    '::example{exampleId="training.errors.printer_offline"}',
    '',
    '## Что дальше',
    'После sandbox переходите к созданию настоящего OData connection. Логика та же: сначала проверяете OData Master, потом переносите resource/filter/select в Flow Builder, затем запускаете Test Console и читаете Timeline.',
  )),
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
    '::expected-result{items="В списке появилась connection OData ERP|Healthcheck/Test $metadata вернул OK или понятную ошибку 1C|Connection можно выбрать в OData Master|Пользователь понимает, что это подключение к конкретной базе 1C, а не generic connector"}',
    '',
    '## Проверьте себя',
    '::checklist{id="pack-a-create-odata-connection" items="Открыл OData Connections|Заполнил Name|Заполнил Base URL с /odata/standard.odata|Указал username|Использовал secret для production password|Нажал Create connection|Нажал Test $metadata"}',
    '',
    '## Частые ошибки',
    '::common-mistakes{items="Wrong base URL: указан адрес web-клиента 1C вместо OData publication|Пропущен хвост /odata/standard.odata|OData в 1C не опубликована|Неверный user/password|Пользователь 1C не имеет прав читать справочники|Создали generic Connector и не понимают, почему его неудобно выбрать в OData Master"}',
    '',
    '## Следующий урок',
    '::next-lesson{label="Проверить OData в OData Master" href="/docs/onec/academy/test-odata-explorer"}',
  )),
  page('academy', 'test-odata-explorer', 'Проверяем OData-запрос в OData Master', 'Подробный урок: выбрать OData ERP, загрузить resources и выполнить первый безопасный query.', 31, mdLines(
    '# Проверяем OData-запрос в OData Master',
    '',
    '::lesson-page{label="Пакет уроков A · Основы OData"}',
    '',
    '## Что вы настроите',
    'Вы проверите, что OMH действительно может читать данные из 1C через созданную connection `OData ERP`.',
    '',
    '## Зачем это нужно',
    'Если простой запрос `Catalog_Контрагенты?$top=5` не работает в OData Master, не нужно строить pipeline. Сначала чините connection, публикацию OData, права пользователя или имя ресурса.',
    '',
    '## Что нужно заранее',
    '- Создана OData Connection `OData ERP`.',
    '- `Test $metadata` возвращает OK.',
    '- В 1C есть хотя бы несколько контрагентов, доступных пользователю `exchange_user`.',
    '',
    '## Пошаговая настройка',
    '1. Откройте `OData Master`.',
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
    '::checklist{id="pack-a-test-odata-explorer" items="Открыл OData Master|Выбрал OData ERP|Загрузил resources|Выбрал Catalog_Контрагенты|Поставил $top=5|Нажал Run query|Увидел несколько контрагентов"}',
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
    '1. Откройте `OData Master`.',
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
].map(withSelfCheck).map(withPedagogicalPass);

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
    '- В OData Master работает query contractor by INN.',
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
    '::common-mistakes{items="Save result as пустой или назван customer, а JSON Builder ожидает contractor|Required выключен и target JSON получает null|Value source указан как product_code|$select не содержит Ref_Key|Не проверили этот filter в OData Master"}',
    '',
    '## Вариант для `/master` Step 2A: найти заказ по номеру',
    'Если вы идете через новый Integration Master, после сохранения Input Contract откроется один OData Query Builder. Для заказа на производство используйте:',
    '',
    '```text',
    'Resource: Document_ЗаказНаПроизводство2_2',
    "Filter: Number eq '{{request.body.Number}}'",
    '$select: Ref_Key, Number, Date, Posted',
    '$top: 1',
    '$orderby: Date desc',
    'save_as: order',
    'required: true',
    '```',
    '',
    'Preview должен отрендерить sample value:',
    '',
    '```text',
    "Number eq '260666/6938'",
    '```',
    '',
    'После успешного test query следующие шаги смогут использовать `order.Ref_Key`. Если 1C вернула пустой список и `required=true`, test покажет `ODATA_RESULT_EMPTY`: проверьте точный номер, resource, OData connection и права пользователя 1C.',
    '',
    'Подробный разбор: [Найти заказ на производство по номеру](/docs/onec/academy/find-production-order-by-number).',
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
    '- В OData Master проверен resource номенклатуры и field `Артикул`.',
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
    '| Resource | `Catalog_Номенклатура` | Техническое имя из OData Master |',
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
    '| `get_product` failed | `odata.get_product.request.json`, OData Master для `Catalog_Номенклатура` | Выбрана ERP вместо WMS, поле `Артикул` называется иначе, product_code не существует |',
    '| `build_target_payload` failed | `target_payload.json` preview, JSON Builder mapping | Ошибка в source path, например `contractor.uuid` вместо `contractor.Ref_Key`, массив `codes` превращен в строку |',
    '| `send_to_dnp` failed | `target.request.json`, `target.response.json`, external error | Неверный connector `DNP Service`, неправильный path `/api/marking/pools`, 401/403 target API, timeout |',
    '',
    'Правило диагностики: если OData response пустой, сначала повторите тот же filter в OData Master. Если в Explorer тоже пусто, проблема не во Flow Builder, а в connection/resource/filter/data.',
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
  page('academy', 'request-response-workbench', 'Мастер запроса и ответа: внешний сервис → OMH → OData → ответ', 'Собрать понятную sync-интеграцию: внешний сервис вызывает OMH, OMH делает один или несколько OData-запросов и возвращает JSON, XML или raw text.', 116, mdLines(
    '# Мастер запроса и ответа: внешний сервис → OMH → OData → ответ',
    '',
    '::lesson-page{label="Академия интеграции 1C"}',
    '',
    'Этот урок про самый частый рабочий сценарий: не 1C вызывает внешний сервис, а внешний сайт, WMS, Telegram bot или внутренний API вызывает OMH. OMH принимает запрос, читает нужные поля, обращается в OData 1C и возвращает вызывающему сервису готовый ответ.',
    '',
    '::open-page{route="/test-console" label="Открыть мастер запроса и ответа"}',
    '::open-page{route="/odata-explorer" label="Проверить OData отдельно"}',
    '',
    '## Когда использовать этот мастер',
    '',
    'Используйте `Мастер запроса и ответа`, если caller ждёт результат сразу в HTTP response. Примеры: сайт спрашивает остаток, сервис просит статус заказа, WMS просит состав документа, мобильное приложение просит данные клиента.',
    '',
    'Не используйте sync-ответ для тяжёлых отчётов и долгих обменов. Если запрос может идти долго, выберите `accepted_event`: OMH быстро вернёт `event_id`, а результат нужно смотреть по Timeline, DLQ или отдельному callback.',
    '',
    '## Рабочая схема',
    '',
    '```text',
    'External service',
    '  POST /api/bus/in/lookup-order-products',
    '  { "Number": "260666/6938", "device_type": "toodoo" }',
    '',
    'OMH',
    '  1. принимает request',
    '  2. читает request.body.Number',
    '  3. OData ERP: ищет документ по Number',
    '  4. OData ERP: читает табличную часть по Ref_Key',
    '  5. собирает JSON/XML/raw response',
    '  6. возвращает response caller-у',
    '```',
    '',
    '## Шаг 1. Кто вызывает OMH',
    '',
    'Откройте `/test-console` и переключитесь в режим `Собрать интеграцию`. В первом блоке задайте:',
    '',
    '- `Source system`: кто будет вызывать OMH, например `External API / Website`.',
    '- `Integration name`: понятное имя, например `Lookup order products`.',
    '- `Endpoint slug`: короткий URL slug, например `lookup-order-products`.',
    '- `Auth`: `none` для внутреннего стенда или `static token`, если endpoint должен принимать только запросы с `X-OMH-Token`.',
    '',
    'Итоговый URL будет выглядеть так:',
    '',
    '```bash',
    'curl -X POST http://omh.example.local/api/bus/in/lookup-order-products \\',
    '  -H "Content-Type: application/json" \\',
    '  -d \'{"Number":"260666/6938","device_type":"toodoo"}\'',
    '```',
    '',
    '## Шаг 2. Что приходит во входящем запросе',
    '',
    'Выберите формат входа: `JSON`, `XML` или `raw text`.',
    '',
    'JSON пример:',
    '```json',
    '{',
    '  "operation": "lookup_order_products",',
    '  "Number": "260666/6938",',
    '  "device_type": "toodoo"',
    '}',
    '```',
    '',
    'XML пример:',
    '```xml',
    '<Request>',
    '  <Operation>lookup_order_products</Operation>',
    '  <Number>260666/6938</Number>',
    '  <DeviceType>toodoo</DeviceType>',
    '</Request>',
    '```',
    '',
    'После вставки примера мастер покажет извлечённые поля. Их можно вставлять в OData filter и response template через `{{...}}`, например `{{request.body.Number}}`.',
    '',
    '## Шаг 3. Что должен сделать OMH',
    '',
    'Для production-сценария сейчас используйте OData action. Сначала выбираете saved OData connection, затем resource, filter, select и имя переменной `Save as`.',
    '',
    'Первый OData-запрос ищет документ по номеру:',
    '```text',
    'Connection: OData ERP',
    'Resource: Document_ЗаказНаПроизводство2_2',
    '$filter: Number eq \'{{request.body.Number}}\'',
    '$select: Ref_Key,Number,Date,Posted',
    '$top: 1',
    'Save as: order',
    '```',
    '',
    'Второй OData-запрос читает табличную часть найденного документа:',
    '```text',
    'Connection: OData ERP',
    'Resource: Document_ЗаказНаПроизводство2_2(guid\'{{order.Ref_Key}}\')/Продукция',
    '$select: Ref_Key,LineNumber,Номенклатура_Key,Количество',
    '$top: 100',
    'Save as: products',
    '```',
    '',
    'Если нужно сначала проверить resource или filter отдельно, откройте `OData Master`, выполните query, затем вернитесь в мастер и перенесите проверенные значения.',
    '',
    '## Шаг 4. Что вернуть внешнему сервису',
    '',
    'Выберите response mode:',
    '',
    '| Mode | Когда выбирать | Что получает caller |',
    '| --- | --- | --- |',
    '| `sync_response` | Нужно вернуть свой бизнес-ответ после OData | JSON/XML/raw тело из response builder |',
    '| `proxy_response` | Нужно вернуть ответ целевого target почти без изменений | response target step |',
    '| `accepted_event` | Операция долгая, caller не должен ждать | `event_id`, `run_id`, `timeline_url` |',
    '',
    'JSON response:',
    '```json',
    '{',
    '  "success": true,',
    '  "order_uuid": "{{order.Ref_Key}}",',
    '  "order_number": "{{order.Number}}",',
    '  "products": "{{products}}"',
    '}',
    '```',
    '',
    'XML response:',
    '```xml',
    '<Response>',
    '  <Success>true</Success>',
    '  <OrderUUID>{{order.Ref_Key}}</OrderUUID>',
    '  <OrderNumber>{{order.Number}}</OrderNumber>',
    '</Response>',
    '```',
    '',
    'Raw text response:',
    '```text',
    'OK {{order.Ref_Key}}',
    '```',
    '',
    '## Шаг 5. Preview, create, test',
    '',
    'Нажмите `Preview / Dry Run`. Мастер не должен сразу ходить в production OData без необходимости: preview показывает, какие переменные будут прочитаны, какие OData шаги будут выполнены и какое response body получится.',
    '',
    'Когда preview понятен, нажмите `Create integration`. OMH создаст endpoint, route, flow/workflow и тестовый payload. После этого нажмите `Send test request` и откройте Timeline.',
    '',
    '## Что смотреть в Timeline',
    '',
    '| Artifact | Что доказывает |',
    '| --- | --- |',
    '| `incoming.request.json` | Caller реально прислал ожидаемый JSON/XML/raw |',
    '| `odata.request.json` | OMH собрал правильный OData URL, `$filter`, `$select`, `$top` |',
    '| `odata.response.json` | 1C вернула данные или пустой `value: []` |',
    '| `incoming_response.json` / `return_response.json` | OMH собрал именно тот ответ, который получил caller |',
    '',
    '## Частые ошибки',
    '',
    '- `products` пустой: первый OData step не нашёл `order.Ref_Key` или второй resource собран не от того документа.',
    '- Caller ждёт XML, а endpoint возвращает JSON: проверьте `Response body type` и `Content-Type`.',
    '- 401 от OMH: проблема во входном endpoint token, а не в OData password.',
    '- 401 от 1C OData: проблема в saved OData connection.',
    '- Timeout: sync response выбран для слишком тяжёлого запроса; переключите flow на `accepted_event` или сузьте `$select/$top`.',
    '',
    '## Проверьте себя',
    '::checklist{id="request-response-workbench" items="Понимаю, кто вызывает OMH|Вставил реальный sample request|Вижу извлечённые поля|Проверил OData connection|Настроил один или два OData step|Собрал JSON/XML/raw response|Сделал Preview|Создал integration|Запустил Send test request|Открыл Timeline и проверил artifacts"}',
  )),
].map(withSelfCheck).map(withPedagogicalPass);

export const academyPages: PageSeed[] = [
  page('academy', 'odata-integration-master', 'Мастер OData-интеграции', 'Как собрать входящий request -> OData -> JSON/XML/raw response или endpoint без raw builder JSON.', 5, mdLines(
    '# Мастер OData-интеграции',
    '',
    'Открывайте `/odata-explorer`, когда внешний сервис вызывает OMH, а OMH должен сходить в 1C OData, собрать ответ или отправить результат дальше.',
    '',
    '## Когда использовать',
    '- DnP, WMS, сайт или терминал отправляет JSON/XML/raw request в OMH.',
    '- Нужно найти документ в 1C OData по полю входящего запроса.',
    '- Нужно прочитать табличную часть 1C object resource.',
    '- Нужно выполнить OData foreach по массиву предыдущего шага.',
    '- Нужно вернуть JSON/XML/raw или отправить результат на endpoint.',
    '',
    '## Основной путь',
    '```text',
    'Входящий запрос -> OData-шаги -> Итоговое действие -> Проверка -> Сохранение',
    '```',
    '',
    '## Pagination',
    '`$top` не может быть больше 500. Для больших выборок включайте pagination: OMH использует `$skip` до `max_pages` из OData connection.',
    '',
    '## Timeline',
    'После сохранения нажмите `Run test`. Мастер покажет `event_id`, ссылку на Timeline и artifact checklist.',
    '',
    'Проверяйте artifacts `odata_query_request.json`, `odata_query_response.json`, `odata_query_result.json`, `foreach_result.json`, `outgoing_request.json` и `return_response.json`.',
    '',
    '::open-page{route="/odata-explorer" label="Открыть Мастер OData"}',
  )),
  page('academy', 'find-production-order-by-number', 'Найти заказ на производство по номеру', 'Step 2A в /master: один OData Query по Number, save_as=order и диагностика empty result.', 6, mdLines(
    '# Найти заказ на производство по номеру',
    '',
    '::lesson-page{label="Integration Master · Step 2A"}',
    '',
    '## Что вы настроите',
    'В `/master` после Input Contract вы добавите один OData Query: OMH возьмет `request.body.Number`, найдёт документ `Document_ЗаказНаПроизводство2_2` и сохранит первую строку как `order`.',
    '',
    '## Входящий sample',
    '```json',
    '{',
    '  "operation": "dnp_sinc_pull_codes",',
    '  "sinc": "dnp_sinc_pull_codes",',
    '  "order_name": "26-0666/6938",',
    '  "Number": "260666/6938"',
    '}',
    '```',
    '',
    '## OData Query Builder',
    '```text',
    'OData connection: 1C ERP OData',
    'Resource: Document_ЗаказНаПроизводство2_2',
    "Filter: Number eq '{{request.body.Number}}'",
    '$select: Ref_Key, Number, Date, Posted',
    '$top: 1',
    '$orderby: Date desc',
    'save_as: order',
    'required: true',
    '```',
    '',
    '## Preview',
    'Preview должен показать rendered filter:',
    '',
    '```text',
    "Number eq '260666/6938'",
    '```',
    '',
    'И переменные после шага:',
    '',
    '```text',
    'order.Ref_Key',
    'order.Number',
    'order.Date',
    'order.Posted',
    '```',
    '',
    '## Почему важен Ref_Key',
    '`Ref_Key` — ссылка 1C на документ. Если следующий шаг должен передать найденный заказ во внешний API или в 1C HTTP service, используйте `order.Ref_Key`, а не человекочитаемый номер.',
    '',
    '## Если результат пустой',
    '`ODATA_RESULT_EMPTY` означает, что запрос выполнился, но 1C вернула `value=[]`. Проверьте точный номер, resource, выбранную OData connection и права пользователя 1C.',
    '',
    '::checklist{id="find-production-order-by-number" items="Input Contract содержит request.body.Number|Выбрана OData connection|Resource Document_ЗаказНаПроизводство2_2|Filter Number eq request.body.Number|$select содержит Ref_Key|save_as=order|required=true|Preview показывает order.Ref_Key"}',
    '',
    '::next-lesson{label="Читаем табличную часть документа 1С" href="/docs/onec/academy/read-tabular-part"}',
  )),
  page('academy', 'read-tabular-part', 'Читаем табличную часть документа 1С через OData', 'Step 2B в /master: собрать Document_...(guid...)\/Продукция, протестировать и сохранить массив products.', 7, mdLines(
    '# Читаем табличную часть документа 1С через OData',
    '',
    '::lesson-page{label="Integration Master · Step 2B"}',
    '',
    '## Что такое табличная часть',
    'В документах 1С есть вложенные строки: товары, продукция, материалы, услуги. В OData они читаются как nested resource объекта.',
    '',
    '```text',
    "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция",
    '```',
    '',
    '`Document_ЗаказНаПроизводство2_2` — базовый resource документа. `order.Ref_Key` — внутренняя ссылка 1С на найденный объект. `Продукция` — имя табличной части.',
    '',
    '## Настройка Step 2B',
    '```text',
    'Какой объект 1С читать: order',
    'Поле ссылки 1С: Ref_Key',
    'Тип ключа: GUID',
    'Базовый OData Resource: Document_ЗаказНаПроизводство2_2',
    'Табличная часть / вложенный ресурс: Продукция',
    'Какие поля получить: Номенклатура_Key, Количество, КоличествоУпаковок',
    '$top: 100',
    'Сохранить строки как: products',
    'Ошибка, если строк нет: true',
    '```',
    '',
    '## Preview',
    'Template resource:',
    '',
    '```text',
    "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция",
    '```',
    '',
    'Rendered resource:',
    '',
    '```text',
    "Document_ЗаказНаПроизводство2_2(guid'c3335ee4-43d0-11f1-8388-000c29b755c7')/Продукция",
    '```',
    '',
    '## Result',
    'OMH сохранит массив как `products`.',
    '',
    '```text',
    'products[]',
    'products[0].Номенклатура_Key',
    'products[0].Количество',
    'products[0].КоличествоУпаковок',
    '```',
    '',
    'Следующий шаг сможет пройти по `products` и выполнить OData-запрос для каждой строки.',
    '',
    '## Empty result',
    'Если строк нет и `required=true`, test вернёт `ODATA_TABULAR_PART_EMPTY`. Проверьте `order.Ref_Key`, имя табличной части, права OData пользователя и базовый resource.',
    '',
    '::checklist{id="read-tabular-part" items="Выбрал order|Выбрал Ref_Key|Key type GUID|Указал Document_ЗаказНаПроизводство2_2|Указал Продукция|Preview показывает template и rendered resource|Test вернул products[]|Сохранил odata_object_query"}',
    '',
    '::next-lesson{label="Повторяем OData-запрос по каждой строке массива" href="/docs/onec/academy/foreach-odata-over-products"}',
  )),
  page('academy', 'foreach-odata-over-products', 'Повторяем OData-запрос по каждой строке массива', 'Step 2C в /master: пройти по products[], выполнить OData-запрос для каждой строки и сохранить общий codes[].', 8, mdLines(
    '# Повторяем OData-запрос по каждой строке массива',
    '',
    '::lesson-page{label="Integration Master · Step 2C"}',
    '',
    '## Зачем нужен Step 2C',
    'После Step 2A есть `order`, после Step 2B есть `products[]`. Step 2C проходит по массиву и для каждой строки выполняет вложенный OData-запрос.',
    '',
    '## Настройка DnP',
    '```text',
    'По какому массиву пройти: products',
    'Как назвать одну строку массива: product',
    'Resource: InformationRegister_ПулКодовМаркировкиСУЗ',
    '$top: 500',
    'Pagination: true',
    'Merge: flatten',
    'Save as: codes',
    'Required: true',
    '```',
    '',
    '## Filter',
    '```text',
    "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')",
    '```',
    '',
    '`product.Номенклатура_Key` берётся из текущей строки `products[]`. `order.Ref_Key` берётся из найденного заказа Step 2A.',
    '',
    '## Preview',
    'Preview берёт первую строку `products[]` и показывает rendered filter без запроса в 1С.',
    '',
    '```text',
    "Номенклатура_Key eq guid'ff22288c-2da4-11f1-8388-000c29b755c7' and ДокументОснование eq cast(guid'c3335ee4-43d0-11f1-8388-000c29b755c7', 'Document_ЗаказНаПроизводство2_2')",
    '```',
    '',
    '## Test',
    'Test выполняет вложенные OData-запросы в рамках `test_limit` и safety limits.',
    '',
    '```text',
    'source_count: 1',
    'items_processed: 1',
    'odata_requests: 1',
    'rows_found: 180',
    '```',
    '',
    'После успешного test/save будущие шаги смогут использовать:',
    '',
    '```text',
    'codes[]',
    'codes[0].КодМаркировки',
    'codes[0].Номенклатура_Key',
    '```',
    '',
    '## Merge modes',
    '`flatten` складывает все строки из всех ответов в один `codes[]`. Это режим по умолчанию для DnP.',
    '',
    '`group_by_item` сохраняет группы по исходной строке `products[]`.',
    '',
    '`first_per_item` берёт первую найденную строку на каждый `product`.',
    '',
    '## Safety limits',
    '```text',
    'max_items: 100',
    'max_requests: 100',
    'max_result_rows: 10000',
    '```',
    '',
    'Если `products[]` содержит больше строк, чем разрешено лимитами, validation остановит test до выполнения запросов в 1С.',
    '',
    '::checklist{id="foreach-odata-over-products" items="Выбрал products[]|item_as=product|Указал регистр пула кодов|Filter использует product.Номенклатура_Key|Filter использует order.Ref_Key|Merge flatten|save_as=codes|Safety limits заполнены|Test вернул rows_found"}',
  )),
  page('academy', 'final-action-send-or-return', 'Выбираем финальное действие', 'Step 4A в /master: вернуть ответ caller-у, отправить endpoint, проксировать endpoint response или принять async event.', 9, mdLines(
    '# Выбираем финальное действие',
    '',
    '::lesson-page{label="Integration Master · Step 4A"}',
    '',
    'Step 4A появляется после сохранения `build_payload`. Он отвечает на вопрос: что сделать с `target_payload`.',
    '',
    '## Варианты',
    '',
    '| Type | Когда использовать |',
    '| --- | --- |',
    '| `return_response` | Сразу вернуть JSON/XML/raw вызывающей системе. |',
    '| `send_endpoint` | Отправить `target_payload` во внешний endpoint и вернуть фиксированный/custom ответ. |',
    '| `send_and_return_response` | Отправить endpoint и проксировать его ответ caller-у. |',
    '| `accepted_event` | Вернуть `event_id`/`queue_item_id` и продолжить обработку асинхронно. |',
    '',
    '## Переменные',
    '',
    '```text',
    'target_payload',
    'request.body',
    'context.run_id',
    'context.event_id',
    'context.queue_item_id',
    '```',
    '',
    '`target_payload` должен быть создан Step 3A. Если его нет, вернитесь к payload builder и сохраните шаг.',
    '',
    '## Preview и Test',
    '',
    '`Preview final action` не отправляет запросы во внешние системы. Он показывает `would_send`, caller response и warnings.',
    '',
    '`Dry run` не ходит в сеть. `Real test endpoint` отправляет реальный HTTP request только после подтверждения в UI.',
    '',
    '## Что сохраняется',
    '',
    'Step 4A сохраняет один объект `final_action` в draft. Full integration compile, production endpoint, queue, retry/DLQ и Timeline runtime будут отдельными этапами.',
    '',
    '::next-lesson{label="Отправить результат во внешний endpoint" href="/docs/onec/academy/send-result-to-endpoint"}',
  )),
  page('academy', 'send-result-to-endpoint', 'Отправляем результат во внешний endpoint', 'Step 4A: настроить send_endpoint для target_payload, headers, body source, dry-run и real test.', 10, mdLines(
    '# Отправляем результат во внешний endpoint',
    '',
    'Используйте `send_endpoint`, когда Step 3A уже собрал `target_payload`, а внешний сервис должен получить этот body.',
    '',
    '## DnP пример',
    '',
    '```text',
    'Action type: send_endpoint',
    'Method: POST',
    'URL: http://172.16.3.10/api/v2/integrations/omh/chz/codes/import',
    'Headers: {"Content-Type":"application/json"}',
    'Body source: target_payload',
    'Body type: JSON',
    'Timeout: 30',
    'Return to caller: fixed_success {"ok": true}',
    '```',
    '',
    '## Headers',
    '',
    'Headers задаются JSON object. Secret refs можно описать как `{"Authorization":{"$secret":"dnp_api_token"}}`, но Step 4A пока не реализует secrets store.',
    '',
    '## Body source',
    '',
    '- `target_payload` отправляет результат payload builder.',
    '- `custom` даёт body-template с placeholders.',
    '- `none` полезен для `GET`/`DELETE` без body.',
    '',
    'Form body отключен. Сейчас поддержаны JSON, XML и raw text.',
    '',
    '## Private URL',
    '',
    '`localhost`, `127.0.0.1`, `10.*`, `172.16-31.*`, `192.168.*` разрешены, но preview покажет warning. Проверяйте доступность из backend-контейнера.',
    '',
    '## Проверка',
    '',
    'Сначала нажмите `Dry run`. Затем используйте `Real test endpoint`, если нужно отправить настоящий request. При `4xx/5xx` OMH показывает оригинальный target response.',
    '',
    '::next-lesson{label="Вернуть JSON/XML/raw response" href="/docs/onec/academy/return-json-or-xml-response"}',
  )),
  page('academy', 'return-json-or-xml-response', 'Возвращаем JSON, XML или raw response', 'Step 4A: настроить return_response, custom XML/raw body или proxy/accepted response.', 11, mdLines(
    '# Возвращаем JSON, XML или raw response',
    '',
    'Используйте `return_response`, когда caller должен получить синхронный ответ от OMH без target endpoint.',
    '',
    '## JSON из target_payload',
    '',
    '```text',
    'Action type: return_response',
    'Body source: target_payload',
    'Response type: JSON',
    'HTTP status: 200',
    'Headers: {"Content-Type":"application/json"}',
    '```',
    '',
    '## Custom XML',
    '',
    '```xml',
    '<Response>',
    '  <Order>{{request.body.order_name}}</Order>',
    '  <Codes>{{codes.length}}</Codes>',
    '</Response>',
    '```',
    '',
    'Для XML поставьте `Response type: XML` и header `Content-Type: application/xml`.',
    '',
    '## Raw response',
    '',
    '```text',
    'OK order={{request.body.order_name}} codes={{codes.length}}',
    '```',
    '',
    'Если нужно отправить endpoint и вернуть его ответ, используйте `send_and_return_response`. Если caller не должен ждать выполнения, используйте `accepted_event`.',
    '',
    '::checklist{id="final-action-return-response" items="Выбрал return_response|Проверил target_payload или custom body|Выставил status code|Указал Content-Type|Сделал Preview|Сделал Dry run"}',
  )),
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
      'Введите username: `exchange_erp_training`. Пароль храните через `$secret:onec.erp.password`. Для временного учебного стенда можно использовать простой пароль, но явно помечайте такое подключение как test-only.',
      'Сохраните connection.',
      'Нажмите Test $metadata и дождитесь HTTP 200 или понятной внешней ошибки.'
    ],
    example: `~~~json
{
  "name": "OData ERP training",
  "base_url": "http://erp-demo/ERP/odata/standard.odata",
  "auth_type": "basic",
  "username": "exchange_erp_training",
  "password": { "$secret": "onec.erp.password" },
  "default_top": 50,
  "max_pages": 5
}
~~~`,
    expected: [
      'В списке OData Connections появился `OData ERP training`.',
      'Metadata test показывает success или точную ошибку 1C.',
      'Connection доступен в OData Master и Flow Builder.'
    ],
    mistakes: [
      'Указывать URL базы без `/odata/standard.odata`.',
      'Создавать raw Connector вместо OData Connection для каждого flow.',
      'Оставлять пароль `123` в production вместо Secrets Store.'
    ],
    checklist: ['Создал OData connection', 'Проверил base URL', 'Проверил $metadata', 'Понял где хранить пароль'],
    next: '[Урок 03 — Проверяем OData-запрос в OData Master](/docs/onec/academy/lesson-03-test-odata-in-odata-explorer).'
  }),
  lesson({
    slug: 'lesson-03-test-odata-in-odata-explorer',
    order: 30,
    title: 'Урок 03 — Проверяем OData-запрос в OData Master',
    description: 'Проверка resource, filter, select и sample response до настройки flow.',
    build: 'Вы выполните первый запрос к `Catalog_Контрагенты` и сохраните точные поля, которые потом нужны для contractor lookup.',
    why: 'Flow не должен быть местом угадывания имен ресурсов. Сначала пользователь проверяет запрос в Explorer и только потом переносит его в builder.',
    before: ['Пройден урок 02.', 'Есть OData connection `OData ERP training`.', 'Пользователь 1C имеет права читать справочник контрагентов.'],
    steps: [
      'Откройте OData Master.',
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
    before: ['Пройден урок 05.', 'В OData Master проверен filter для `Catalog_Контрагенты`.', 'В flow есть variable \`inn\`.'],
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
      'Писать filter вручную иначе, чем он прошел в OData Master.'
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
    before: ['Пройден урок 06.', 'В OData Master проверен resource номенклатуры.', 'В flow есть variable \`product_code\`.'],
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
    before: ['Пройден урок 11.', 'Есть доступ к Timeline, OData Connections, OData Master и DLQ.', 'Пользователь понимает разницу inbound token, OData credentials и target API auth.'],
    steps: [
      'Если входной endpoint вернул 401, проверьте \`X-OMH-Token\`.',
      'Если OData вернула 401, проверьте OData Connection credentials или secret.',
      'Если resource не найден, откройте OData Master и выберите resource из metadata.',
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
      'Менять flow filter, не проверив его в OData Master.',
      'Удалять DLQ событие до разбора artifacts.'
    ],
    checklist: ['Понял 401 inbound', 'Понял 401 OData', 'Понял empty lookup', 'Понял target error', 'Понял DLQ replay']
  }),
  page('academy', 'xml-input-to-odata-to-xml-response', 'XML-вход → OData → XML-ответ', 'Пошаговый учебный сценарий: внешний сервис отправляет XML, OMH ищет данные в 1C OData и возвращает XML.', 190, mdLines(
    '# XML-вход → OData → XML-ответ',
    '',
    'Цель урока: собрать интеграцию от реальной задачи, а не от технических терминов. Внешний сервис вызывает OMH, OMH понимает XML, берет номер документа, делает OData-запрос в 1C и сразу возвращает XML-ответ.',
    '',
    '## Схема',
    '```text',
    'External service',
    '  -> POST /api/bus/in/lookup-order-products',
    '  -> XML Toolkit: /Request/Number -> number',
    "  -> OData ERP: Document_ЗаказНаПроизводство2_2?$filter=Number eq '{{number}}'",
    '  -> XML Response Builder',
    '  -> XML response to caller',
    '```',
    '',
    '## 1. Вставьте входящий XML',
    '```xml',
    '<Request>',
    '  <Operation>lookup_order_products</Operation>',
    '  <Number>260666/6938</Number>',
    '  <DeviceType>toodoo</DeviceType>',
    '</Request>',
    '```',
    '',
    'Откройте Request/Response Workbench, выберите `Input mode = XML` и вставьте пример. Ниже появится XML Path Picker. Нажмите `Use this field` у `/Request/Number`.',
    '',
    '## 2. Проверьте переменную',
    'После выбора поля Workbench создаст шаг:',
    '```json',
    '{',
    '  "type": "xml_extract",',
    '  "source": "request.xml",',
    '  "fields": [{ "name": "number", "path": "/Request/Number", "required": true }]',
    '}',
    '```',
    '',
    'Теперь в следующих шагах можно использовать `{{number}}`.',
    '',
    '## 3. Настройте OData',
    'Выберите OData connection, например `OData ERP production`. Resource укажите из OData Master, не из памяти.',
    '',
    '| Поле | Значение |',
    '| --- | --- |',
    '| Resource | `Document_ЗаказНаПроизводство2_2` |',
    '| $filter | `Number eq \'{{number}}\'` |',
    '| $select | `Ref_Key,Number,Date,Posted` |',
    '| $top | `1` |',
    '| Save as | `order` |',
    '',
    '## 4. Соберите XML-ответ',
    '```xml',
    '<Response>',
    '  <Success>true</Success>',
    '  <OrderRef>{{order.Ref_Key}}</OrderRef>',
    '  <OrderNumber>{{order.Number}}</OrderNumber>',
    '</Response>',
    '```',
    '',
    'XML Response Builder проверит, что итоговый XML валиден. Если переменная отсутствует, будет понятная ошибка `Missing XML template variables`.',
    '',
    '## 5. Проверьте Preview и Timeline',
    'В Preview должны быть шаги `xml_extract`, `get_order`, `return_response`. После live test откройте Timeline и проверьте artifacts: `xml_parse_input.xml`, `xml_parse_tree.json`, `xml_extracted_fields.json`, `odata_query_request.json`, `xml_response_rendered.xml`.',
    '',
    '::open-page{route="/test-console" label="Открыть Request/Response Workbench"}',
    '::checklist{id="academy-xml-odata-xml-response" items="Вставил XML sample|Выбрал /Request/Number|Проверил переменную number|Настроил OData filter|Собрал XML response|Сделал Preview|Проверил Timeline artifacts"}'
  )),
].map(withSelfCheck).map(withPedagogicalPass);

export const referencePages: PageSeed[] = [
  page('reference', 'integration-master', 'Reference — Integration Master', 'Первый шаг мастера: scenario chooser, sample parser и Input Contract.', 4, md(`
# Reference — Integration Master

\`/master\` — общий мастер интеграции. В первом шаге пользователь выбирает сценарий, формат входящего запроса и пример body.

Результат шага — \`InputContract\`: fields, route key, business key и endpoint slug.

## Endpoints

~~~text
GET  /api/integration-master/scenarios
POST /api/integration-master/input/parse
POST /api/integration-master/input/validate
POST /api/integration-master/input/save-draft
GET  /api/integration-master/drafts/{draft_id}
POST /api/integration-master/odata-step/preview
POST /api/integration-master/odata-step/test
POST /api/integration-master/odata-step/validate
POST /api/integration-master/drafts/{draft_id}/odata-steps
POST /api/integration-master/odata-object-step/preview
POST /api/integration-master/odata-object-step/test
POST /api/integration-master/odata-object-step/validate
POST /api/integration-master/drafts/{draft_id}/odata-object-steps
POST /api/integration-master/foreach-odata-step/preview
POST /api/integration-master/foreach-odata-step/test
POST /api/integration-master/foreach-odata-step/validate
POST /api/integration-master/drafts/{draft_id}/foreach-odata-steps
~~~

## Что поддерживает step 1

- JSON paths: \`request.body.operation\`.
- Arrays: \`request.body.items[]\`, \`request.body.items[0].sku\`.
- XML paths: \`xml./Документ/Номер\`.
- Raw text: \`request.raw_text\` и простые \`key=value\`.
- Endpoint slug validation.
- Draft сохранение без создания боевой интеграции.
- Step 2A: один OData Query после Input Contract.
- Step 2B: чтение табличной части найденного объекта 1С.
- Step 2C: повтор OData-запроса по массиву, например \`products[] -> codes[]\`.

## Step 2A OData example

~~~text
Resource: Document_ЗаказНаПроизводство2_2
Filter: Number eq '{{request.body.Number}}'
$select: Ref_Key, Number, Date, Posted
$top: 1
$orderby: Date desc
save_as: order
required: true
~~~

Preview на sample \`Number=260666/6938\` должен показать:

~~~text
Number eq '260666/6938'
~~~

После test query следующие шаги смогут использовать \`order.Ref_Key\`. Если результат пустой и \`required=true\`, test вернёт \`ODATA_RESULT_EMPTY\`.

## Step 2B OData object example

~~~text
Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция
~~~

Config:

~~~text
object_variable: order
key_field: Ref_Key
key_type: guid
base_resource: Document_ЗаказНаПроизводство2_2
nested_resource: Продукция
$select: Номенклатура_Key, Количество, КоличествоУпаковок
save_as: products
required: true
~~~

Future variables:

~~~text
products[]
products[0].Номенклатура_Key
products[0].Количество
products[0].КоличествоУпаковок
~~~

Пустая табличная часть при \`required=true\` возвращает \`ODATA_TABULAR_PART_EMPTY\`.

## Step 2C foreach OData example

~~~text
items: products
item_as: product
Resource: InformationRegister_ПулКодовМаркировкиСУЗ
Filter: Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')
$top: 500
paginate: true
merge: flatten
save_as: codes
~~~

Future variables:

~~~text
codes[]
codes[0].КодМаркировки
codes[0].Номенклатура_Key
~~~

Validation контролирует source array, \`$top <= 500\`, \`save_as\` collision и safety limits: \`max_items\`, \`max_requests\`, \`max_result_rows\`.

## Non-goals

На текущих шагах не создаются JSON/XML builder, response builder, final action, full integration save и Timeline.

::open-page{route="/master" label="Открыть Мастер интеграции"}
`)),
  page('reference', 'odata-master', 'Reference - OData Master', 'Wizard spec, backend API и compilation в Integration Flow.', 5, md(`
# Reference - OData Master

Backend endpoints:

~~~text
GET  /api/odata-master/examples
POST /api/odata-master/preview
POST /api/odata-master/save
POST /api/odata-master/run-test
~~~

Все endpoints относятся к package \`omh-package-onec\`.

## Step types

- \`odata_query\`
- \`odata_object_query\`
- \`foreach_odata\`

## Final actions

- \`return_response\`
- \`send_endpoint\`
- \`send_onec_http_service\`
- \`async_accepted\`

Compiler создает обычный \`IntegrationFlow\`: endpoint, route, compiled workflow, builder_json и saved test case.

## Limits

- \`$top <= 500\`.
- Pagination использует \`$skip\` до \`max_pages\` из OData connection.
- Exact JSON placeholder \`"{{codes}}"\` сохраняет массив/object тип.
`)),
  page('reference', 'odata-connection', 'Reference — OData Connection', 'Что хранит OData connection и где он используется.', 10, md(`
# Reference — OData Connection

OData Connection — сохраненное подключение к конкретной публикации 1C OData. Пользователь создает его один раз, а потом выбирает из списка в OData Master и Flow Builder.

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
  page('reference', 'xml-toolkit', 'Reference — XML Toolkit', 'Парсер XML, выбор path, извлечение переменных, XML response и raw forwarding.', 55, md(`
# Reference — XML Toolkit

XML Toolkit — не отдельный сценарий интеграции. Это общий слой, который используют Request/Response Workbench, 1C Cockpit, Visual Flow Builder и advanced XML Tools.

## Когда пользователь видит XML Toolkit
- Входящий request имеет input mode \`xml\`.
- Нужно выбрать поле XML и использовать его в OData filter.
- Нужно вернуть caller XML response.
- Нужно переслать XML в 1C HTTP service без изменения тела.

## Основные возможности
| Возможность | Где используется | Что дает |
| --- | --- | --- |
| Parse XML | Workbench, Cockpit, XML Tools | root, encoding, namespaces, preview tree |
| Path Picker | Workbench, Flow Builder | путь вида \`/Request/Number\` |
| xml_extract | runtime step | переменные \`number\`, \`operation\`, \`device_type\` |
| XML Response Builder | Workbench, Flow Builder | валидный XML из шаблона и variables |
| Raw XML forward | Flow Builder, Cockpit | SHA256 до/после и доказательство, что тело не менялось |

## Пример входящего XML
~~~xml
<Request>
  <Operation>lookup_order_products</Operation>
  <Number>260666/6938</Number>
  <DeviceType>toodoo</DeviceType>
</Request>
~~~

Path Picker покажет:

| Path | Variable |
| --- | --- |
| \`/Request/Operation\` | \`operation\` |
| \`/Request/Number\` | \`number\` |
| \`/Request/DeviceType\` | \`device_type\` |

## Runtime step
~~~json
{
  "id": "extract_xml_fields",
  "type": "xml_extract",
  "source": "request.xml",
  "fields": [
    { "name": "number", "path": "/Request/Number", "required": true, "mode": "first" }
  ]
}
~~~

После этого OData filter может использовать:

~~~text
Number eq '{{number}}'
~~~

## XML response
~~~xml
<Response>
  <Success>true</Success>
  <OrderRef>{{order.Ref_Key}}</OrderRef>
  <OrderNumber>{{order.Number}}</OrderNumber>
</Response>
~~~

OMH экранирует значения XML-переменных, валидирует итоговый XML и сохраняет artifacts:
- \`xml_response_template.xml\`;
- \`xml_response_rendered.xml\`;
- \`return_response.json\`.

::open-page{route="/test-console" label="Открыть Request/Response Workbench"}
::checklist{id="reference-xml-toolkit" items="Понял, что XML Toolkit встроен в мастера|Выбрал XML path|Создал переменную|Использовал переменную в OData|Собрал XML response|Проверил XML artifacts"}
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

type SymptomPageConfig = {
  slug: string;
  title: string;
  description: string;
  order: number;
  whatYouSee: string[];
  meaning: string;
  quickFix: string;
  checklist: string[];
  where: string[];
  exampleLanguage: string;
  example: string[];
  related: string[];
};

function russianSymptomExplanation(slug: string): string {
  const explanations: Record<string, string> = {
    'odata-empty-result': 'По-русски: OMH дошел до 1C, авторизация и ресурс сработали, но фильтр не нашел ни одной строки. Не меняйте весь flow. Сначала откройте `odata_query_request`, скопируйте filter в OData Master и проверьте value из `incoming.request.json`.',
    'onec-returned-401': 'По-русски: Неверный логин или пароль для подключения к 1C, если failed step — `odata_query`; неверный `X-OMH-Token`, если failed step — `receive`; неверные credentials target-сервиса, если failed step — `call_endpoint`.',
    'event-moved-to-dlq': 'По-русски: DLQ — это не причина ошибки, а безопасная остановка после неуспешных попыток. Причина находится в первом failed step Timeline и его artifacts. Сначала исправьте данные, secret, config или target, потом делайте Replay from DLQ.',
  };
  return explanations[slug] ?? 'По-русски: начните не с общего сообщения об ошибке, а с первого failed step в Timeline. Он показывает владельца проблемы: входной endpoint, OData, JSON Builder, target API, очередь или принтер.';
}

function symptomPage(config: SymptomPageConfig): PageSeed {
  return page('troubleshooting', config.slug, config.title, config.description, config.order, mdLines(
    `# ${config.title}`,
    '',
    '## What you see',
    ...config.whatYouSee,
    '',
    '## What it means',
    config.meaning,
    '',
    '### По-русски для пользователя 1C',
    russianSymptomExplanation(config.slug),
    '',
    '## Quick fix',
    config.quickFix,
    '',
    '## Full checklist',
    ...config.checklist.map((item) => `- ${item}`),
    '',
    '## Where to look in OMH',
    ...config.where.map((item) => `- ${item}`),
    '',
    '## Example',
    `~~~${config.exampleLanguage}`,
    ...config.example,
    '~~~',
    '',
    '## Related lessons',
    ...config.related.map((item) => `- ${item}`),
  ));
}

const troubleshootingIndex = page('troubleshooting', 'index', 'Troubleshooting по симптомам', 'Начинайте диагностику с того, что видит пользователь: пустой OData result, 401, 404, DLQ, очередь или печать.', 1, mdLines(
  '# Troubleshooting по симптомам',
  '',
  'Эта страница нужна для первой диагностики. Пользователь обычно не знает код ошибки OMH и не должен начинать с внутренней терминологии. Начинайте с того, что видно на экране 1С, в Test Console, Timeline, Queue, DLQ или Printing.',
  '',
  '::open-page{route="/test-console" label="Открыть Test Console"}',
  '::open-page{route="/events" label="Открыть Event Timeline"}',
  '::open-page{route="/runtime/dlq" label="Открыть DLQ"}',
  '::open-page{route="/odata-explorer" label="Открыть OData Master"}',
  '',
  '## Connection/OData',
  '- [OData connection test failed](/docs/onec/troubleshooting/odata-connection-test-failed)',
  '- [1C returned 401 Unauthorized](/docs/onec/troubleshooting/onec-returned-401)',
  '- [OData metadata does not load](/docs/onec/troubleshooting/odata-metadata-does-not-load)',
  '- [OData resource not found](/docs/onec/troubleshooting/odata-resource-not-found)',
  '- [OData query returns empty result](/docs/onec/troubleshooting/odata-empty-result)',
  '- [Contractor not found by INN](/docs/onec/troubleshooting/contractor-not-found-by-inn)',
  '- [Product not found by article](/docs/onec/troubleshooting/product-not-found)',
  '',
  '## Endpoint/Request',
  '- [1C receives 404 from OMH](/docs/onec/troubleshooting/omh-404-from-1c)',
  '- [1C receives 401/403 from OMH](/docs/onec/troubleshooting/omh-401-403-from-1c)',
  '- [Endpoint exists but route did not match](/docs/onec/troubleshooting/route-did-not-match)',
  '- [Request body is not valid JSON](/docs/onec/troubleshooting/invalid-json-body)',
  '- [XML parse failed](/docs/onec/troubleshooting/xml-parse-error)',
  '',
  '## Pipeline',
  '- [OData step failed](/docs/onec/troubleshooting/odata-step-failed)',
  '- [JSON Builder variable missing](/docs/onec/troubleshooting/json-builder-variable-missing)',
  '- [Business Rule stopped flow](/docs/onec/troubleshooting/business-rule-stopped-flow)',
  '- [Target connector not found](/docs/onec/troubleshooting/target-connector-not-found)',
  '- [External API returned error](/docs/onec/troubleshooting/target-api-returned-error)',
  '',
  '## Runtime',
  '- [Event stuck in queue](/docs/onec/troubleshooting/event-stuck-in-queue)',
  '- [Event moved to DLQ](/docs/onec/troubleshooting/event-moved-to-dlq)',
  '- [Retry does not happen](/docs/onec/troubleshooting/retry-does-not-happen)',
  '- [Worker is not processing](/docs/onec/troubleshooting/worker-not-processing)',
  '',
  '## Printer',
  '- [Printer unavailable](/docs/onec/troubleshooting/printer-unavailable)',
  '- [ZPL sent but label wrong](/docs/onec/troubleshooting/zpl-label-wrong)',
  '- [Print job created but not printed](/docs/onec/troubleshooting/print-job-not-printed)',
  '',
  '## Как пользоваться',
  '1. Найдите строку, похожую на то, что видит пользователь.',
  '2. Откройте страницу симптома.',
  '3. Сделайте Quick fix.',
  '4. Если не помогло, пройдите Full checklist.',
  '5. После исправления откройте Timeline и убедитесь, что artifacts показывают новый успешный run.',
));

export const troubleshootingPages: PageSeed[] = [
  troubleshootingIndex,
  symptomPage({ slug: 'odata-connection-test-failed', title: 'Symptom: OData connection test failed', description: 'Test metadata or connection healthcheck does not pass for a 1C OData profile.', order: 10, whatYouSee: ['- OData Connections page shows failed Test metadata.', '- OData Master cannot load resources for the selected connection.', '- Flow OData step fails before it can build a filter.'], meaning: 'OMH cannot reliably reach the selected 1C OData publication. This is connection-level: URL, network, credentials, SSL, publication path or 1C user rights.', quickFix: 'Open OData Connections, run Test metadata for the same profile, then fix the first reported external error before editing the flow.', checklist: ['Base URL ends with the actual OData publication, for example `/odata/standard.odata`.', 'The URL is reachable from the OMH backend/container network.', 'Username and password or secret reference are valid.', 'SSL verification matches the real certificate setup.', 'The 1C user can read metadata and required catalogs.', 'You are testing the same environment where the flow runs.'], where: ['OData Connections -> selected profile -> Test metadata.', 'Secrets Store -> referenced password exists.', 'Timeline -> failed `odata_query` step if the failure happened inside a flow.', 'Health page if connection healthcheck is enabled.', 'Audit log if the profile changed recently.'], exampleLanguage: 'json', example: ['{', '  "status": "failed",', '  "error": "OData metadata request failed",', '  "url": "http://1c-server/erp/odata/standard.odata/$metadata"', '}'], related: ['[Создаём OData-подключение к 1С](/docs/onec/academy/create-odata-connection)', '[Проверяем OData-запрос в OData Master](/docs/onec/academy/test-odata-explorer)', '[Reference — OData Connection](/docs/onec/reference/odata-connection)'] }),
  symptomPage({ slug: 'onec-returned-401', title: 'Symptom: 1C returned 401 Unauthorized', description: 'How to separate inbound OMH auth from OData/target 1C authentication failures.', order: 20, whatYouSee: ['- OData Master shows `401 Unauthorized`.', '- Timeline step `get_contractor` or `get_product` failed with 401.', '- 1C HTTP service target returned 401 to `send_to_dnp` or another call step.'], meaning: 'A 401 means authentication failed, but the owner depends on the failed step. OData 401 belongs to the OData Connection. Inbound 401 from OMH belongs to endpoint token. Target 1C 401 belongs to target connector credentials.', quickFix: 'Open the failed Timeline step first. If it is OData, run Test metadata on that OData Connection. If it is receive, check `X-OMH-Token` from 1C.', checklist: ['Failed step is identified: `receive`, `odata_query`, or `call_endpoint`.', 'Inbound `X-OMH-Token` is correct for `/api/bus/in/{slug}`.', 'OData username/password secret is valid.', '1C OData user has read rights for the catalog/document.', 'Target connector auth is not confused with inbound token.', 'Secrets exist in the current environment after promotion.'], where: ['Timeline -> first failed step.', '`incoming.request.headers` for inbound auth, with secrets redacted.', '`odata_query_request` and `odata_query_response` for OData auth.', '`target.response.json` for target 1C HTTP service auth.', 'OData Connections -> Test metadata.'], exampleLanguage: 'json', example: ['{', '  "status": 401,', '  "error": "Unauthorized",', '  "step": "get_contractor"', '}'], related: ['[Создаём OData-подключение к 1С](/docs/onec/academy/create-odata-connection)', '[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts)', '[Secrets Store](/docs/onec/reference/secrets)'] }),
  symptomPage({ slug: 'odata-metadata-does-not-load', title: 'Symptom: OData metadata does not load', description: 'The `$metadata` document cannot be loaded or parsed.', order: 30, whatYouSee: ['- OData Master resources list is empty.', '- Test metadata returns timeout, 404, 500, certificate error or invalid XML.', '- Flow cannot show resources for OData Query step.'], meaning: 'OMH needs `$metadata` to know exact resource and field names. If metadata does not load, do not guess `Catalog_...` names in Flow Builder.', quickFix: 'Open the exact metadata URL from OData Connection and fix publication/network/auth until `$metadata` loads successfully.', checklist: ['OData publication is enabled in 1C.', 'Base URL is not a web client URL.', 'The metadata URL is `${base_url}/$metadata` or the platform equivalent.', 'Reverse proxy does not strip auth headers.', 'Response is XML metadata, not an HTML login page.', 'Resource list reloads after 1C publication changes.'], where: ['OData Connections -> Test metadata details.', 'OData Master -> resource loader.', 'Browser/curl from OMH host if available.', 'Timeline only if failure happens during flow preview.', '1C web server publication settings.'], exampleLanguage: 'text', example: ['GET http://1c-server/erp/odata/standard.odata/$metadata', 'Expected: 200 application/xml', 'Bad: 200 text/html login page or 404 Not Found'], related: ['[Проверяем OData-запрос в OData Master](/docs/onec/academy/test-odata-explorer)', '[Глубокий курс OData](/docs/onec/odata-course/what-is-odata-for-omh)', '[OData resource not found](/docs/onec/troubleshooting/odata-resource-not-found)'] }),
  symptomPage({ slug: 'odata-resource-not-found', title: 'Symptom: OData resource not found', description: 'Resource is missing from metadata or the wrong OData base is selected.', order: 40, whatYouSee: ['- Flow OData step fails with resource not found.', '- OData Master does not contain `Catalog_Контрагенты` or `Catalog_Номенклатура`.', '- Timeline request contains a resource name that 1C rejects.'], meaning: 'The selected 1C OData base does not publish the resource used by the flow, or the resource technical name is different from the name typed in the step.', quickFix: 'Reload resources in OData Master for the same connection and copy the resource name from the list, not from memory.', checklist: ['Correct OData connection selected.', 'Resource is copied from metadata.', 'Object is published in 1C OData.', 'Base URL points to the intended ERP/WMS/УСП base.', 'Flow draft was republished after resource fix.', 'Metadata cache was refreshed after 1C changes.'], where: ['OData Master -> resources list.', 'Timeline -> `odata_query_request`.', 'Flow Builder -> OData Query step settings.', 'Config History if the resource changed recently.', '1C publication settings.'], exampleLanguage: 'json', example: ['{', '  "resource": "Catalog_Контрагенты",', '  "error": "Resource not found in metadata"', '}'], related: ['[Проверяем OData-запрос в OData Master](/docs/onec/academy/test-odata-explorer)', '[Как выбрать OData-подключение в интеграционном потоке](/docs/onec/odata-course/select-connection-in-flow)', '[Reference — Integration Flow](/docs/onec/reference/integration-flow)'] }),
  symptomPage({ slug: 'odata-empty-result', title: 'Symptom: OData query returns empty result', description: 'OMH reached 1C successfully, but the OData filter returned no rows.', order: 50, whatYouSee: ['~~~json', '{', '  "value": []', '}', '~~~', '- Timeline may show `ODATA_LOOKUP_NOT_FOUND`.', '- Required OData step stops the flow before JSON Builder or target call.'], meaning: 'OMH reached 1C successfully, but 1C did not return matching records. This is usually filter, value, field, base, permissions or data quality.', quickFix: 'Copy the generated filter from Timeline and run it in OData Master.', checklist: ['Correct OData connection selected.', 'Correct resource selected.', 'Correct field name from metadata.', 'Value has no spaces or hidden characters.', 'Field is visible to the OData user.', 'Object is not marked for deletion.', 'Using correct 1C base.', 'Try `$top=5` without filter.'], where: ['Timeline -> OData step.', 'Artifact `odata_query_request`.', 'Artifact `odata_query_response`.', 'OData Master with the same connection.', 'Incoming request artifact to compare the raw value.'], exampleLanguage: 'text', example: ['ODATA_LOOKUP_NOT_FOUND', "Catalog_Контрагенты?$filter=ИНН eq '7707083893'&$top=1", 'Response: { "value": [] }'], related: ['[Как строить $filter](/docs/onec/odata-course/filter-basics)', '[Ищем контрагента по ИНН](/docs/onec/academy/find-contractor-by-inn)', '[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts)'] }),
  symptomPage({ slug: 'contractor-not-found-by-inn', title: 'Symptom: Contractor not found by INN', description: 'Contractor lookup returned an empty OData result.', order: 60, whatYouSee: ['- `get_contractor` failed or returned empty result.', '- `contractor_uuid` is missing from target JSON.', '- Timeline has empty `odata.get_contractor.response.json`.'], meaning: 'The contractor may exist in another 1C base, the INN may be formatted differently, or the OData user cannot see the contractor.', quickFix: 'Copy `request.body.inn` and the generated contractor filter into OData Master, then test without filter using `$top=5`.', checklist: ['Incoming path is `request.body.inn`.', 'INN is trimmed and contains no non-breaking spaces.', 'Field is `ИНН` or the actual metadata field.', 'Resource is the contractor catalog for this configuration.', 'OData connection points to the base where the contractor exists.', 'Contractor is not marked for deletion.', 'User has catalog read rights.'], where: ['Timeline -> `incoming.request.json`.', 'Timeline -> `odata.get_contractor.request.json`.', 'Timeline -> `odata.get_contractor.response.json`.', 'OData Master contractor query.', 'Transform output before lookup.'], exampleLanguage: 'json', example: ['{', '  "inn": "7707083893",', '  "contractor": null,', '  "error": "ODATA_LOOKUP_NOT_FOUND"', '}'], related: ['[Ищем контрагента по ИНН](/docs/onec/academy/find-contractor-by-inn)', '[Первая выборка OData: контрагент по ИНН](/docs/onec/academy/first-odata-query-contractor)', '[OData query returns empty result](/docs/onec/troubleshooting/odata-empty-result)'] }),
  symptomPage({ slug: 'product-not-found', title: 'Symptom: Product not found by article', description: 'Product lookup by product_code/article returned an empty result.', order: 70, whatYouSee: ['- `get_product` failed or returned empty result.', '- JSON Builder cannot fill `product_uuid`.', '- Product exists in 1C UI but not through selected OData query.'], meaning: 'The product lookup does not match the actual product storage: wrong base, wrong field, article formatting, missing publication or access rights.', quickFix: 'Open OData Master on the same connection and try `Catalog_Номенклатура?$top=5`, then add the article filter.', checklist: ['Input value comes from `request.body.product_code`.', 'Field is `Артикул`, `Code`, SKU or actual metadata field.', 'Connection is ERP/WMS where product really lives.', 'Case and spaces are normalized.', 'Product variant/barcode is not confused with article.', 'OData user can read nomenclature.'], where: ['Timeline -> `odata.get_product.request.json`.', 'Timeline -> `odata.get_product.response.json`.', 'OData Master resources/fields.', 'Flow Builder second OData step.', 'Transform output before product lookup.'], exampleLanguage: 'text', example: ["Catalog_Номенклатура?$filter=Артикул eq 'ABC-123'&$top=1", 'Response: { "value": [] }'], related: ['[Вторая выборка OData: товар по артикулу](/docs/onec/academy/second-odata-query-product)', '[Как строить $filter](/docs/onec/odata-course/filter-basics)', '[Recipe 2 two OData queries](/docs/onec/recipes/recipe-02-onec-post-two-odata-lookups)'] }),
  symptomPage({ slug: 'omh-404-from-1c', title: 'Symptom: 1C receives 404 from OMH', description: '1C calls OMH but receives Not Found.', order: 80, whatYouSee: ['- 1C HTTPСоединение returns 404.', '- Browser or curl shows `Not Found`.', '- No new event appears in Event Journal.'], meaning: 'The request did not reach a valid inbound endpoint route. It may be wrong slug, disabled package route, wrong API host, frontend URL instead of backend API URL, or `/api/bus/in/{slug}` does not exist.', quickFix: 'Copy the endpoint URL from Integration Bus or Flow Builder and use the backend API URL, not the frontend documentation URL.', checklist: ['Endpoint slug matches exactly.', 'Path is `/api/bus/in/{slug}`.', 'You are using backend API host/port.', 'Package route is installed and enabled.', 'Flow endpoint is published/enabled.', 'Reverse proxy routes `/api` to backend.', 'Auth package is not confused with integration endpoint auth.'], where: ['Integration Bus -> endpoints list.', 'Flow Builder -> generated endpoint URL.', 'Test Console endpoint selector.', 'Event Journal to confirm whether request created an event.', 'Reverse proxy logs if external URL is used.'], exampleLanguage: 'text', example: ['Bad:  POST http://omh-ui.example.local/docs/onec/endpoint', 'Bad:  POST http://omh-server:8000/api/bus/onec-pool-to-dnp', 'Good: POST http://omh-server:8000/api/bus/in/onec-pool-to-dnp'], related: ['[Создаём входную точку для POST-запроса из 1С](/docs/onec/academy/create-inbound-endpoint)', '[Настраиваем полный обмен click-by-click](/docs/onec/academy/full-flow-click-by-click)', '[Test Console](/test-console)'] }),
  symptomPage({ slug: 'omh-401-403-from-1c', title: 'Symptom: 1C receives 401/403 from OMH', description: 'The inbound OMH endpoint rejects the request before the flow starts.', order: 90, whatYouSee: ['- 1C receives 401 or 403 from `/api/bus/in/{slug}`.', '- Event is not created, or Timeline stops at receive/auth.', '- Test Console works only when token header is present.'], meaning: 'This is inbound endpoint authorization. It protects OMH from unauthorized requests. It is separate from optional UI auth and separate from OData credentials.', quickFix: 'Pass the correct `X-OMH-Token` header for this endpoint, then test the same request in Test Console.', checklist: ['Endpoint auth mode is known: none/static token.', '`X-OMH-Token` header is present in 1C request.', 'Token value matches the endpoint config or secret.', 'Header is not stripped by proxy.', 'You did not use OData password as inbound token.', 'Optional UI auth package is not expected to protect integration API.'], where: ['Integration Bus endpoint auth settings.', 'Timeline -> receive step if event exists.', '`incoming.request.headers` with redaction.', 'Test Console headers field.', 'Audit log for endpoint auth changes.'], exampleLanguage: 'http', example: ['POST /api/bus/in/onec-pool-to-dnp', 'Content-Type: application/json', 'X-OMH-Token: training-token'], related: ['[Secrets и static token](/docs/onec/setup/auth-secrets-static-token)', '[Создаём входную точку для POST-запроса из 1С](/docs/onec/academy/create-inbound-endpoint)', '[1C returned 401 Unauthorized](/docs/onec/troubleshooting/onec-returned-401)'] }),
  symptomPage({ slug: 'route-did-not-match', title: 'Symptom: Endpoint exists but route did not match', description: 'The inbound endpoint exists, but no route/action selected the request.', order: 100, whatYouSee: ['- Endpoint accepts the request, but response says route not matched.', '- Timeline has receive/match_route failed.', '- Business action never starts.'], meaning: 'OMH found the endpoint but route conditions did not match the request body, headers, source, event type or package route.', quickFix: 'Open Timeline `route.match.json`, compare matcher conditions with the incoming request, then run the same payload in Test Console.', checklist: ['Endpoint slug is correct.', 'Input mode matches JSON/XML/raw.', 'Matcher field path exists.', 'Expected value equals actual value exactly.', 'Default route/fallback exists if needed.', 'Package route is enabled.', 'Flow was published after matcher changes.'], where: ['Timeline -> `route.match.json`.', 'Timeline -> `incoming.request.json` or raw XML.', 'Integration Bus routes list.', 'Flow Builder matcher/source block.', 'Test Console saved request.'], exampleLanguage: 'json', example: ['{', '  "matched": false,', '  "reason": "pool_type expected DNP, got PRINT"', '}'], related: ['[Рецепт 8. Маршрутизация по phrase/value](/docs/onec/recipes/recipe-08-route-by-key-phrase-value)', '[Visual Flow Builder](/docs/onec/tools/visual-flow-builder)', '[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts)'] }),
  symptomPage({ slug: 'invalid-json-body', title: 'Symptom: Request body is not valid JSON', description: 'OMH endpoint expects JSON, but the body cannot be parsed as JSON.', order: 110, whatYouSee: ['- 1C receives validation error for JSON body.', '- Timeline stops before read fields.', '- Test Console shows parse error.'], meaning: 'The endpoint input mode is JSON, but the request body is empty, malformed, encoded incorrectly, or sent with wrong Content-Type.', quickFix: 'Copy the body from `incoming.request` or 1C code into Test Console and fix JSON until it parses.', checklist: ['Content-Type is `application/json`.', 'Body is a JSON object, not a 1C string dump.', 'Quotes are double quotes.', 'No trailing commas.', 'Encoding is UTF-8.', '1C code writes JSON through JSON writer, not manual concatenation.', 'Endpoint input mode is JSON.'], where: ['Test Console JSON editor.', 'Timeline -> `incoming.request.raw` if event is created.', '1C code that builds request body.', 'Integration Bus endpoint input mode.', 'Saved Test Cases for a known-good payload.'], exampleLanguage: 'json', example: ['{', '  "inn": "7707083893",', '  "product_code": "ABC-123",', '  "pool_id": "POOL-001",', '  "codes": ["010464615169738421ABC"]', '}'], related: ['[Читаем значения из входящего запроса](/docs/onec/academy/read-request-fields)', '[Настраиваем полный обмен click-by-click](/docs/onec/academy/full-flow-click-by-click)', '[Test Console](/test-console)'] }),
  symptomPage({ slug: 'xml-parse-error', title: 'Symptom: XML parse failed', description: 'XML body cannot be parsed, fields are empty or encoding is broken.', order: 120, whatYouSee: ['- XML Tools reports invalid XML.', '- Flow parse step returns empty fields.', '- Cyrillic text looks corrupted.', '- Raw forwarding scenario accidentally tries to parse XML.'], meaning: 'The XML body, encoding, namespace, Content-Type or flow input mode does not match what the pipeline expects.', quickFix: 'Open the raw XML artifact in XML Tools and validate it before debugging OData or target steps.', checklist: ['Content-Type is `application/xml` or `text/xml`.', 'XML declaration encoding matches real body encoding.', 'Namespaces are handled in XPath/path picker.', 'Payload is raw XML, not escaped XML inside JSON.', 'Flow input mode is XML or raw_text as intended.', 'raw_forward is used when XML must not be changed.'], where: ['Timeline -> `incoming.request.xml`.', 'XML Tools parse/hash/diff.', '`xml.parse.result.json` artifact.', 'Endpoint input mode settings.', 'Target XML artifact for forwarding scenarios.'], exampleLanguage: 'xml', example: ['<?xml version="1.0" encoding="UTF-8"?>', '<Envelope>', '  <Customer><INN>7707083893</INN></Customer>', '</Envelope>'], related: ['[Recipe 3 XML raw forwarding](/docs/onec/recipes/recipe-03-onec-xml-raw-forwarding)', '[Recipe 4 XML with INN lookup](/docs/onec/recipes/recipe-04-onec-xml-inn-lookup)', '[XML Tools](/docs/onec/tools/xml-tools)'] }),
  symptomPage({ slug: 'odata-step-failed', title: 'Symptom: OData step failed', description: 'Any OData Query step failed in Flow Builder or Timeline.', order: 130, whatYouSee: ['- Timeline step `get_contractor` or `get_product` is failed.', '- The flow stops before JSON Builder.', '- Error may be 401, resource not found, timeout or empty required lookup.'], meaning: 'The OData step combines connection, resource, filter, selected fields and required behavior. You need to identify which part failed, not rewrite the whole flow.', quickFix: 'Open `odata_query_request` and `odata_query_response`; then reproduce the same query in OData Master.', checklist: ['Connection healthcheck passes.', 'Resource exists in metadata.', 'Filter uses exact field name.', 'Value source exists and has expected value.', '`$select` includes fields used later.', '`Top` is safe.', 'Required behavior is intentional.'], where: ['Timeline -> failed OData step.', 'Artifacts `odata_query_request`, `odata_query_response`, `odata_query_result`.', 'OData Master.', 'Flow Builder OData Query block.', 'Variables preview before this step.'], exampleLanguage: 'text', example: ['Step: get_product', "Request: Catalog_Номенклатура?$filter=Артикул eq 'ABC-123'&$top=1", 'Result: failed required lookup'], related: ['[Как выбрать OData-подключение](/docs/onec/odata-course/select-connection-in-flow)', '[Как строить $filter](/docs/onec/odata-course/filter-basics)', '[OData query returns empty result](/docs/onec/troubleshooting/odata-empty-result)'] }),
  symptomPage({ slug: 'json-builder-variable-missing', title: 'Symptom: JSON Builder variable missing', description: 'JSON Builder cannot read contractor/product/request fields.', order: 140, whatYouSee: ['- Preview says variable missing.', '- Target JSON contains null or missing `contractor_uuid` / `product_uuid`.', '- Flow fails at `build_target_payload`.'], meaning: 'JSON Builder references a variable that was not created, was named differently, or does not contain the requested field.', quickFix: 'Open preview variables before JSON Builder and fix the source path, for example `contractor.Ref_Key` instead of `contractor.uuid`.', checklist: ['Previous step saved result as the same name used in Builder.', 'OData `$select` includes `Ref_Key` and `Description`.', 'Request path is `request.body.pool_id`, not `request.pool_id`.', 'Array fields such as `codes` stay arrays.', 'Required OData steps do not silently continue with null.', 'Builder preview is checked before publish.'], where: ['Flow Builder -> JSON Builder preview.', 'Timeline -> `target_payload.json`.', 'Timeline -> previous OData response artifact.', 'Builder variables panel.', 'Config History if mapping changed.'], exampleLanguage: 'json', example: ['{', '  "field": "contractor_uuid",', '  "source": "contractor.uuid",', '  "error": "Variable path not found. Use contractor.Ref_Key"', '}'], related: ['[Собираем целевой JSON](/docs/onec/academy/build-target-json)', '[Как использовать результат OData дальше](/docs/onec/odata-course/use-result-json-builder)', '[Настраиваем полный обмен click-by-click](/docs/onec/academy/full-flow-click-by-click)'] }),
  symptomPage({ slug: 'business-rule-stopped-flow', title: 'Symptom: Business Rule stopped flow', description: 'Rule evaluation stopped or skipped the integration before target call.', order: 150, whatYouSee: ['- Timeline step `business_rule` or `evaluate_rules` stopped the event.', '- Target connector was not called.', '- Response contains business validation message.'], meaning: 'A configured rule intentionally blocked the route, or the rule condition does not match the real request shape.', quickFix: 'Open the rule result artifact and compare actual input values with rule conditions.', checklist: ['Rule input field exists.', 'Expected value matches actual value exactly.', 'Rule order is correct.', 'Fallback rule exists for unknown values.', 'Rule action is fail/skip/route as intended.', 'Rule set was published after edits.'], where: ['Timeline -> `business_rule.result.json`.', 'Business Rules page -> Test rule set.', 'Transform output before rule.', 'Flow Builder preview.', 'Audit log for rule changes.'], exampleLanguage: 'json', example: ['{', '  "matched": true,', '  "action": "fail",', '  "message": "Unsupported pool_type PRINT"', '}'], related: ['[Rule Sets](/business-rules)', '[Recipe 8 route by phrase/value](/docs/onec/recipes/recipe-08-route-by-key-phrase-value)', '[Урок 12 — Исправляем частые ошибки](/docs/onec/academy/lesson-12-fix-common-errors)'] }),
  symptomPage({ slug: 'target-connector-not-found', title: 'Symptom: Target connector not found', description: 'Flow references a connector that is missing, disabled or not installed in the environment.', order: 160, whatYouSee: ['- `send_to_dnp` fails before HTTP request is sent.', '- Error says connector not found or disabled.', '- `target.request.json` is absent.'], meaning: 'The flow configuration points to a connector name/id that is not available in the current environment or package boundary.', quickFix: 'Open Connectors and verify the exact connector used by the flow exists and is enabled in this environment.', checklist: ['Connector exists in current environment.', 'Connector package is installed/enabled.', 'Flow references correct connector id/name.', 'Promotion included connector dependency or environment variable.', 'Connector healthcheck passes.', 'Secrets referenced by connector exist.'], where: ['Connectors page.', 'Flow Builder -> Call Endpoint block.', 'Config History / Change Set dependencies.', 'Secrets Store.', 'Timeline -> failed call step.'], exampleLanguage: 'json', example: ['{', '  "step": "send_to_dnp",', '  "connector": "DNP Service",', '  "error": "Connector not found in environment production"', '}'], related: ['[Отправляем JSON во внешний API](/docs/onec/academy/send-to-external-api)', '[Connector docs](/docs/onec/tools/connector)', '[Environment profiles](/environments)'] }),
  symptomPage({ slug: 'target-api-returned-error', title: 'Symptom: External API returned error', description: 'Target API returned 4xx, 5xx, timeout or business failure.', order: 170, whatYouSee: ['- Flow reached `send_to_dnp` and then failed.', '- `target.response.json` contains 400/401/409/500.', '- 1C received proxy error or accepted event later failed.'], meaning: 'OMH successfully built and sent a target request, but the external system rejected it or failed. Read the original target response artifact before retrying.', quickFix: 'Compare `target.request.json` with the target API contract, then read `target.response.json` for the real business error.', checklist: ['URL, method and path are correct.', 'Headers and auth secret are correct.', 'Body matches target schema.', 'Idempotency key exists for retryable operations.', '4xx validation errors are not blindly retried.', '5xx/timeouts use retry only when safe.'], where: ['Timeline -> `target.request.json`.', 'Timeline -> `target.response.json`.', 'External error details.', 'Queue/DLQ attempt history.', 'Secrets Store for target auth.'], exampleLanguage: 'json', example: ['{', '  "status": 400,', '  "error": "VALIDATION_FAILED",', '  "message": "contractor_uuid is required"', '}'], related: ['[Отправляем JSON во внешний API](/docs/onec/academy/send-to-external-api)', '[Queue / DLQ](/docs/onec/reference/queue-dlq)', '[JSON Builder variable missing](/docs/onec/troubleshooting/json-builder-variable-missing)'] }),
  symptomPage({ slug: 'event-stuck-in-queue', title: 'Symptom: Event stuck in queue', description: 'Event stays queued or retry_waiting and does not complete.', order: 180, whatYouSee: ['- Runtime Queue shows event waiting for a long time.', '- Event status is `queued` or `retry_waiting`.', '- Timeline does not move to the next run.'], meaning: 'The event is waiting for worker capacity, retry delay, package availability, maintenance window or dependency health.', quickFix: 'Open Runtime Queue and check next attempt time, worker status and last error before forcing replay.', checklist: ['Worker is online.', 'Queue item is not scheduled for future retry.', 'Package route is enabled.', 'Maintenance window is not active.', 'Retry policy delay is understood.', 'No dependency health gate blocks execution.', 'DLQ status is checked.'], where: ['Runtime Queue page.', 'Transaction Monitor.', 'Health page worker heartbeat.', 'Timeline last run.', 'DLQ if attempts were exhausted.'], exampleLanguage: 'json', example: ['{', '  "status": "retry_waiting",', '  "attempt": 2,', '  "next_attempt_at": "2026-07-05T14:30:00Z"', '}'], related: ['[Queue / DLQ reference](/docs/onec/reference/queue-dlq)', '[Transaction Monitor](/runtime/monitor)', '[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts)'] }),
  symptomPage({ slug: 'event-moved-to-dlq', title: 'Symptom: Event moved to DLQ', description: 'Retry attempts are exhausted or the error is non-retryable.', order: 190, whatYouSee: ['- Event appears on Dead Letter Queue page.', '- Status is `dlq`.', '- Automatic retry stopped.'], meaning: 'OMH stopped automatic processing to avoid endless retries. The root cause still lives in the first failed Timeline step and its artifacts.', quickFix: 'Open the DLQ row, jump to Timeline, fix the first failed step, then use Replay from DLQ.', checklist: ['First failed step is identified.', 'Root cause is data/config/secret/target/network, not just final DLQ state.', 'Retrying will not duplicate target operation or printing.', 'Payload edit is needed or not needed.', 'Config version is fixed and published.', 'Audit log records manual replay.'], where: ['Dead Letter Queue page.', 'Timeline failed step artifacts.', 'Queue attempt history.', 'Config History.', 'Audit log for replay/edit retry.'], exampleLanguage: 'json', example: ['{', '  "event_id": "event-uuid",', '  "status": "dlq",', '  "failed_step": "send_to_dnp"', '}'], related: ['[Queue / DLQ reference](/docs/onec/reference/queue-dlq)', '[External API returned error](/docs/onec/troubleshooting/target-api-returned-error)', '[Урок 12 — Исправляем частые ошибки](/docs/onec/academy/lesson-12-fix-common-errors)'] }),
  symptomPage({ slug: 'retry-does-not-happen', title: 'Symptom: Retry does not happen', description: 'A failed event does not retry even though the user expects it.', order: 200, whatYouSee: ['- Event failed once and stayed failed.', '- Queue has no future attempt.', '- User clicks retry but nothing changes.'], meaning: 'The error may be non-retryable, retry policy may be disabled, attempts may be exhausted, or the event may already be in DLQ/manual state.', quickFix: 'Check retry policy and error classification before pressing manual replay.', checklist: ['Error type is retryable: timeout/5xx/network, not 400 validation.', 'Retry policy is enabled for this route/step.', 'Max attempts are not exhausted.', 'Next attempt time is not in the future.', 'Worker is online.', 'Event is not locked by maintenance/manual action.'], where: ['Runtime Queue item details.', 'Timeline -> external error classification.', 'Flow/route retry policy.', 'DLQ page.', 'Audit log for manual state changes.'], exampleLanguage: 'json', example: ['{', '  "retryable": false,', '  "reason": "HTTP 400 validation error is not retryable"', '}'], related: ['[Queue / DLQ reference](/docs/onec/reference/queue-dlq)', '[External API returned error](/docs/onec/troubleshooting/target-api-returned-error)', '[Event stuck in queue](/docs/onec/troubleshooting/event-stuck-in-queue)'] }),
  symptomPage({ slug: 'worker-not-processing', title: 'Symptom: Worker is not processing', description: 'Events stay queued because runtime worker is offline or unhealthy.', order: 210, whatYouSee: ['- Queue length grows.', '- Worker heartbeat is stale.', '- No new Timeline steps appear after receive.'], meaning: 'The runtime worker responsible for processing events is not running, cannot connect to database, or is blocked by infrastructure health.', quickFix: 'Open Health / Transaction Monitor and restart or fix the worker before replaying individual events.', checklist: ['Worker process/container is running.', 'Worker can reach database and artifact storage.', 'Worker heartbeat is current.', 'Package runtime dependencies are installed.', 'No global maintenance mode blocks processing.', 'Logs do not show migration/config errors.'], where: ['Health page -> worker heartbeat.', 'Transaction Monitor.', 'Runtime Queue length.', 'Backend/worker logs.', 'Maintenance page.'], exampleLanguage: 'text', example: ['Worker heartbeat: stale', 'Queue status: 42 queued events', 'Last processed: 35 minutes ago'], related: ['[Transaction Monitor](/runtime/monitor)', '[Health](/health)', '[Event stuck in queue](/docs/onec/troubleshooting/event-stuck-in-queue)'] }),
  symptomPage({ slug: 'printer-unavailable', title: 'Symptom: Printer unavailable', description: 'Printer connector cannot deliver a print job.', order: 220, whatYouSee: ['- Print job is failed or retry_waiting.', '- Timeline shows network error.', '- 1C sent print request but label did not print.'], meaning: 'OMH rendered or accepted the print job, but cannot reach the printer, port, network route or printer state.', quickFix: 'Test TCP connectivity from the OMH backend host to printer IP/port before retrying the print job.', checklist: ['Printer IP is current.', 'Port 9100 or configured raw port is open.', 'Firewall/VLAN allows OMH backend to reach printer.', 'Printer is online and not paused.', 'ZPL artifact exists.', 'Retry will not create unwanted duplicate print.'], where: ['Printing page -> printer status.', 'Printing page -> print job details.', 'Timeline -> `zpl.rendered.txt`.', 'Timeline -> printer request/response artifacts.', 'Queue/DLQ for print event.'], exampleLanguage: 'text', example: ['Connection refused 192.168.1.50:9100', 'Print job: retry_waiting'], related: ['[Recipe 5 print request to Zebra](/docs/onec/recipes/recipe-05-onec-print-request-to-zebra)', '[Printing](/printing)', '[Event moved to DLQ](/docs/onec/troubleshooting/event-moved-to-dlq)'] }),
  symptomPage({ slug: 'zpl-label-wrong', title: 'Symptom: ZPL sent but label wrong', description: 'Printer prints a label, but size, barcode, text or encoding is wrong.', order: 230, whatYouSee: ['- Printer prints something, but barcode cannot be scanned.', '- Text is shifted/cut off.', '- Cyrillic or GS1 content is wrong.'], meaning: 'Network delivery worked. The problem is ZPL template, data mapping, encoding, printer DPI/label size or barcode format.', quickFix: 'Open `zpl.rendered.txt`, compare it with expected printer template and test the same ZPL on a safe test printer.', checklist: ['Correct printer DPI and label size.', 'Template variables are filled from expected request fields.', 'Barcode format matches GS1/Code128/DataMatrix requirements.', 'Encoding/font supports required characters.', 'No extra spaces/newlines inside barcode data.', 'Rendered ZPL artifact matches what was sent.'], where: ['Timeline -> `zpl.rendered.txt`.', 'Printing job details.', 'Template/config version history.', 'Incoming request artifact.', 'Printer test page if available.'], exampleLanguage: 'text', example: ['^XA', '^FO50,50^BCN,100,Y,N,N', '^FD010464615169738421ABC^FS', '^XZ'], related: ['[Recipe 5 print request to Zebra](/docs/onec/recipes/recipe-05-onec-print-request-to-zebra)', '[Printing](/printing)', '[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts)'] }),
  symptomPage({ slug: 'print-job-not-printed', title: 'Symptom: Print job created but not printed', description: 'OMH created a print job, but the physical label never appeared.', order: 240, whatYouSee: ['- Printing page shows job created.', '- No physical label printed.', '- Timeline may show job accepted but no printer completion.'], meaning: 'The event reached print subsystem, but the job may be waiting, assigned to wrong printer, paused, duplicate-guarded, or blocked by printer/network state.', quickFix: 'Open the print job, verify assigned printer and status, then check whether the job is queued, failed, duplicate or delivered.', checklist: ['Correct printer selected by route/business rule.', 'Job status is not queued behind earlier failed jobs.', 'Duplicate guard did not suppress printing.', 'Printer connector is enabled.', 'Printer is online and has paper/ribbon.', 'No DLQ event exists for this print job.'], where: ['Printing page -> jobs list.', 'Timeline -> print job artifacts.', 'Business rule result if printer is selected dynamically.', 'Queue/DLQ for print event.', 'Printer hardware status.'], exampleLanguage: 'json', example: ['{', '  "print_job_id": "job-uuid",', '  "printer": "Zebra-01",', '  "status": "queued"', '}'], related: ['[Recipe 5 print request to Zebra](/docs/onec/recipes/recipe-05-onec-print-request-to-zebra)', '[Printer unavailable](/docs/onec/troubleshooting/printer-unavailable)', '[Business Rule stopped flow](/docs/onec/troubleshooting/business-rule-stopped-flow)'] }),
];

type ExerciseConfig = {
  slug: string;
  title: string;
  description: string;
  order: number;
  goal: string;
  open: string[];
  task: string[];
  pass: string[];
  testConsole?: boolean;
  related: string[];
};

function exercisePage(config: ExerciseConfig): PageSeed {
  return page('exercises', config.slug, config.title, config.description, config.order, mdLines(
    `# ${config.title}`,
    '',
    '## Цель',
    config.goal,
    '',
    '## Что открыть в OMH',
    ...config.open.map((item) => `- ${item}`),
    '',
    '## Задание',
    ...config.task.map((item, index) => `${index + 1}. ${item}`),
    '',
    '## Проверка результата',
    ...config.pass.map((item) => `- [ ] ${item}`),
    '',
    ...(config.testConsole ? [
      '## Open Exercise in Test Console',
      '::open-page{route="/test-console?exampleId=onec.golden_scenario" label="Open Exercise in Test Console"}',
      '',
      'Run sample request через Test Console, затем откройте Timeline по `event_id`.',
      '',
    ] : []),
    '## Если не получилось',
    '- Не переходите к следующему упражнению, пока не найден первый failed step.',
    '- Откройте Timeline и artifacts, а не только общий текст ошибки.',
    '- Сверьте результат с troubleshooting по симптомам.',
    '',
    '## Связанные уроки',
    ...config.related.map((item) => `- ${item}`),
  ));
}

const exercisesIndex = page('exercises', 'index', 'Практические упражнения и проверка навыков', '10 упражнений, которые показывают, готов ли пользователь самостоятельно настраивать базовую 1C интеграцию.', 1, mdLines(
  '# Практические упражнения и проверка навыков',
  '',
  'Этот раздел превращает документацию в проверяемое обучение. После каждого упражнения пользователь должен получить конкретный результат: созданную настройку, успешный preview, event id, Timeline или исправленную ошибку.',
  '',
  '## Что вы сможете проверить',
  '- Can I configure OData?',
  '- Can I build a flow?',
  '- Can I debug Timeline?',
  '- Can I fix common errors?',
  '',
  '## Маршрут упражнений',
  '1. [Create OData connection and find contractor](/docs/onec/exercises/create-odata-connection-find-contractor).',
  '2. [Create endpoint and send test POST](/docs/onec/exercises/create-endpoint-send-test-post).',
  '3. [Add OData lookup by INN](/docs/onec/exercises/add-odata-lookup-by-inn).',
  '4. [Add second OData lookup by product_code](/docs/onec/exercises/add-second-odata-lookup-by-product-code).',
  '5. [Build target JSON](/docs/onec/exercises/build-target-json).',
  '6. [Run flow with Dry Run](/docs/onec/exercises/run-flow-with-dry-run).',
  '7. [Run flow with real send](/docs/onec/exercises/run-flow-with-real-send).',
  '8. [Find original error in Timeline](/docs/onec/exercises/find-original-error-in-timeline).',
  '9. [Move DLQ item back to retry](/docs/onec/exercises/move-dlq-item-back-to-retry).',
  '10. [Fix missing contractor error](/docs/onec/exercises/fix-missing-contractor-error).',
  '',
  '## Как сдавать самому себе',
  '- Не отмечайте exercise complete, пока не можете показать экран или artifact.',
  '- Для OData упражнений сохраняйте exact resource, filter и response.',
  '- Для flow упражнений сохраняйте `event_id`, `timeline_url` и список artifacts.',
  '- Для error упражнений называйте first failed step и root cause.',
  '',
  '## После упражнений',
  'Перейдите к [Readiness checklist](/docs/onec/readiness-checklist) и мини-сертификации.',
));

export const exercisePages: PageSeed[] = [
  exercisesIndex,
  exercisePage({
    slug: 'create-odata-connection-find-contractor',
    title: 'Упражнение 01 — Create OData connection and find contractor',
    description: 'Создать OData ERP connection и найти контрагента по ИНН.',
    order: 10,
    goal: 'Проверить, что пользователь может подключить 1C OData, увидеть metadata и найти `Ref_Key` контрагента без Flow Builder.',
    open: ['OData Connections', 'OData Master', 'Secrets Store если пароль хранится через secret reference'],
    task: ['Создайте connection `OData ERP`.', 'Запустите Test metadata.', 'Откройте OData Master.', 'Выберите resource `Catalog_Контрагенты`.', "Выполните filter `ИНН eq '7707083893'` и `$top=1`.", 'Найдите `Ref_Key` и `Description`.'],
    pass: ['OData metadata загружается без ошибки.', 'OData Master показывает `Catalog_Контрагенты`.', 'Query возвращает одну строку или понятный empty result.', 'Вы можете объяснить, что такое `Ref_Key`.'],
    related: ['[Создаём OData-подключение к 1С](/docs/onec/academy/create-odata-connection)', '[Ищем контрагента по ИНН](/docs/onec/academy/find-contractor-by-inn)', '[OData empty result](/docs/onec/troubleshooting/odata-empty-result)'],
  }),
  exercisePage({
    slug: 'create-endpoint-send-test-post',
    title: 'Упражнение 02 — Create endpoint and send test POST',
    description: 'Создать inbound endpoint и отправить Golden Scenario payload.',
    order: 20,
    goal: 'Проверить, что пользователь отличает endpoint URL от frontend URL и может отправить первый POST в OMH.',
    open: ['Integration Bus или Flow Builder', 'Test Console', 'Event Journal / Timeline'],
    task: ['Создайте endpoint slug `onec-pool-to-dnp`.', 'Скопируйте URL `/api/bus/in/onec-pool-to-dnp`.', 'Откройте Test Console.', 'Вставьте Golden Scenario payload.', 'Нажмите Send.', 'Откройте Timeline из ответа.'],
    pass: ['Test Console отправляет POST без `Not Found`.', 'Ответ содержит `event_id` или понятную controlled error.', 'В Event Journal появился новый event.', 'Вы можете показать `incoming.request.json`.'],
    testConsole: true,
    related: ['[Создаём входную точку для POST-запроса из 1С](/docs/onec/academy/create-inbound-endpoint)', '[1C receives 404 from OMH](/docs/onec/troubleshooting/omh-404-from-1c)', '[Test Console](/test-console)'],
  }),
  exercisePage({
    slug: 'add-odata-lookup-by-inn',
    title: 'Упражнение 03 — Add OData lookup by INN',
    description: 'Добавить первый OData Query step, который сохраняет contractor.',
    order: 30,
    goal: 'Проверить, что пользователь умеет использовать входное поле `request.body.inn` как значение фильтра OData.',
    open: ['Integration Flow Builder', 'OData Master', 'Timeline artifacts'],
    task: ['Откройте flow Golden Scenario.', 'Добавьте step `get_contractor`.', 'Connection: `OData ERP`.', 'Resource: `Catalog_Контрагенты`.', "Filter: `ИНН eq request.body.inn`.", '`$select`: `Ref_Key,Description,ИНН`.', 'Save result as: `contractor`.', 'Required: yes.'],
    pass: ['Preview строит правильный OData request.', '`contractor.Ref_Key` доступен следующему шагу.', 'Timeline содержит OData request/response artifact.', 'Пустой результат дает понятную ошибку, а не null в target JSON.'],
    related: ['[Первая выборка OData: контрагент по ИНН](/docs/onec/academy/first-odata-query-contractor)', '[Как строить $filter](/docs/onec/odata-course/filter-basics)', '[OData step failed](/docs/onec/troubleshooting/odata-step-failed)'],
  }),
  exercisePage({
    slug: 'add-second-odata-lookup-by-product-code',
    title: 'Упражнение 04 — Add second OData lookup by product_code',
    description: 'Добавить второй lookup товара и не перезаписать contractor.',
    order: 40,
    goal: 'Проверить, что пользователь понимает chaining: второй OData result сохраняется как `product`, а первый остается `contractor`.',
    open: ['Flow Builder', 'OData Master', 'Preview variables'],
    task: ['Добавьте step `get_product` после `get_contractor`.', 'Выберите connection, где хранится номенклатура: `OData ERP` или `OData WMS`.', 'Resource: `Catalog_Номенклатура`.', 'Filter field: `Артикул` или фактическое поле из metadata.', 'Value source: `request.body.product_code`.', 'Save result as: `product`.', 'Запустите Preview.'],
    pass: ['Preview показывает одновременно `contractor` и `product`.', '`product.Ref_Key` доступен JSON Builder.', 'Вы не перезаписали переменную `contractor`.', 'OData response artifact показывает выбранную connection.'],
    related: ['[Вторая выборка OData: товар по артикулу](/docs/onec/academy/second-odata-query-product)', '[Multiple OData connections](/docs/onec/odata-course/multiple-connections)', '[Product not found](/docs/onec/troubleshooting/product-not-found)'],
  }),
  exercisePage({
    slug: 'build-target-json',
    title: 'Упражнение 05 — Build target JSON',
    description: 'Собрать target payload только из нужных полей.',
    order: 50,
    goal: 'Проверить, что пользователь умеет выбирать нужные поля из request, contractor и product, а не отправлять весь сырой OData response.',
    open: ['Flow Builder JSON Builder', 'Preview variables', 'Timeline target_payload artifact'],
    task: ['Добавьте `build_target_payload`.', 'Создайте `pool_id <- request.body.pool_id`.', 'Создайте `contractor_uuid <- contractor.Ref_Key`.', 'Создайте `product_uuid <- product.Ref_Key`.', 'Создайте `codes <- request.body.codes`.', 'Добавьте constant `source_system = "1C"`.', 'Запустите Preview.'],
    pass: ['Preview показывает валидный JSON.', '`codes` остался массивом.', 'В target JSON нет лишних полей OData.', '`target_payload.json` открывается в Timeline.'],
    related: ['[Собираем целевой JSON](/docs/onec/academy/build-target-json)', '[Как использовать результат OData дальше](/docs/onec/odata-course/use-result-json-builder)', '[JSON Builder variable missing](/docs/onec/troubleshooting/json-builder-variable-missing)'],
  }),
  exercisePage({
    slug: 'run-flow-with-dry-run',
    title: 'Упражнение 06 — Run flow with Dry Run',
    description: 'Проверить flow без реальной отправки во внешний API.',
    order: 60,
    goal: 'Проверить, что пользователь умеет видеть будущие OData requests, target JSON и target request preview до реального Send.',
    open: ['Test Console', 'Flow Builder Preview', 'Timeline если Dry Run сохраняет run preview'],
    task: ['Откройте Test Console.', 'Выберите endpoint `onec-pool-to-dnp`.', 'Вставьте Golden Scenario payload.', 'Нажмите Dry Run.', 'Откройте OData request preview для contractor.', 'Откройте OData request preview для product.', 'Откройте JSON builder output и target request preview.'],
    pass: ['Dry Run не отправляет запрос во внешний API.', 'Оба OData filters читаемы.', 'Target request preview содержит `target_payload`.', 'Вы можете объяснить, что произойдет при Send.'],
    testConsole: true,
    related: ['[Настраиваем полный обмен click-by-click](/docs/onec/academy/full-flow-click-by-click)', '[Проверяем весь интеграционный поток](/docs/onec/academy/test-full-flow)', '[OData artifacts](/docs/onec/odata-course/odata-artifacts)'],
  }),
  exercisePage({
    slug: 'run-flow-with-real-send',
    title: 'Упражнение 07 — Run flow with real send',
    description: 'Выполнить настоящий запуск и открыть Timeline.',
    order: 70,
    goal: 'Проверить, что пользователь умеет отличить accepted event от полного результата выполнения.',
    open: ['Test Console', 'Event Journal', 'Timeline'],
    task: ['Убедитесь, что Dry Run корректный.', 'Нажмите Send.', 'Скопируйте `event_id`.', 'Откройте `timeline_url`.', 'Проверьте steps: receive, get_contractor, get_product, build_target_payload, send_to_dnp, handle_response.', 'Откройте artifacts каждого шага.'],
    pass: ['Send создает event id.', 'Timeline показывает все ожидаемые steps.', 'Target request и target response сохранены.', 'Вы можете объяснить итог без чтения backend logs.'],
    testConsole: true,
    related: ['[Проверяем весь интеграционный поток](/docs/onec/academy/test-full-flow)', '[Timeline reference](/docs/onec/reference/timeline)', '[External API returned error](/docs/onec/troubleshooting/target-api-returned-error)'],
  }),
  exercisePage({
    slug: 'find-original-error-in-timeline',
    title: 'Упражнение 08 — Find original error in Timeline',
    description: 'Найти первопричину ошибки по artifacts, а не по последнему статусу.',
    order: 80,
    goal: 'Проверить, что пользователь умеет открыть first failed step, request artifact и response artifact.',
    open: ['Event Timeline', 'Artifacts panel', 'Troubleshooting по симптомам'],
    task: ['Откройте failed event.', 'Найдите первый красный/failed step.', 'Откройте request artifact этого step.', 'Откройте response/error artifact этого step.', 'Сформулируйте root cause одной фразой.', 'Откройте соответствующий symptom playbook.'],
    pass: ['Назван first failed step.', 'Открыт original external response.', 'Root cause не подменен общим `failed`.', 'Понятно, retry безопасен или нет.'],
    related: ['[Урок 11 — Читаем Timeline и артефакты](/docs/onec/academy/lesson-11-read-timeline-and-artifacts)', '[Errors, Timeline and artifacts](/docs/onec/support/errors-timeline-artifacts)', '[Troubleshooting по симптомам](/docs/onec/troubleshooting)'],
  }),
  exercisePage({
    slug: 'move-dlq-item-back-to-retry',
    title: 'Упражнение 09 — Move DLQ item back to retry',
    description: 'Вернуть событие из DLQ после исправления причины.',
    order: 90,
    goal: 'Проверить, что пользователь не делает replay blindly, а сначала исправляет root cause и понимает риск дублей.',
    open: ['Dead Letter Queue', 'Timeline', 'Audit log'],
    task: ['Откройте DLQ item.', 'Перейдите в Timeline.', 'Найдите first failed step.', 'Исправьте конфигурацию, secret или payload.', 'Проверьте, что retry не создаст дубль target operation.', 'Нажмите Replay from DLQ или Edit & Retry.', 'Откройте новый run.'],
    pass: ['Причина DLQ названа до retry.', 'Новый run появился в Timeline.', 'Audit log содержит ручное действие.', 'Target operation не продублирована без контроля.'],
    related: ['[Queue, Retry и DLQ](/docs/onec/support/queue-retry-dlq)', '[Event moved to DLQ](/docs/onec/troubleshooting/event-moved-to-dlq)', '[Runtime DLQ](/runtime/dlq)'],
  }),
  exercisePage({
    slug: 'fix-missing-contractor-error',
    title: 'Упражнение 10 — Fix missing contractor error',
    description: 'Разобрать ODATA_LOOKUP_NOT_FOUND и исправить lookup.',
    order: 100,
    goal: 'Проверить, что пользователь умеет отличить успешное обращение к 1C от пустого результата фильтра.',
    open: ['Timeline', 'OData Master', 'Flow Builder OData step'],
    task: ['Откройте event с `ODATA_LOOKUP_NOT_FOUND`.', 'Откройте `odata_query_request`.', 'Скопируйте resource/filter в OData Master.', 'Проверьте filter без лишних пробелов.', 'Попробуйте `$top=5` без filter.', 'Исправьте connection, field или value source.', 'Запустите Dry Run повторно.'],
    pass: ['Понятно, что OMH reached 1C successfully.', 'Найдено, почему `value` пустой.', 'Исправленный filter возвращает contractor.', 'Flow больше не падает на contractor lookup.'],
    testConsole: true,
    related: ['[OData query returns empty result](/docs/onec/troubleshooting/odata-empty-result)', '[Contractor not found by INN](/docs/onec/troubleshooting/contractor-not-found-by-inn)', '[Пустой результат OData](/docs/onec/odata-course/empty-result-debugging)'],
  }),
];

export const readinessChecklistPages: PageSeed[] = [
  page('readiness-checklist', 'index', 'Readiness checklist для 1C интеграций', 'Самопроверка: готов ли пользователь настраивать базовые 1C интеграции в OMH.', 10, mdLines(
    '# Readiness checklist для 1C интеграций',
    '',
    'Отмечайте пункты только если можете показать экран, request, response или artifact. Это не формальность, а защита от ситуации “документацию прочитал, но настроить не могу”.',
    '',
    '## Checklist',
    '- [ ] I can create OData connection.',
    '- [ ] I can run OData query.',
    '- [ ] I can create endpoint.',
    '- [ ] I can send test JSON.',
    '- [ ] I can add OData lookup.',
    '- [ ] I can build JSON.',
    '- [ ] I can open Timeline.',
    '- [ ] I can find request/response artifacts.',
    '- [ ] I can read external error.',
    '- [ ] I can retry failed event.',
    '',
    '## Практическая проверка',
    '::checklist{id="onec-readiness" items="I can create OData connection|I can run OData query|I can create endpoint|I can send test JSON|I can add OData lookup|I can build JSON|I can open Timeline|I can find request/response artifacts|I can read external error|I can retry failed event"}',
    '',
    '## Мини-сертификация',
    'You are ready to configure basic 1C integrations if:',
    '- you completed these exercises;',
    '- all test cases passed;',
    '- you can explain Timeline artifacts.',
    '',
    '## Что приложить к приемке',
    '- Screenshot или export OData Connection с redacted secrets.',
    '- Test Console request и response.',
    '- Event `event_id` и Timeline URL.',
    '- `odata_query_request`, `odata_query_response`, `target_payload.json`, `target.response.json`.',
    '- Короткое объяснение: что было входом, что OMH запросил в OData, что отправил наружу, где была ошибка.',
    '',
    '## Следующий шаг',
    '- [Открыть упражнения](/docs/onec/exercises).',
    '- [Открыть мини-сертификацию](/docs/onec/readiness-checklist/mini-certification).',
  )),
  page('readiness-checklist', 'mini-certification', 'Mini certification — готовность к базовым 1C интеграциям', 'Неформальная внутренняя проверка перед самостоятельной настройкой.', 20, mdLines(
    '# Mini certification — готовность к базовым 1C интеграциям',
    '',
    'Это не официальный сертификат. Это короткий внутренний gate: пользователь готов настраивать базовые интеграции, если может воспроизвести путь от OData до Timeline без подсказок.',
    '',
    '## Условие готовности',
    'You are ready to configure basic 1C integrations if:',
    '- you completed these exercises;',
    '- all test cases passed;',
    '- you can explain Timeline artifacts.',
    '',
    '## Устная проверка',
    '1. Explain the difference between Endpoint and OData Connection.',
    '2. Show where OMH stores the exact OData filter sent to 1C.',
    '3. Explain what `Ref_Key` usually represents.',
    '4. Show `target_payload.json` and explain every field.',
    '5. Show how you would fix `ODATA_LOOKUP_NOT_FOUND`.',
    '',
    '## Практический минимум',
    '- Run sample request в Test Console.',
    '- Open Exercise in Test Console for the Golden Scenario.',
    '- Open Timeline and name first failed step for a broken run.',
    '- Move one DLQ item back to retry only after explaining duplicate risk.',
    '',
    '::open-page{route="/test-console?exampleId=onec.golden_scenario" label="Run sample request"}',
  )),
];

export const recipePages: PageSeed[] = [
  page("recipes", "dnp-chz-code-pool-sync", "Рецепт. DnP запрашивает пул кодов Честного знака", "DnP -> OMH -> 1C OData order -> Продукция -> foreach code pool -> DnP endpoint.", 5, mdLines(
    "# Рецепт. DnP запрашивает пул кодов Честного знака",
    "",
    "## Схема",
    "```text",
    "DnP calls OMH",
    "  -> OMH finds production order by Number",
    "  -> OMH reads tabular part Продукция",
    "  -> OMH repeats OData query for each product row",
    "  -> OMH merges code rows into codes",
    "  -> OMH sends result to DnP endpoint",
    "  -> OMH returns response to caller",
    "```",
    "",
    "## Входящий JSON",
    "```json",
    "{",
    "  \"operation\": \"dnp_sinc_pull_codes\",",
    "  \"sinc\": \"dnp_sinc_pull_codes\",",
    "  \"order_id\": 10271,",
    "  \"order_name\": \"26-0666/6938\",",
    "  \"Number\": \"260666/6938\"",
    "}",
    "```",
    "",
    "## OData steps",
    "1. `Document_ЗаказНаПроизводство2_2`, filter `Number eq '{{request.body.Number}}'`, save as `order`.",
    "2. `Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция`, save as `products`.",
    "3. Foreach `products` as `product`, query `InformationRegister_ПулКодовМаркировкиСУЗ`, save merged result as `codes`.",
    "",
    "## Финальное действие",
    "`POST http://172.16.3.10/api/v2/integrations/omh/chz/codes/import` и вернуть вызывающему `{ \"ok\": true }`.",
    "",
    "После сохранения endpoint: `POST /api/bus/in/dnp_sinc_pull_codes`.",
    "",
    "::open-page{route=\"/odata-explorer\" label=\"Открыть Мастер OData\"}",
  )),
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
    "- [OData Master](/odata-explorer)",
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
  page("recipes", "xml-raw-forwarding", "XML raw forwarding без изменения тела", "Короткий рецепт: принять XML, сохранить hash и передать дальше как пришло.", 90, mdLines(
    "# XML raw forwarding без изменения тела",
    "",
    "## Когда использовать",
    "Используйте этот рецепт, если целевая 1C или внешний сервис требует ровно тот XML, который пришел во входящем запросе. OMH в этом сценарии не должен форматировать, pretty-print, менять encoding или переставлять namespace.",
    "",
    "## Настройка",
    "1. В Workbench или Cockpit выберите `Input mode = XML`.",
    "2. Выберите действие `Raw XML forward`.",
    "3. Укажите target connector и path 1C HTTP service, например `/hs/omh/receive`.",
    "4. Сделайте Preview и убедитесь, что hash не меняется.",
    "",
    "## Runtime block",
    "```json",
    "{",
    "  \"id\": \"raw_xml_forward\",",
    "  \"type\": \"raw_xml_forward\",",
    "  \"source\": \"request.xml\",",
    "  \"method\": \"POST\",",
    "  \"path\": \"/hs/omh/receive\"",
    "}",
    "```",
    "",
    "## Timeline artifacts",
    "- `raw_xml_forward_input.xml`: оригинальное тело.",
    "- `raw_xml_forward.json`: SHA256 input/forwarded и флаг `forwarded_unchanged`.",
    "- `incoming.request`: headers и content type.",
    "",
    "## Частые ошибки",
    "- Пользователь выбрал XML parse, хотя нужен raw: XML может быть валидирован, но бизнес-смысл в том, что тело нельзя менять.",
    "- Target ждет `text/xml`, а endpoint отправляет `application/json`.",
    "- 1C отправляет XML внутри JSON-строки: сначала нужно извлечь строку, это уже не raw XML body.",
    "",
    "::checklist{id=\"recipe-xml-raw-forwarding\" items=\"Выбран input mode XML|Выбран Raw XML forward|Проверен Content-Type|Проверен SHA256|Открыт Timeline artifact\"}"
  )),
  page("recipes", "xml-field-extraction", "Извлечение полей из XML для OData и ответа", "Короткий рецепт: выбрать XML path, сделать переменную и использовать ее в OData filter.", 100, mdLines(
    "# Извлечение полей из XML для OData и ответа",
    "",
    "## Когда использовать",
    "Входящий сервис присылает XML, но дальше интеграции нужны конкретные значения: номер заказа, ИНН, код склада, тип устройства. Не надо вручную писать XPath в JSON. Вставьте XML sample и выберите поля через Path Picker.",
    "",
    "## Пример XML",
    "```xml",
    "<Request>",
    "  <Number>260666/6938</Number>",
    "  <DeviceType>toodoo</DeviceType>",
    "</Request>",
    "```",
    "",
    "## Что нажать",
    "1. Откройте Request/Response Workbench.",
    "2. Выберите `Input mode = XML`.",
    "3. Вставьте XML sample.",
    "4. В XML Path Picker нажмите `Use this field` у `/Request/Number`.",
    "5. В OData step используйте filter `Number eq '{{number}}'`.",
    "6. В response template используйте `{{order.Ref_Key}}` или `{{number}}`.",
    "",
    "## Что создаст OMH",
    "```json",
    "{",
    "  \"type\": \"xml_extract\",",
    "  \"fields\": [",
    "    { \"name\": \"number\", \"path\": \"/Request/Number\", \"required\": true }",
    "  ]",
    "}",
    "```",
    "",
    "## Проверка",
    "В Preview переменные должны содержать `number = 260666/6938`. В Timeline ищите `xml_extracted_fields.json`; если переменная пустая, значит path не совпадает с реальным XML или namespace.",
    "",
    "::checklist{id=\"recipe-xml-field-extraction\" items=\"Вставил XML sample|Выбрал path|Проверил variable name|Использовал variable в OData|Проверил xml_extracted_fields artifact\"}"
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
    setup: ['Создайте OData ERP profile.', 'В OData Master проверьте Catalog_Номенклатура по Артикул.', 'Создайте второй lookup для остатка или цены, если они опубликованы отдельным регистром.', 'Добавьте transform: trim article, normalize barcode, convert price to number.', 'Добавьте business rule: не отправлять товар без barcode.', 'Отправьте target payload в marketplace REST connector.'],
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
    odata: ['Если lookup empty, сначала повторите filter в OData Master.', 'Если 401, проверьте OData profile credentials.', 'Если 404, проверьте resource name и публикацию OData в 1C.', 'Если timeout, уменьшите $select/$top или проверьте индекс/фильтр.'],
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
  requestExample({ slug: 'request-01-customer-lookup', order: 10, title: 'Запрос 1. Проверить контрагента по ИНН', description: 'Минимальный POST, который учит искать контрагента и читать lookup artifacts.', endpoint: 'POST /api/bus/in/onec-customer-lookup', headers: 'Content-Type: application/json\nX-OMH-Token: <token>\nX-OMH-Source: 1c', body: '{\n  "inn": "7707083893",\n  "source_document": "Order SO-1001"\n}', onecCode: basicOneCPost, odataFilter: 'Resource: Catalog_Контрагенты\n$filter: ИНН eq \'7707083893\'\n$select: Ref_Key,Description,ИНН', exampleId: 'onec.customer_lookup_by_inn', notes: ['Если lookup empty, откройте тот же фильтр в OData Master.', 'Если INN хранится без лидирующих нулей, нормализуйте значение transform step.', 'Для филиалов добавьте KPP.'] }),
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
  errorPlaybook({ slug: 'odata-404-resource', order: 20, title: 'Playbook 2. OData resource не найден', description: '404/invalid resource при запросе Catalog или Document.', symptom: 'OData step падает с 404 или ONEC_ODATA_ERROR, хотя connection metadata работает.', likelyCauses: ['Ресурс называется иначе в этой базе.', 'Объект не опубликован в OData 1C.', 'Использовано русское имя справочника вместо technical OData name.', 'Base URL указывает не на ту информационную базу.'], whereToLook: ['OData Master resources list.', 'Timeline -> odata_query_request.json url/resource.', '1C publication settings.', 'OData profile base_url.'], fix: ['Откройте OData Master и загрузите resources.', 'Выберите ресурс из списка, не набирайте по памяти.', 'Проверьте публикацию OData в 1C.', 'Обновите flow step resource и сохраните draft/publish.'], prevent: ['В docs flow фиксируйте exact resource name.', 'Добавляйте screenshots/resources examples для клиента.', 'Проверяйте resource после обновления 1C конфигурации.'] }),
  errorPlaybook({ slug: 'odata-empty-required', order: 30, title: 'Playbook 3. Required OData lookup пустой', description: 'Lookup не нашел строку и flow остановился.', symptom: 'Timeline показывает ODATA_RESULT_EMPTY или бизнес-ошибку “required lookup returned no rows”.', likelyCauses: ['Неверный field/operator/value source.', 'Входное значение не нормализовано: пробелы, регистр, лидирующие нули.', 'Данные еще не заведены в 1C.', 'Фильтр требует KPP/warehouse/date, а передан только INN/SKU.'], whereToLook: ['Timeline -> odata_query_request.json.', 'Timeline -> incoming.request.', 'OData Master с тем же filter.', 'Transform output до lookup.'], fix: ['Скопируйте filter из artifact в OData Master.', 'Проверьте фактическое значение из incoming.request.', 'Добавьте transform trim/remove_spaces/normalize.', 'Если данные отсутствуют, заведите их в 1C и сделайте replay.'], prevent: ['Проверяйте negative examples до production.', 'Документируйте required fields.', 'Для неоднозначных ключей используйте resolver вместо прямого lookup.'] }),
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
- Нужно быстро проверить ресурс: OData Master и OData lookup.

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
