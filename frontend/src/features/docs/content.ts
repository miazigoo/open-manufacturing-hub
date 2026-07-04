import type { Language } from '../../i18n/dictionary';
import type { DocsLanguageBundle, DocsPackageId, DocsPageRecord, DocsPackageRecord } from './types';

const updatedAt = '2026-07-04';

type PageSeed = Omit<DocsPageRecord, 'id' | 'updatedAt' | 'translationStatus'>;

type PackageSeed = {
  id: DocsPackageId;
  title: string;
  description: string;
  order: number;
  accent: string;
  sections: Array<{ id: string; title: string; description: string; order: number; pages: PageSeed[] }>;
};

const ruSeeds: PackageSeed[] = [
  {
    id: 'core', title: 'Быстрый старт', description: 'Что такое OMH и как думать о событиях, очереди, timeline и пакетах.', order: 10, accent: 'amber',
    sections: [
      { id: 'start', title: 'Основа продукта', description: 'Ключевые понятия OMH.', order: 10, pages: [
        { packageId: 'core', sectionId: 'start', slug: 'overview', title: 'Что такое OMH', description: 'Интеграционный runtime, который делает события наблюдаемыми и повторяемыми.', order: 10, markdown: `# Что такое Open Manufacturing Hub

OMH — это не просто набор коннекторов. Это операционная поверхность для интеграций между ERP, WMS, MES, сайтами, 1C, принтерами и внешними API.

Главная идея: каждое входящее сообщение превращается в **событие**, каждый запуск пишет **timeline**, каждый шаг оставляет **артефакты**, а ошибку можно разобрать и повторить без угадываний.

{{screenshot:Главная панель: ошибки, очередь, здоровье и последние события}}

## Когда использовать OMH

- 1C отправляет данные на сайт или в WMS.
- Сайт вызывает 1C HTTP-сервис через безопасный endpoint.
- Нужно увидеть оригинальную ошибку внешней системы.
- Нужно повторить событие после исправления данных.
- Нужно отделить runtime интеграции от кода конкретного клиента.

## Базовый путь события

\`\`\`text
External system -> OMH Endpoint -> Event -> Workflow/Flow -> Target system -> Timeline
\`\`\`

## Что открывать первым

1. **Plugin Store** — установите нужный пакет.
2. **Connectors** — создайте подключение к внешней системе.
3. **Integration Flows** — настройте маршрут данных.
4. **Test Console** — отправьте тестовый payload.
5. **Timeline** — проверьте шаги, артефакты и ошибки.` },
        { packageId: 'core', sectionId: 'start', slug: 'concepts', title: 'Основные понятия', description: 'Endpoint, route, flow, workflow, mapping, resolver, package.', order: 20, markdown: `# Основные понятия

## Endpoint

Endpoint — входная точка OMH. Например, 1C POST отправляет JSON на URL вида:

\`\`\`bash
curl -X POST http://localhost:8000/api/bus/in/onec-orders \\
  -H 'Content-Type: application/json' \\
  -d '{"order_id":"SO-1001"}'
\`\`\`

## Route

Route решает, куда отправить событие и какие lookup/transformation шаги выполнить.

## Integration Flow

Integration Flow — no-code сценарий: matcher, lookup, transform, target action. Для 1C это основной инструмент внедренца.

## Workflow

Workflow — более низкоуровневый runtime plan. Он полезен для разработчиков и сложных сценариев.

## Mapping

Mapping превращает один JSON/XML формат в другой. Хороший mapping хранит версию и может быть проверен тестом.

## Resolver

Resolver ищет бизнес-объект: контрагента по ИНН, номенклатуру по коду, склад по external id.

## Business Rule

Business Rule принимает решение: блокировать, отправить в другой endpoint, изменить priority или применить fallback.

## Package

Package добавляет доменную функциональность: 1C, Printer, Auth, Secrets. Registered не значит installed. Рабочие страницы появляются только когда package installed и enabled.` },
      ] },
    ],
  },
  {
    id: 'onec', title: '1C', description: 'Практические инструкции для 1C OData, XML, HTTP-сервисов, Cockpit и Flow Builder.', order: 20, accent: 'green',
    sections: [
      { id: 'overview', title: 'Обзор 1C', description: 'Что дает 1C package.', order: 10, pages: [
        { packageId: 'onec', sectionId: 'overview', slug: 'overview', title: 'Обзор 1C Package', description: 'OData, HTTP-сервисы, XML, печать, integration bus.', order: 10, markdown: `# Обзор 1C Package

1C Package добавляет в OMH рабочие инструменты для интеграций с 1C: OData Explorer, XML Tools, 1C Cockpit, сценарии, шаблоны операций и guarded backend routes.

{{screenshot:1C Cockpit: обзор интеграций и быстрые действия}}

## Что можно сделать

- Читать справочники и документы через OData.
- Вызывать HTTP-сервисы 1C из внешнего сайта/API.
- Принимать raw XML, валидировать hash и пересылать дальше.
- Строить flow: **1C POST → OData lookup → JSON → endpoint**.
- Печатать ZPL через Printer Package.
- Смотреть timeline, артефакты и оригинальные ошибки 1C.

## Что важно

1C не является core. Сначала установите ` + '`omh-package-onec`' + ` в Plugin Store. Если пакет disabled, страницы покажут Package Gate вместо полурабочего UI.` },
      ] },
      { id: 'quick-start', title: 'Быстрый старт 1C', description: 'От установки до первого тестового события.', order: 20, pages: [
        { packageId: 'onec', sectionId: 'quick-start', slug: 'quick-start', title: 'Быстрый старт 1C', description: 'Пошаговая настройка первой интеграции.', order: 10, markdown: `# Быстрый старт 1C

## 1. Установите пакет

Откройте **Plugin Store**, найдите **1C Integration Package**, нажмите **Install**.

## 2. Создайте connector

Откройте **Connectors** и создайте 1C connector.

\`\`\`json
{
  "base_url": "https://onec.example.local/odata/standard.odata",
  "http_service_base_url": "https://onec.example.local/hs/omh",
  "auth": { "type": "basic", "username": "api", "password": { "$secret": "onec.api.password" } },
  "timeout_seconds": 30,
  "verify_ssl": true
}
\`\`\`

## 3. Проверьте соединение

Нажмите **Test config**. Если ошибка 401 — проверьте пользователя 1C и права публикации OData.

## 4. Создайте Integration Flow

В **Integration Flows** выберите preset или соберите flow вручную.

## 5. Отправьте тест

\`\`\`bash
curl -X POST http://localhost:8000/api/bus/in/onec-marking \\
  -H 'Content-Type: application/json' \\
  -d '{"inn":"1234567890","product_code":"ABC-123","codes":["code1","code2"]}'
\`\`\`

## 6. Откройте Timeline

Timeline покажет входной payload, lookup, transform, outgoing request, response и ошибку внешней системы, если она была.` },
      ] },
      { id: 'tools', title: 'Инструменты 1C', description: 'Connector, OData Explorer, XML Tools, Cockpit, Flow Builder.', order: 30, pages: [
        { packageId: 'onec', sectionId: 'tools', slug: 'connector', title: '1C Connector', description: 'Поля подключения и безопасные секреты.', order: 10, markdown: `# 1C Connector

## Поля

| Поле | Назначение |
| --- | --- |
| base_url | OData endpoint 1C, обычно заканчивается на /odata/standard.odata |
| http_service_base_url | База HTTP-сервисов 1C, например /hs/omh |
| auth | none или basic; пароль лучше хранить через Secrets Store |
| timeout_seconds | таймаут запроса к 1C |
| verify_ssl | проверка TLS сертификата |
| operations | дополнительные операции, опубликованные в 1C |

## Пример с secret reference

\`\`\`json
{
  "base_url": "https://onec.local/odata/standard.odata",
  "auth": {
    "type": "basic",
    "username": "omh_api",
    "password": { "$secret": "onec.odata.password" }
  },
  "timeout_seconds": 30,
  "verify_ssl": true
}
\`\`\`

## Проверка

Если connector не проходит health check, сначала проверьте URL из браузера/CLI, затем права пользователя в 1C, затем TLS.` },
        { packageId: 'onec', sectionId: 'tools', slug: 'odata-explorer', title: 'OData Explorer', description: 'Как смотреть ресурсы 1C, фильтровать и создавать lookup templates.', order: 20, markdown: `# OData Explorer

OData Explorer нужен, чтобы увидеть реальные ресурсы опубликованной базы 1C и быстро проверить запросы.

{{screenshot:OData Explorer: выбор connector и загрузка ресурсов}}

## Как пользоваться

1. Выберите 1C connector.
2. Нажмите **Load resources**.
3. Выберите resource.
4. Добавьте \`$filter\`, \`$select\`, \`$top\`.
5. Нажмите **Run query**.
6. Если запрос стабилен — создайте lookup template.

## Частые ресурсы 1C

\`\`\`text
Catalog_Контрагенты
Catalog_Номенклатура
Document_ЗаказКлиента
InformationRegister_ШтрихкодыНоменклатуры
\`\`\`

## Пример фильтра по ИНН

\`\`\`text
$filter=ИНН eq '1234567890'&$select=Ref_Key,Description,ИНН&$top=1
\`\`\`

## Пример curl

\`\`\`bash
curl 'https://onec.local/odata/standard.odata/Catalog_Контрагенты?$filter=ИНН%20eq%20%271234567890%27&$top=1' \\
  -u omh_api:password
\`\`\`

## Если resource не найден

- Проверьте публикацию OData в 1C.
- Проверьте права пользователя.
- Убедитесь, что имя resource совпадает с metadata.
- Откройте raw metadata и найдите entity set.` },
        { packageId: 'onec', sectionId: 'tools', slug: 'xml-tools', title: 'XML Tools', description: 'Raw XML, parse, hash, diff и raw-forward.', order: 30, markdown: `# XML Tools

XML Tools помогают работать с 1C XML без потери исходного тела сообщения.

## Основные режимы

- **Parse XML** — проверить, что XML валиден.
- **XML → JSON preview** — увидеть структуру для mapping.
- **Hash check** — сравнить контрольную сумму raw payload.
- **XML diff** — найти отличие между двумя XML.
- **Raw forward** — переслать исходный XML дальше без форматирования.

{{screenshot:XML Tools: raw forward и hash check}}

## Raw forward

Raw forward нужен, когда принимающая 1C система требует байт-в-байт близкий XML. OMH сохраняет оригинальный artifact и передает его как outgoing body.

\`\`\`xml
<Документ>
  <Номер>SO-1001</Номер>
  <Контрагент ИНН="1234567890" />
</Документ>
\`\`\`

## Hash check

Hash check полезен для споров: 1C утверждает, что XML другой. Вы открываете timeline artifact и сравниваете hash входного и исходящего тела.` },
        { packageId: 'onec', sectionId: 'tools', slug: 'cockpit', title: '1C Integration Cockpit', description: 'Продуктовая поверхность для создания 1C интеграций.', order: 40, markdown: `# 1C Integration Cockpit

Cockpit — это рабочее место внедренца. Он скрывает техническую сложность flow builder и предлагает понятные сценарии.

## Что есть на странице

- Быстрые действия: 1C → API, API → 1C, XML → 1C, 1C → Printer.
- Список интеграций.
- Состояние connector health.
- Последние события 1C.

## Как создать интеграцию

1. Нажмите **Create Integration**.
2. Выберите input mode: JSON, XML или proxy.
3. Выберите target action: REST endpoint, 1C HTTP service, printer.
4. Настройте matcher и mapping.
5. Нажмите **Test**.

{{screenshot:1C Cockpit: кнопка Create Integration}}

## Ошибки

Если test возвращает ошибку, не исправляйте вслепую. Откройте timeline: там видны request, response, external error и artifact diff.` },
        { packageId: 'onec', sectionId: 'tools', slug: 'visual-flow-builder', title: 'Visual Flow Builder', description: 'Сборка flow 1C POST → OData → JSON → endpoint.', order: 50, markdown: `# Visual Flow Builder

Visual Flow Builder нужен для сценариев, где одного mapping недостаточно.

## Типовой сценарий

\`\`\`text
1C POST
  ↓
OData lookup #1: контрагент по ИНН
  ↓
OData lookup #2: номенклатура по коду
  ↓
Build JSON
  ↓
Send to endpoint
\`\`\`

{{screenshot:Visual Flow Builder: цепочка lookup и preview результата}}

## Что проверять перед запуском

- Matcher выбирает нужные payload.
- Lookup template возвращает ровно один объект или понятный fallback.
- JSON builder не оставляет undefined/null в обязательных полях.
- Target endpoint имеет token или другой auth mode.

## Пример итогового JSON

\`\`\`json
{
  "pool_type": "DNP",
  "contractor_ref": "8f7a...",
  "product_ref": "b20c...",
  "codes": ["code1", "code2"]
}
\`\`\`` },
      ] },
      { id: 'examples', title: 'Примеры 1C', description: 'Готовые payload и сценарии.', order: 40, pages: [
        { packageId: 'onec', sectionId: 'examples', slug: 'external-api', title: '1C → внешний API', description: 'Отправка маркировочных кодов из 1C на сайт/API.', order: 10, markdown: `# 1C → внешний API

## Входной payload

\`\`\`json
{
  "pool_type": "DNP",
  "inn": "1234567890",
  "product_code": "ABC-123",
  "codes": ["code1", "code2"]
}
\`\`\`

## Что делает flow

1. Принимает POST от 1C.
2. Ищет контрагента в 1C по ИНН.
3. Ищет номенклатуру по product_code.
4. Собирает JSON для внешнего API.
5. Отправляет endpoint request.
6. Пишет timeline и artifacts.

## Ошибка внешнего API

Если внешний API вернул 400/500, OMH сохраняет оригинальное тело ответа во вкладке External error. Это важно для поддержки: видна причина, а не просто “ошибка отправки”.` },
        { packageId: 'onec', sectionId: 'examples', slug: 'site-to-1c', title: 'Сайт/API → 1C', description: 'Внешний сайт вызывает OMH, OMH обращается в 1C.', order: 20, markdown: `# Сайт/API → 1C

Сценарий: сайт создает заказ, OMH валидирует payload, затем вызывает HTTP-сервис 1C.

\`\`\`bash
curl -X POST http://localhost:8000/api/bus/in/site-order-to-1c \\
  -H 'Content-Type: application/json' \\
  -H 'X-OMH-Token: secret' \\
  -d '{"order_id":"WEB-42","inn":"1234567890","total":1900}'
\`\`\`

## Что настроить

- Endpoint auth token.
- 1C connector с http_service_base_url.
- Target action ` + '`call_1c_http_service`' + `.
- Error mapping для ошибок 1C.` },
        { packageId: 'onec', sectionId: 'examples', slug: 'xml-to-1c', title: '1C XML → 1C', description: 'Raw XML forwarding между 1C системами.', order: 30, markdown: `# 1C XML → 1C

Этот сценарий нужен, когда одна 1C отправляет XML, а другая 1C принимает почти тот же XML.

## Почему не парсить лишний раз

Если принимающая сторона проверяет подпись или hash, форматирование XML может сломать прием. Используйте raw-forward и храните parsed preview только как диагностический artifact.

\`\`\`xml
<ExchangeMessage id="SO-1001">
  <Warehouse>MAIN</Warehouse>
</ExchangeMessage>
\`\`\`` },
        { packageId: 'onec', sectionId: 'examples', slug: 'printer', title: '1C → принтер', description: 'Печать этикеток через Printer Package.', order: 40, markdown: `# 1C → принтер

1C отправляет print batch, OMH валидирует payload и передает ZPL в Printer Package.

\`\`\`json
{
  "printer": "LINE-1-ZEBRA",
  "labels": [
    { "sku": "ABC-123", "code": "010460..." }
  ]
}
\`\`\`

## Что смотреть при ошибке

- Printer health.
- Print job timeline.
- Raw ZPL artifact.
- TCP/network error до принтера.` },
      ] },
      { id: 'support', title: 'Ошибки и диагностика', description: 'Timeline, artifacts, replay и частые проблемы.', order: 50, pages: [
        { packageId: 'onec', sectionId: 'support', slug: 'errors-timeline', title: 'Ошибки и Timeline', description: 'Как читать ошибки 1C и внешних систем.', order: 10, markdown: `# Ошибки и Timeline

Timeline — главный инструмент поддержки.

## Что смотреть

- **Receive**: что реально пришло от 1C.
- **Lookup**: какой OData запрос ушел и что вернулось.
- **Transform**: какой JSON собрал OMH.
- **Send**: request/response внешней системы.
- **External error**: оригинальный текст ошибки.

## Replay

После исправления справочника или endpoint можно нажать Replay. Если нужно изменить payload, используйте Edit & Replay.

{{screenshot:Timeline: artifacts, external error и replay actions}}` },
        { packageId: 'onec', sectionId: 'support', slug: 'troubleshooting', title: 'Частые проблемы 1C', description: '401, OData not found, contractor not found, XML parse, printer unavailable.', order: 20, markdown: `# Частые проблемы 1C

## 1C вернула 401

Проверьте пользователя, пароль, права, публикацию OData/HTTP-сервиса. Если пароль хранится как secret, проверьте reference через Secrets Store.

## OData resource not found

Откройте metadata, найдите entity set. В русских конфигурациях имя может отличаться от ожидаемого.

## Контрагент не найден по ИНН

Проверьте пробелы, КПП, дубли, регистр и права чтения справочника.

## XML parse error

Сохраните raw artifact, проверьте encoding и namespace. Если XML надо только переслать — используйте raw-forward.

## Printer unavailable

Проверьте Printer Package, network route, порт принтера и print job logs.

## Endpoint token invalid

Проверьте endpoint auth mode и header ` + '`X-OMH-Token`' + `.` },
      ] },
    ],
  },
  {
    id: 'printer', title: 'Printer', description: 'ZPL печать, print jobs и диагностика принтеров.', order: 30, accent: 'blue',
    sections: [{ id: 'printer', title: 'Печать', description: 'ZPL и ошибки принтера.', order: 10, pages: [
      { packageId: 'printer', sectionId: 'printer', slug: 'overview', title: 'Printer Overview', description: 'Что делает Printer Package.', order: 10, markdown: `# Printer Package

Printer Package добавляет ZPL connector, print jobs, health checks и timeline печати.

## Типовой путь

\`\`\`text
1C / API -> OMH Print endpoint -> Print job -> ZPL printer -> Print logs
\`\`\`

{{screenshot:Printing page: очередь заданий и статус принтера}}` },
      { packageId: 'printer', sectionId: 'printer', slug: 'zpl', title: 'ZPL печать', description: 'Как отправлять ZPL и проверять результат.', order: 20, markdown: `# ZPL печать

\`\`\`text
^XA
^FO50,50^ADN,36,20^FDABC-123^FS
^XZ
\`\`\`

Проверяйте raw ZPL artifact, printer status и network errors. Если этикетка печатается неверно, сначала сравните ZPL, затем настройки принтера.` },
      { packageId: 'printer', sectionId: 'printer', slug: 'troubleshooting', title: 'Ошибки принтера', description: 'Unavailable, timeout, неверный ZPL.', order: 30, markdown: `# Ошибки принтера

## Printer unavailable
Проверьте IP, порт и доступность из контейнера/backend host.

## Timeout
Увеличьте timeout или проверьте сетевую задержку.

## Неверная этикетка
Сравните ZPL artifact с эталоном и настройками DPI.` },
    ] }],
  },
  {
    id: 'auth', title: 'Auth', description: 'Пользователи, login, bootstrap, recovery keys.', order: 40, accent: 'red',
    sections: [{ id: 'auth', title: 'Авторизация', description: 'Как включить и администрировать Auth Package.', order: 10, pages: [
      { packageId: 'auth', sectionId: 'auth', slug: 'install', title: 'Включение авторизации', description: 'Install Auth Package и bootstrap первого пользователя.', order: 10, markdown: `# Auth Package

Auth Package защищает только web UI и configuration API. Inbound integration endpoints не блокируются этим login.

## Как включить

1. Откройте Plugin Store.
2. Установите Auth Package.
3. Откройте сайт — появится bootstrap, если пользователей нет.
4. Создайте первого пользователя.
5. Сохраните recovery keys.

{{screenshot:Bootstrap first user page}}` },
      { packageId: 'auth', sectionId: 'auth', slug: 'users', title: 'Пользователи', description: 'Создание и отключение пользователей.', order: 20, markdown: `# Пользователи

У пользователей нет ролей в v1. Если пользователь enabled — он может работать в UI.

## Создать пользователя

Откройте **Users**, заполните username/password. После создания OMH покажет 5 recovery keys.` },
      { packageId: 'auth', sectionId: 'auth', slug: 'recovery', title: 'Recovery keys', description: 'Одноразовые ключи восстановления пароля.', order: 30, markdown: `# Recovery keys

Каждый пользователь получает одноразовые ключи восстановления. Ключ показывается один раз и сгорает после использования.

Если пользователь забыл пароль: откройте login, выберите recovery mode, введите username, recovery key и новый пароль.` },
    ] }],
  },
  {
    id: 'secrets', title: 'Secrets', description: 'Хранилище секретов и безопасные config references.', order: 50, accent: 'violet',
    sections: [{ id: 'secrets', title: 'Secrets Store', description: 'Secret references для 1C и REST.', order: 10, pages: [
      { packageId: 'secrets', sectionId: 'secrets', slug: 'overview', title: 'Что такое Secrets Store', description: 'Как хранить пароли вне connector JSON.', order: 10, markdown: `# Secrets Store

Secrets Store хранит реальные значения секретов и отдает UI только safe reference.

\`\`\`json
{ "$secret": "onec.odata.password" }
\`\`\`

Такой reference можно использовать в 1C connector, REST connector и endpoint auth config.` },
      { packageId: 'secrets', sectionId: 'secrets', slug: 'usage', title: 'Использование secret в connector', description: '1C и REST примеры.', order: 20, markdown: `# Использование secret

## 1C basic password

\`\`\`json
{
  "auth": {
    "type": "basic",
    "username": "omh_api",
    "password": { "$secret": "onec.odata.password" }
  }
}
\`\`\`

## REST bearer token

\`\`\`json
{
  "headers": {
    "Authorization": { "$secret": "rest.auth.header" }
  }
}
\`\`\`

При export config raw secret values маскируются.` },
    ] }],
  },
  {
    id: 'packages', title: 'Packages', description: 'Plugin Store, статусы пакетов и зависимости.', order: 60, accent: 'orange',
    sections: [{ id: 'packages', title: 'Пакеты', description: 'Lifecycle и установка.', order: 10, pages: [
      { packageId: 'packages', sectionId: 'packages', slug: 'plugin-store', title: 'Plugin Store', description: 'Available, installed, disabled, coming soon, in development.', order: 10, markdown: `# Plugin Store

Plugin Store показывает installable official packages и roadmap packages.

## Статусы

- **available** — можно установить.
- **installed** — установлен и включен.
- **disabled** — установлен, но выключен.
- **coming_soon** — показан в roadmap, установить нельзя.
- **in_development** — разрабатывается, заблокирован по умолчанию.
- **incompatible** — не подходит текущей версии OMH Core.

## Важно

Registered package code в monorepo не значит installed. Operational navigation появляется только после install + enable.` },
    ] }],
  },
];

