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
