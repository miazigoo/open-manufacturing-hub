import type { PageSeed } from './content';

function md(value: string) {
  return value.trim();
}

function page(sectionId: string, slug: string, title: string, description: string, order: number, markdown: string): PageSeed {
  return { packageId: 'onec', sectionId, slug, title, description, order, markdown };
}

type LessonConfig = {
  slug: string;
  order: number;
  title: string;
  description: string;
  build: string;
  why: string;
  steps: string[];
  example: string;
  expected: string[];
  mistakes: string[];
  checklist: string[];
  next?: string;
};

function lesson(config: LessonConfig): PageSeed {
  return page('academy', config.slug, config.title, config.description, config.order, md(`
# ${config.title}

## Что вы соберете
${config.build}

## Почему это важно
${config.why}

## Перед стартом
- Установлен и включен пакет 1C Integration Package в Plugin Store.
- Есть доступ к веб-интерфейсу OMH.
- Если в уроке используется OData, в 1C опубликован OData сервис и известен URL вида http://server/base/odata/standard.odata.
- Если endpoint принимает запросы из 1C, заранее решите, будет ли нужен статический inbound token.

## Карта действий
${config.steps.map((item, index) => `${index + 1}. ${item}`).join('\n')}

## Пример, который можно повторить
${config.example}

## Как понять, что все получилось
${config.expected.map((item) => `- ${item}`).join('\n')}

## Частые ошибки
${config.mistakes.map((item) => `- ${item}`).join('\n')}

::checklist{id="${config.slug}" items="${config.checklist.join('|')}"}

${config.next ? `## Следующий урок\n${config.next}` : ''}
`));
}

export const academyPages: PageSeed[] = [
  lesson({
    slug: 'lesson-01-map-of-the-product',
    order: 10,
    title: 'Урок 1. Карта продукта: endpoint, flow, OData, timeline',
    description: 'Объясняет простыми словами, из каких частей состоит 1C интеграция в OMH.',
    build: 'Вы не настраиваете интеграцию полностью. Вы собираете mental model: где входной запрос из 1C, где no-code pipeline, где OData подключение, где ответ целевой системе и где смотреть ошибки.',
    why: 'Большинство ошибок внедрения возникает не из-за OData или JSON, а из-за путаницы терминов. Пользователь создает connector, потом ищет endpoint, потом не понимает, почему Flow Builder просит connection. Этот урок связывает все понятия в один путь.',
    steps: [
      'Откройте 1C Cockpit. Это стартовая рабочая поверхность для 1C.',
      'Откройте OData Connections. Здесь создаются понятные профили: OData ERP, OData УСП, OData WMS.',
      'Откройте Integration Flows. Здесь создается бизнес-маршрут: кто вызывает OMH, какие lookup нужны, что отправлять дальше.',
      'Откройте OData Explorer. Здесь проверяется реальный ресурс 1C и фильтр до того, как вы вставите его в pipeline.',
      'Откройте Timeline любого события. Здесь видно, какой шаг сработал, какой запрос ушел наружу и какой ответ вернулась внешняя система.'
    ],
    example: `~~~text
1C POST /api/flows/in/marking-pool
  -> OMH endpoint проверяет token
  -> Flow читает inn и product_code
  -> Flow делает OData lookup в OData ERP
  -> Flow собирает JSON для DNP API
  -> OMH отправляет POST во внешний endpoint
  -> Timeline сохраняет вход, lookup, target request и target response
~~~`,
    expected: [
      'Вы понимаете, что OData Connection отвечает только за подключение к базе 1C.',
      'Вы понимаете, что Integration Flow отвечает за бизнес-логику маршрута.',
      'Вы знаете, что OData Explorer нужен для проверки ресурса и фильтра до настройки pipeline.',
      'Вы знаете, что Timeline является главным местом диагностики.'
    ],
    mistakes: [
      'Создавать отдельный raw connector для каждого flow, хотя достаточно одного named OData connection на базу 1C.',
      'Настраивать фильтр в pipeline без проверки в OData Explorer.',
      'Искать ошибку только в браузере, не открывая Timeline и artifacts.',
      'Смешивать inbound token из 1C и логин/пароль OData. Это разные уровни доступа.'
    ],
    checklist: ['Открыл 1C Cockpit', 'Понял разницу OData Connection и Integration Flow', 'Нашел OData Explorer', 'Понял где смотреть Timeline'],
    next: 'Перейдите к уроку 2 и создайте первый named OData profile.'
  }),
  lesson({
    slug: 'lesson-02-create-odata-connection',
    order: 20,
    title: 'Урок 2. Создаем OData Connection: ERP, УСП или WMS',
    description: 'Пошаговое создание понятного OData профиля вместо сырого JSON-коннектора.',
    build: 'Вы создадите профиль OData ERP или OData УСП с URL, пользователем, паролем или ссылкой на secret. Этот профиль потом будет выбираться в Explorer и Visual Flow Builder.',
    why: 'Новичку трудно понять, какой connector выбрать в flow. Named profile решает это: вместо технической записи пользователь видит OData ERP, OData УСП, OData WMS и понимает, в какую базу идет запрос.',
    steps: [
      'Откройте Data Tools -> OData Connections.',
      'Нажмите пресет OData ERP, OData УСП или OData WMS.',
      'Укажите URL OData. Обычно это http://server/base/odata/standard.odata.',
      'Выберите auth basic, если 1C требует логин и пароль.',
      'Укажите пользователя. Например Администратор для тестовой УСП или exchange_user для ERP.',
      'Укажите пароль напрямую для локальной проверки или $secret:onec.erp.password для production.',
      'Нажмите Create connection.',
      'Откройте созданный профиль и нажмите Test $metadata.'
    ],
    example: `~~~json
{
  "name": "OData УСП",
  "base_url": "http://usp-server/Trade/odata/standard.odata",
  "auth_type": "basic",
  "username": "Администратор",
  "password": "123",
  "default_top": 100,
  "max_pages": 10,
  "tags": ["УСП", "marking"]
}
~~~

Production-вариант отличается только хранением пароля:

~~~json
{
  "name": "OData ERP production",
  "password_secret": "onec.erp.production.password"
}
~~~`,
    expected: [
      'Профиль появляется в списке Saved OData connections.',
      'Test $metadata возвращает HTTP 200 или понятную внешнюю ошибку.',
      'Этот же профиль доступен в OData Explorer.',
      'В Visual Flow Builder OData step предлагает этот профиль в списке OData connection.'
    ],
    mistakes: [
      'Указывать URL базы без /odata/standard.odata.',
      'Использовать пароль 1C пользователя, которому не опубликованы нужные OData объекты.',
      'Путать пароль OData и X-OMH-Token для входного endpoint.',
      'Оставлять тестовый пароль 123 в production вместо Secrets Store.'
    ],
    checklist: ['Создал OData profile', 'Проверил URL', 'Проверил $metadata', 'Понял где хранить пароль', 'Открыл профиль в Explorer'],
    next: 'Урок 3 покажет, как проверить ресурс, фильтр и выборку в OData Explorer.'
  }),
  lesson({
    slug: 'lesson-03-odata-explorer-first-query',
    order: 30,
    title: 'Урок 3. Первый запрос в OData Explorer',
    description: 'Как безопасно проверить ресурс, фильтр, select и top перед pipeline.',
    build: 'Вы выберете OData profile, загрузите список ресурсов, выполните запрос к Catalog_Контрагенты и сохраните lookup template.',
    why: 'Pipeline не должен быть местом угадывания. Сначала проверяем OData отдельно: существует ли ресурс, правильно ли называется поле, возвращает ли фильтр одну запись, какие поля надо забрать.',
    steps: [
      'Откройте OData Explorer.',
      'Выберите OData connection: например OData ERP.',
      'Если список resources загрузился, найдите нужный Catalog или Document.',
      'Введите resource, например Catalog_Контрагенты.',
      'Введите $filter: ИНН eq 1234567890 или ИНН eq строка в кавычках, если ваша 1C требует строку.',
      'Введите $select: Ref_Key,Description,ИНН.',
      'Поставьте $top 10 для проверки.',
      'Нажмите Run query.',
      'Если результат правильный, сохраните lookup template: Find contractor by INN.'
    ],
    example: `~~~text
Connection: OData ERP
Resource: Catalog_Контрагенты
$filter: ИНН eq '1234567890'
$select: Ref_Key,Description,ИНН
$top: 10
~~~

Lookup template:

~~~json
{
  "name": "Find contractor by INN",
  "filter_template": "ИНН eq '{inn}'",
  "extract_json": {
    "contractor_uuid": "Ref_Key",
    "contractor_name": "Description"
  }
}
~~~`,
    expected: [
      'Explorer показывает request payload и response payload.',
      'В sample items есть Ref_Key и Description.',
      'Lookup template создан без ошибки JSON.',
      'Вы понимаете, какой resource и filter переносить в flow.'
    ],
    mistakes: [
      'Писать русское имя справочника вместо технического OData имени.',
      'Забывать кавычки вокруг строковых значений в $filter.',
      'Делать $top 1000 при проверке и ждать долгий ответ.',
      'Сохранять extract_json как массив, хотя нужен объект field -> ODataField.'
    ],
    checklist: ['Выбрал OData profile', 'Выполнил Run query', 'Увидел sample items', 'Сохранил lookup template'],
    next: 'В уроке 4 этот проверенный запрос станет OData step внутри Visual Flow Builder.'
  }),
  lesson({
    slug: 'lesson-04-build-1c-post-to-odata-flow',
    order: 40,
    title: 'Урок 4. Flow: 1C POST -> OData lookup -> JSON -> endpoint',
    description: 'Главный сценарий: 1C присылает запрос, OMH обогащает его через OData и отправляет наружу.',
    build: 'Вы соберете no-code pipeline: входной JSON от 1C, чтение INN, OData lookup контрагента, сборка target JSON и отправка во внешний REST endpoint.',
    why: 'Это самый частый промышленный сценарий. 1C знает часть данных, OMH должен найти недостающие данные в OData, нормализовать их и отдать внешней системе предсказуемый JSON.',
    steps: [
      'Откройте Integration Flows и создайте flow с source 1C и target REST/API.',
      'В input выберите JSON и endpoint slug, например marking-pool.',
      'Добавьте Read field: path request.body.inn, save_as inn.',
      'Добавьте OData step и выберите OData connection OData ERP.',
      'Укажите resource Catalog_Контрагенты.',
      'Укажите filter field ИНН, operator eq, value request.body.inn.',
      'Укажите $select Ref_Key,Description,ИНН и $top 1.',
      'Укажите save_as contractor и Required result enabled.',
      'Добавьте Build JSON: customer_uuid из contractor.Ref_Key, pool_id из request.body.pool_id.',
      'Добавьте Call endpoint: REST connector, POST, path /api/marking/pools, body target_payload.',
      'Нажмите Preview, затем Save Draft, затем Compile workflow.'
    ],
    example: `~~~json
{
  "inn": "1234567890",
  "product_code": "ABC-123",
  "pool_id": "POOL-001",
  "codes": ["010460123456789021ABC"]
}
~~~

Target JSON после OData lookup:

~~~json
{
  "pool_id": "POOL-001",
  "customer_uuid": "Ref_Key из Catalog_Контрагенты",
  "product_code": "ABC-123",
  "codes": ["010460123456789021ABC"]
}
~~~`,
    expected: [
      'Preview проходит без ошибки Invalid preview input.',
      'OData step показывает выбранный named profile.',
      'Compiled workflow появляется у flow.',
      'Тестовый POST создает событие и Timeline показывает lookup и target request.'
    ],
    mistakes: [
      'В value source писать просто inn, когда в sample request поле лежит в request.body.inn.',
      'Не включить Required result и отправить наружу payload без найденного контрагента.',
      'Путать save_as contractor и имя поля contractor_uuid в финальном JSON.',
      'Собирать JSON руками в 1C, хотя проще передать исходные поля и собрать target в OMH.'
    ],
    checklist: ['Создал flow', 'Добавил OData step', 'Выбрал OData connection', 'Собрал target JSON', 'Запустил Preview', 'Compiled workflow создан'],
    next: 'Урок 5 объясняет endpoint auth: как 1C должна безопасно вызывать OMH.'
  }),
  lesson({
    slug: 'lesson-05-inbound-token-and-1c-request',
    order: 50,
    title: 'Урок 5. Входной endpoint и ключ от 1C',
    description: 'Разница между X-OMH-Token для входа в OMH и логином OData для чтения 1C.',
    build: 'Вы настроите понятный контракт вызова из 1C: URL, method, headers, body, token и expected response.',
    why: 'Пользователи часто думают, что логин OData защищает входной endpoint. Нет: OData credentials используются OMH для запроса в 1C, а inbound token проверяет, имеет ли 1C право вызвать endpoint OMH.',
    steps: [
      'Откройте flow и найдите endpoint URL.',
      'Решите, нужен ли token. Для production почти всегда нужен.',
      'В документации flow сохраните header X-OMH-Token.',
      'В 1C HTTPЗапрос добавьте Content-Type application/json.',
      'Добавьте X-OMH-Token со значением, выданным для endpoint.',
      'Передайте JSON body в UTF-8.',
      'Проверьте код ответа. 2xx означает accepted или success, 4xx означает ошибка контракта, 5xx означает инфраструктурная или внешняя ошибка.'
    ],
    example: `~~~1c
HTTP = Новый HTTPСоединение("omh.example.local", 443,,,, Новый ЗащищенноеСоединениеOpenSSL);
Запрос = Новый HTTPЗапрос("/api/flows/in/marking-pool");
Запрос.Заголовки.Вставить("Content-Type", "application/json");
Запрос.Заголовки.Вставить("X-OMH-Token", "token-from-omh");
Запрос.УстановитьТелоИзСтроки(ТелоЗапроса, КодировкаТекста.UTF8);
Ответ = HTTP.ОтправитьДляОбработки(Запрос);
~~~`,
    expected: [
      'Без token endpoint возвращает понятную auth ошибку.',
      'С token endpoint создает event или возвращает sync response.',
      'Timeline содержит incoming.request с исходным JSON.',
      'OData credentials нигде не передаются из 1C в OMH endpoint.'
    ],
    mistakes: [
      'Отправлять логин и пароль OData в body входного запроса.',
      'Не проверять HTTP status в 1C и считать, что запрос прошел.',
      'Использовать Content-Type text/plain для JSON.',
      'Вшивать production token в общий модуль без контроля доступа.'
    ],
    checklist: ['Понял разницу token и OData credentials', 'Скопировал endpoint URL', 'Добавил headers в 1C', 'Проверил 2xx/4xx поведение'],
    next: 'Урок 6 показывает, как выбирать response mode.'
  }),
  lesson({
    slug: 'lesson-06-response-modes',
    order: 60,
    title: 'Урок 6. Какой ответ возвращать в 1C',
    description: 'Proxy response, accepted event и sync response простыми словами.',
    build: 'Вы выберете режим ответа flow: ждать внешнюю систему, вернуть только event id или собрать собственный sync JSON.',
    why: 'Неправильный response mode ломает UX в 1C. Если 1C ждет результат сразу, нельзя молча вернуть accepted. Если внешний API нестабилен, нельзя держать пользователя в форме 1C 60 секунд.',
    steps: [
      'Если 1C должна получить ответ внешнего API прямо сейчас, выберите proxy_response.',
      'Если 1C только передает событие в очередь, выберите accepted_event.',
      'Если OMH должен вернуть собственный компактный ответ, выберите sync_response.',
      'Для долгих операций включайте очередь и возвращайте accepted_event.',
      'Проверьте response в Test Console и в 1C обработчике HTTP status.'
    ],
    example: `~~~json
{
  "response_mode": "accepted_event",
  "response": {
    "status": "accepted",
    "event_id": "uuid",
    "message": "Request accepted for processing"
  }
}
~~~`,
    expected: [
      '1C получает предсказуемый формат ответа.',
      'Пользователь 1C не ждет долгую операцию без необходимости.',
      'Ошибки внешней системы остаются в Timeline и DLQ.',
      'Для sync сценария response содержит бизнес-результат.'
    ],
    mistakes: [
      'Использовать proxy_response при нестабильном target API.',
      'Возвращать accepted_event, когда 1C должна показать номер созданного документа.',
      'Не документировать response contract для разработчика 1C.',
      'Считать 202 ошибкой, хотя для accepted_event это нормальный ответ.'
    ],
    checklist: ['Выбрал response mode', 'Проверил ответ в Test Console', 'Зафиксировал contract для 1C', 'Понимаю когда нужна очередь'],
    next: 'Урок 7 посвящен ошибкам, retry и DLQ.'
  }),
  lesson({
    slug: 'lesson-07-errors-retry-dlq',
    order: 70,
    title: 'Урок 7. Ошибки, Retry и DLQ без паники',
    description: 'Как читать Timeline и отличать исправимые ошибки от ошибок настройки.',
    build: 'Вы научитесь открывать событие, читать original external error, находить failed step, решать Retry now или исправлять config.',
    why: 'Ценность OMH в том, что ошибка не превращается в фразу “не работает”. Система хранит исходный request, outgoing request, response и ошибку внешней системы без маскировки.',
    steps: [
      'Откройте Event Journal или Transaction Monitor.',
      'Найдите failed или attention event.',
      'Откройте Timeline.',
      'Прочитайте failed step: endpoint auth, OData lookup, transform, target request или response mapping.',
      'Откройте artifacts incoming.request, target.request, target.response.',
      'Если ошибка временная, нажмите Retry now.',
      'Если ошибка в данных, исправьте payload или source data и используйте replay.',
      'Если ошибка в конфигурации, выпустите новую версию flow и повторите событие.'
    ],
    example: `~~~text
404 OData resource -> проверить resource в OData Explorer
401 OData auth -> проверить пользователя/пароль профиля
Required lookup empty -> проверить filter и source field
Target 500 -> смотреть target.response и решать retry
Mapping error -> проверить template и sample request
~~~`,
    expected: [
      'Вы можете назвать конкретный failed step.',
      'Вы видите оригинальную ошибку внешней системы.',
      'Вы понимаете, retry поможет или сначала нужна правка данных/config.',
      'DLQ используется как рабочая очередь расследования, а не мусорная корзина.'
    ],
    mistakes: [
      'Нажимать retry на 401 auth ошибку без изменения credentials.',
      'Исправлять OData filter в flow, не проверив его в Explorer.',
      'Смотреть только общий status event, игнорируя artifacts.',
      'Удалять DLQ событие до сохранения причины.'
    ],
    checklist: ['Открыл Timeline', 'Нашел failed step', 'Посмотрел artifacts', 'Принял решение retry/fix/replay'],
    next: 'Урок 8 показывает, как использовать Secrets Store для паролей OData.'
  }),
  lesson({
    slug: 'lesson-08-secrets-for-odata',
    order: 80,
    title: 'Урок 8. Пароли OData через Secrets Store',
    description: 'Как не хранить production пароли в открытом config.',
    build: 'Вы создадите secret для пароля 1C и подключите его к OData Connection через $secret:name.',
    why: 'Тестовый пароль можно быстро ввести руками, но production конфигурация должна быть переносимой и безопасной. Config version хранит ссылку на secret, а не сам пароль.',
    steps: [
      'Установите и включите Secrets Store package, если он еще не включен.',
      'Откройте Secrets.',
      'Создайте secret onec.erp.production.password.',
      'Откройте OData Connections.',
      'В поле Password or secret введите $secret:onec.erp.production.password.',
      'Сохраните профиль и выполните Test $metadata.',
      'Проверьте, что config_json показывает masked или ссылку, но не пароль.'
    ],
    example: `~~~text
Secret name: onec.erp.production.password
OData profile password field: $secret:onec.erp.production.password
~~~`,
    expected: [
      'Пароль не виден в JSON config.',
      'Test $metadata работает после подстановки secret.',
      'Экспорт config можно переносить между окружениями без раскрытия пароля.',
      'В dev/stage/prod можно держать разные значения одного secret name.'
    ],
    mistakes: [
      'Писать $secret: с пробелом после двоеточия.',
      'Создать secret в одном окружении и забыть создать его в production.',
      'Давать secret слишком общее имя password.',
      'Оставлять старый raw password в description или tags.'
    ],
    checklist: ['Создал secret', 'Указал $secret в OData profile', 'Проверил metadata', 'Убедился что пароль скрыт'],
    next: 'Урок 9 объясняет promotion pipeline и безопасные изменения config.'
  }),
  lesson({
    slug: 'lesson-09-config-versioning',
    order: 90,
    title: 'Урок 9. Draft, Publish, Rollback для интеграций 1C',
    description: 'Как менять flow без случайного полома production.',
    build: 'Вы сохраните draft из Visual Flow Builder, опубликуете версию и поймете, когда использовать rollback.',
    why: 'Интеграция 1C обычно критична для операций. Нельзя редактировать production flow как черновик без истории. OMH хранит версии config, комментарий изменения и возможность отката.',
    steps: [
      'Откройте Visual Flow Builder нужного flow.',
      'Измените OData step или JSON template.',
      'Нажмите Preview на sample request.',
      'Нажмите Save Draft.',
      'Откройте Release control.',
      'Проверьте diff draft vs published.',
      'Опубликуйте draft с понятным комментарием.',
      'Если после публикации появились ошибки, используйте rollback на предыдущую версию.'
    ],
    example: `~~~text
Good publish comment:
Add OData ERP lookup by INN and include contractor_uuid in DNP payload.

Bad publish comment:
fix
~~~`,
    expected: [
      'Изменение имеет номер версии.',
      'В audit log видно кто и что поменял.',
      'Rollback возвращает предыдущий config.',
      'Preview прогоняется до публикации.'
    ],
    mistakes: [
      'Публиковать без sample request.',
      'Не писать смысловой комментарий.',
      'Откатывать config, не проверив, нет ли новых данных, зависящих от новой версии.',
      'Менять endpoint contract без уведомления разработчика 1C.'
    ],
    checklist: ['Сохранил draft', 'Проверил diff', 'Опубликовал с комментарием', 'Знаю где rollback'],
    next: 'Урок 10 собирает production checklist перед сдачей интеграции.'
  }),
  lesson({
    slug: 'lesson-10-production-checklist',
    order: 100,
    title: 'Урок 10. Production checklist перед сдачей 1C интеграции',
    description: 'Финальная проверка: доступы, тесты, retry, документация и диагностика.',
    build: 'Вы пройдете контрольный список перед включением интеграции в рабочем режиме.',
    why: 'Интеграция считается готовой не когда “один раз сработало”, а когда понятны доступы, ошибки, повторная обработка, владельцы данных и инструкция для поддержки.',
    steps: [
      'Проверьте package enabled и route inventory.',
      'Проверьте OData profiles: metadata, credentials, secrets, timeout.',
      'Проверьте endpoint auth и 1C HTTP code.',
      'Проверьте sample requests для success и error случаев.',
      'Проверьте Timeline: incoming, lookup, transform, target request, target response.',
      'Проверьте retry policy и DLQ path.',
      'Проверьте audit log и config version comment.',
      'Сохраните ссылку на recipe/lesson в описании flow.',
      'Попросите человека, который не настраивал flow, пройти по документации и повторить тест.'
    ],
    example: `~~~text
Minimum production acceptance:
- OData $metadata OK
- Test Console success case OK
- Test Console missing required object OK with readable error
- 1C sends real request and handles non-2xx
- Timeline contains enough artifacts for support
- Rollback path known
~~~`,
    expected: [
      'Интеграция воспроизводимо проходит happy path.',
      'Ошибки объяснимы по Timeline без доступа к коду.',
      'Production пароли не лежат в открытом config.',
      'Команда поддержки знает, где смотреть event, retry и DLQ.'
    ],
    mistakes: [
      'Считать готовым сценарий, проверенный только через браузерную форму.',
      'Не проверять отрицательный кейс: отсутствующий контрагент, неверный token, недоступная OData.',
      'Не документировать endpoint URL и headers для 1C.',
      'Не согласовать, кто имеет право менять OData profile.'
    ],
    checklist: ['Проверил happy path', 'Проверил error path', 'Проверил secrets', 'Проверил retry/DLQ', 'Документация приложена к flow']
  }),
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