function pageId(page: PageSeed) {
  return `${page.packageId}.${page.sectionId}.${page.slug}`;
}

function buildBundle(language: Language, seeds: PackageSeed[]): DocsLanguageBundle {
  return {
    language,
    packages: seeds.map((pkg) => ({
      ...pkg,
      sections: pkg.sections.map((section) => ({
        ...section,
        packageId: pkg.id,
        pages: section.pages.map((page) => ({ ...page, id: pageId(page), updatedAt, translationStatus: language === 'ru' ? 'complete' : 'in_progress' })),
      })),
    })),
  };
}

function translateSeeds(language: 'en' | 'zh'): PackageSeed[] {
  const prefix = language === 'en'
    ? 'Translation in progress. This page follows the Russian original and will be expanded with implementation-specific screenshots.'
    : '翻译正在进行中。本页保留与俄文原版相同的结构，后续会补充完整截图和本地化说明。';
  const titleMap: Record<string, string> = language === 'en' ? {
    'Быстрый старт': 'Quick Start', 'Основа продукта': 'Product basics', 'Что такое OMH': 'What is OMH', 'Основные понятия': 'Core concepts', 'Обзор 1C': '1C Overview', 'Обзор 1C Package': '1C Package overview', 'Быстрый старт 1C': '1C Quick Start', 'Инструменты 1C': '1C Tools', '1C Connector': '1C Connector', 'Примеры 1C': '1C Examples', '1C → внешний API': '1C -> External API', 'Сайт/API → 1C': 'Website/API -> 1C', '1C XML → 1C': '1C XML -> 1C', '1C → принтер': '1C -> Printer', 'Ошибки и диагностика': 'Errors and diagnostics', 'Ошибки и Timeline': 'Errors and Timeline', 'Частые проблемы 1C': '1C Troubleshooting', 'Печать': 'Printing', 'Printer Overview': 'Printer Overview', 'ZPL печать': 'ZPL printing', 'Ошибки принтера': 'Printer troubleshooting', 'Авторизация': 'Auth', 'Включение авторизации': 'Enable Auth', 'Пользователи': 'Users', 'Recovery keys': 'Recovery keys', 'Secrets Store': 'Secrets Store', 'Что такое Secrets Store': 'What is Secrets Store', 'Использование secret в connector': 'Use secret in connector', 'Пакеты': 'Packages'
  } : {
    'Быстрый старт': '快速开始', 'Основа продукта': '产品基础', 'Что такое OMH': '什么是 OMH', 'Основные понятия': '核心概念', 'Обзор 1C': '1C 概览', 'Обзор 1C Package': '1C 软件包概览', 'Быстрый старт 1C': '1C 快速开始', 'Инструменты 1C': '1C 工具', '1C Connector': '1C 连接器', 'Примеры 1C': '1C 示例', '1C → внешний API': '1C → 外部 API', 'Сайт/API → 1C': '网站/API → 1C', '1C XML → 1C': '1C XML → 1C', '1C → принтер': '1C → 打印机', 'Ошибки и диагностика': '错误与诊断', 'Ошибки и Timeline': '错误与时间线', 'Частые проблемы 1C': '1C 常见问题', 'Печать': '打印', 'Printer Overview': '打印概览', 'ZPL печать': 'ZPL 打印', 'Ошибки принтера': '打印机错误', 'Авторизация': '认证', 'Включение авторизации': '启用认证', 'Пользователи': '用户', 'Recovery keys': '恢复密钥', 'Secrets Store': '密钥库', 'Что такое Secrets Store': '什么是密钥库', 'Использование secret в connector': '在连接器中使用密钥', 'Пакеты': '软件包'
  };
  return ruSeeds.map((pkg) => ({
    ...pkg,
    title: titleMap[pkg.title] ?? pkg.title,
    description: `${prefix} ${pkg.description}`,
    sections: pkg.sections.map((section) => ({
      ...section,
      title: titleMap[section.title] ?? section.title,
      description: section.description,
      pages: section.pages.map((page) => ({
        ...page,
        title: titleMap[page.title] ?? page.title,
        description: page.description,
        markdown: `# ${titleMap[page.title] ?? page.title}\n\n> ${prefix}\n\n${page.markdown.replace(/^# .+\n\n/, '')}`,
      })),
    })),
  }));
}

export const docsBundles: Record<Language, DocsLanguageBundle> = {
  ru: buildBundle('ru', ruSeeds),
  en: buildBundle('en', translateSeeds('en')),
  zh: buildBundle('zh', translateSeeds('zh')),
};

export function getDocsBundle(language: Language) {
  return docsBundles[language] ?? docsBundles.ru;
}

export function flattenDocs(bundle: DocsLanguageBundle): DocsPageRecord[] {
  return bundle.packages.flatMap((pkg) => pkg.sections.flatMap((section) => section.pages));
}

export function findDocPage(bundle: DocsLanguageBundle, packageId?: string, sectionId?: string, pageId?: string): DocsPageRecord {
  if (!packageId) return flattenDocs(bundle)[0];
  const pkg = bundle.packages.find((item) => item.id === packageId) ?? bundle.packages[0];
  if (!sectionId) return pkg.sections[0].pages[0];
  const section = pkg.sections.find((item) => item.id === sectionId) ?? pkg.sections[0];
  if (!pageId) return section.pages[0];
  return section.pages.find((item) => item.slug === pageId) ?? section.pages[0];
}

export function pagePath(page: DocsPageRecord) {
  return `/docs/${page.packageId}/${page.sectionId}/${page.slug}`;
}

export function packageOverviewPath(pkg: DocsPackageRecord) {
  const page = pkg.sections[0]?.pages[0];
  return page ? pagePath(page) : '/docs';
}
