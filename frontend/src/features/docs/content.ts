import type { Language } from '../../i18n/dictionary';
import type { DocsLanguageBundle, DocsPackageId, DocsPageRecord, DocsPackageRecord } from './types';
import { onecPackageSeed } from './onecContent';

const updatedAt = '2026-07-13';

export type PageSeed = Omit<DocsPageRecord, 'id' | 'updatedAt' | 'translationStatus'>;

export type PackageSeed = {
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
      { id: "learning-path", title: "Путь обучения OMH", description: "Понятный маршрут от первой идеи интеграции до включения production.", order: 9, pages: [
        { packageId: 'core', sectionId: "learning-path", slug: "what-is-omh", title: "Что такое OMH простыми словами", description: "OMH как диспетчер интеграций между 1С, WMS, API, XML, принтерами и файлами.", order: 10, markdown: [
          "# Путь обучения OMH",
          "",
          "OMH — это место, где интеграция настраивается как понятный маршрут: кто отправляет данные, что нужно прочитать или преобразовать, куда отправить результат и где посмотреть выполнение.",
          "",
          "## 1. Что такое OMH простыми словами",
          "",
          "```text",
          "1С / WMS / сайт / API / XML / расписание",
          "  -> OMH endpoint или polling job",
          "  -> Scenario / Pattern wizard",
          "  -> Connection Center",
          "  -> Operation Catalog",
          "  -> Data Contract",
          "  -> Mapping Center",
          "  -> Preview / Test",
          "  -> Timeline + artifacts",
          "  -> Enable integration",
          "```",
          "",
          "OMH не заставляет пользователя начинать с workflow JSON. Пользователь начинает с реального сценария: “WMS отправляет факт в 1С”, “1С печатает этикетки”, “внешний API спрашивает контрагента”.",
          "",
          "## Роли продукта",
          "",
          "| Часть OMH | Простыми словами | Где в UI |",
          "| --- | --- | --- |",
          "| Scenario Router | Помогает выбрать тип интеграции | `/integration-start` |",
          "| Connection Center | Куда OMH может подключаться | `/connection-center` |",
          "| Operation Catalog | Что OMH делает в подключении | `/operation-catalog` |",
          "| Data Contracts | Какие поля должны быть на входе/выходе | `/mapping-center` |",
          "| Mapping Center | Как переложить поля из одного формата в другой | `/mapping-center` |",
          "| Pattern Wizard | Пошаговая настройка конкретного сценария | `/master?pattern=...` |",
          "| Timeline | Что реально произошло при запуске | `/events` |",
          "| Artifact | Сохранённый request/response/preview шага | Timeline события |",
          "",
          "## Главное правило обучения",
          "",
          "Не включайте integration сразу. Сначала выберите сценарий, настройте профили, проверьте preview, запустите saved test case, откройте Timeline и только потом включайте production."
        ].join('\n') },
        { packageId: 'core', sectionId: "learning-path", slug: "choose-scenario", title: "Как выбрать сценарий интеграции", description: "Integration Start examples: от бизнес-задачи к pattern wizard.", order: 20, markdown: [
          "# Как выбрать сценарий интеграции",
          "",
          "Начинайте с вопроса: **кто вызывает OMH и что должно получиться**.",
          "",
          "::open-page{route=\"/integration-start\" label=\"Открыть Scenario Router\"}",
          "",
          "## Примеры выбора",
          "",
          "| Бизнес-задача | Что выбрать в Integration Start | Куда ведёт |",
          "| --- | --- | --- |",
          "| Внешний сервис спрашивает контрагента из 1С | Внешний API -> 1С OData -> ответ | Request -> OData -> Response |",
          "| 1С отправляет заказ на сайт | 1С/API -> OData -> внешний endpoint | Request -> OData -> Send Endpoint |",
          "| DnP запрашивает коды ЧЗ | DnP -> OData order -> foreach codes -> DnP | DnP CHZ wizard |",
          "| 1С выгружает готовый пул кодов ЧЗ | 1С -> файл -> optional SMB/forward | CHZ Code Pool Workbench |",
          "| WMS присылает факт отгрузки | WMS -> 1C HTTP Service | WMS Fact -> 1C wizard |",
          "| XML нужно переслать как есть | XML raw forwarding | XML Raw Bridge |",
          "| XML содержит номер заказа и ждёт XML ответ | XML -> OData -> XML response | XML OData XML Response wizard |",
          "| 1С печатает этикетки | 1С -> labels[] -> ZPL -> printer | Request -> Printer wizard |",
          "| OMH сам читает 1С по расписанию | Poll OData -> Send Target | Polling wizard |",
          "",
          "## Что проверять на карточке сценария",
          "",
          "- **Настроить** должно открывать готовый wizard или workbench.",
          "- **Открыть инструкцию** должно вести на tutorial с payload, curl, preview, test и Timeline.",
          "- **Попробовать на учебном стенде** должно вести в Training Sandbox, если example уже есть.",
          "- Если сценарий planned, карточка должна объяснить, чего не хватает, и не открывать production wizard."
        ].join('\n') },
        { packageId: 'core', sectionId: "learning-path", slug: "setup-flow", title: "Общая схема настройки", description: "10 шагов от scenario до production enable.", order: 30, markdown: [
          "# Общая схема настройки",
          "",
          "## 10 шагов настройки",
          "",
          "1. Откройте `/integration-start` и выберите сценарий.",
          "2. Откройте инструкцию сценария и скопируйте учебный payload.",
          "3. Создайте профили в Connection Center: 1C OData, 1C HTTP Service, REST API, Printer, SMB/local.",
          "4. Создайте или выберите операции в Operation Catalog: конкретный path, method, success condition, extractors.",
          "5. Проверьте Data Contract: какие поля обязательны и каких типов они должны быть.",
          "6. Соберите Mapping: откуда берутся поля и где нужно сохранить array/object без превращения в string.",
          "7. Откройте pattern wizard и пройдите шаги без ручного workflow JSON.",
          "8. Проверьте Preview: rendered filter, target payload, response, warnings.",
          "9. Запустите Saved Test Case или dry-run и откройте Timeline/artifacts.",
          "10. Включите integration только после понятного successful test и зафиксируйте, где смотреть troubleshooting.",
          "",
          "## Минимальный production gate",
          "",
          "```text",
          "Scenario selected",
          "  -> connections tested",
          "  -> operations tested dry-run",
          "  -> contracts/mappings validated",
          "  -> wizard preview clean",
          "  -> saved test case passed",
          "  -> Timeline artifacts checked",
          "  -> integration enabled manually",
          "```",
          "",
          "## Когда остановиться",
          "",
          "Остановитесь и не включайте integration, если нет tutorial, нет training/example payload, preview показывает type mismatch, target operation не проверена, или Timeline не сохраняет исходный request и target response."
        ].join('\n') }
      ] },
      { id: "concepts", title: "Основные понятия", description: "Scenario, Connection, Operation, Contract, Mapping, Wizard, Timeline и Artifact.", order: 11, pages: [
        { packageId: 'core', sectionId: "concepts", slug: "overview", title: "Основные понятия OMH", description: "Словарь ключевых объектов платформы с примерами и ссылками на UI.", order: 10, markdown: [
          "# Основные понятия OMH",
          "",
          "## Scenario / Pattern",
          "",
          "Scenario — бизнес-задача пользователя: “WMS отправляет факт в 1С”, “1С печатает этикетки”, “DnP запрашивает коды ЧЗ”. Pattern — технический шаблон, который эту задачу реализует.",
          "",
          "Пример: scenario “Внешний сервис спрашивает данные из 1С” использует pattern `request_odata_response`.",
          "",
          "Где в UI: `/integration-start`, `/integration-patterns`.",
          "",
          "## Connection",
          "",
          "Connection — куда OMH может подключиться: 1C OData, 1C HTTP Service, REST API, Printer, SMB или local directory.",
          "",
          "Пример: `OData ERP production` с URL `/odata/standard.odata`.",
          "",
          "Где в UI: `/connection-center`.",
          "",
          "## Operation",
          "",
          "Operation — что OMH делает внутри подключения: `POST /shipment-facts`, `POST /api/v2/integrations/omh/chz/codes/import`, `/order-external-id`.",
          "",
          "Где в UI: `/operation-catalog`.",
          "",
          "## Data Contract",
          "",
          "Data Contract описывает поля, типы и обязательность request/response. Он отвечает на вопрос: “какой JSON/XML ожидает операция”.",
          "",
          "Пример: `payload.rows` должен быть array и required для DNP CHZ import.",
          "",
          "Где в UI: `/mapping-center`.",
          "",
          "## Mapping",
          "",
          "Mapping описывает, откуда взять данные для контракта: из входящего request, OData response, context, constant или dynamic object key.",
          "",
          "Пример: `payload.rows <- codes`, `payload.order_numbers_by_basis[order.Ref_Key] <- order.Number`.",
          "",
          "Где в UI: `/mapping-center`.",
          "",
          "## Wizard",
          "",
          "Wizard — пошаговый мастер, который ведёт пользователя по scenario и создаёт endpoint/flow/job/test case без ручного workflow JSON.",
          "",
          "Где в UI: `/master?pattern=...`.",
          "",
          "## Timeline",
          "",
          "Timeline — история выполнения одного события или run: входящий request, OData, mapping, target call, response, errors.",
          "",
          "Где в UI: Events, Test Console, Polling run history, CHZ journal.",
          "",
          "## Artifact",
          "",
          "Artifact — сохранённый request, response или промежуточный результат шага. Artifact нужен, чтобы не гадать, что ушло во внешнюю систему.",
          "",
          "Примеры: `incoming.request.json`, `odata_query_response.json`, `target_payload.json`, `printer_response.json`.",
          "",
          "## Disabled by default",
          "",
          "Новые интеграции создаются выключенными. Это защита от случайного production запуска. Сначала preview/test/Timeline, затем явное enable.",
          "",
          "Где в UI: success panel wizard, compiled integration details, polling job settings."
        ].join('\n') }
      ] },
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
        { packageId: 'core', sectionId: 'start', slug: 'integration-patterns', title: 'Как выбрать правильный мастер интеграции', description: 'Scenario Router и Integration Patterns: выбираем мастер от задачи, а не от технических терминов.', order: 30, markdown: `# Как выбрать правильный мастер интеграции

OMH начинается с вопроса: **что вы хотите интегрировать?**

Не начинайте с endpoint, route, workflow или builder_json. Сначала выберите integration pattern — типовой класс задачи.

::open-page{route="/integration-start" label="Открыть Scenario Router"}

## Основные patterns

| Если задача звучит так | Pattern | Что открыть |
| --- | --- | --- |
| Внешний сервис ждёт ответ | Request -> Response | Request/Response Workbench |
| Внешний сервис ждёт данные из 1С | Request -> OData -> Response | Мастер OData-интеграции |
| Нужно прочитать документ и строки | Request -> Multiple OData -> Response | Мастер OData-интеграции |
| Нужно обогатить через OData и отправить API | Request -> OData -> Send Endpoint | Мастер OData-интеграции |
| Нужно foreach по массиву и отправка | Request -> OData -> Foreach OData -> Send Endpoint | Мастер OData-интеграции |
| XML нужно переслать без изменения | XML Raw Bridge | XML Tools |
| Нужно сохранить файл и optional forward | Request -> Save File -> Optional Forward | Пулы кодов ЧЗ |
| Нужно печатать | Request -> Print | Printing |
| OMH должен сам читать OData по расписанию | Poll OData -> Send Target | \`/master?pattern=poll_odata_send_target\` |
| Нужно записать external_id обратно в 1С | Source -> Web API -> Write Back to 1C | Мастер 1С → сайт → запись ответа |

## Как работает Scenario Router

Страница \`/integration-start\` показывает сценарии человеческим языком:

- что приходит;
- что делает OMH;
- что получится;
- какой мастер будет открыт.

Анкета вызывает:

\`\`\`http
POST /api/integration-patterns/recommend
\`\`\`

Старт паттерна вызывает:

\`\`\`http
POST /api/integration-patterns/start
\`\`\`

Если pattern доступен, OMH возвращает \`wizard_route\`. Если pattern только зарегистрирован, start вернёт ошибку и объяснит, что wizard ещё не реализован.

## Где смотреть результат

После теста смотрите Timeline события. Для production-specific инструментов, например Пулы кодов ЧЗ, основной журнал находится внутри workbench.` },
        { packageId: 'core', sectionId: 'start', slug: 'integration-scenarios', title: 'Какие интеграции можно настроить в OMH', description: 'Матрица реальных интеграционных сценариев, статусы готовности и правила запуска.', order: 40, markdown: `# Какие интеграции можно настроить в OMH

Эта страница отвечает на практический вопрос: **можно ли уже настроить конкретный сценарий в OMH, где мастер, где документация и где troubleshooting**.

Source of truth — backend registry:

\`\`\`text
GET /api/integration-coverage
GET /api/integration-coverage/summary
GET /api/integration-coverage/{requirement_id}
\`\`\`

::open-page{route="/integration-coverage" label="Открыть матрицу покрытия"}
::open-page{route="/integration-start" label="Открыть Scenario Router"}

## Что считается покрытым

| Измерение | Что должно быть |
| --- | --- |
| Wizard / workbench | Пользователь может открыть конкретный мастер или production workbench |
| Docs / recipe | Есть страница с endpoint, payload, шагами и проверкой |
| Training | Есть training example или понятный sandbox path |
| Troubleshooting | Есть playbook по симптомам и сценариям |
| E2E / tests | Есть pytest/saved test coverage или явно указан gap |

## Основные сценарии

Матрица содержит не меньше 11 реальных кейсов:

- внешний API спрашивает 1С по ИНН;
- внешний API спрашивает заказ и ждёт XML response;
- 1С отправляет заказ во внешний API;
- DnP запрашивает пул кодов Честного знака из 1С;
- 1С отправляет пул кодов ЧЗ файлом;
- XML raw bridge между 1С;
- XML request -> OData -> XML response;
- WMS отправляет факт отгрузки в 1С;
- 1С -> сайт -> запись ответа обратно в 1С;
- 1С отправляет данные на печать;
- OMH периодически читает OData и отправляет изменения;
- request -> validation/rules -> разные targets.

## Как читать статусы

- \`ready\` — можно запускать из Scenario Router.
- \`partial\` — wizard/workbench есть, но в матрице видны незакрытые gaps.
- \`planned\` — сценарий показан как направление, но старт заблокирован.
- \`missing_docs\` / \`missing_wizard\` — нельзя начинать без закрытия соответствующего gap.

Scenario Router использует эту же матрицу. Поэтому planned/missing сценарии не должны открывать мастер даже если pattern зарегистрирован.

## Gate перед релизом

Проверка:

\`\`\`bash
make integration-coverage-check
make integration-docs-coverage-check
\`\`\`

Отчёт:

\`\`\`text
docs/reports/integration-coverage-report.md
\`\`\`

Если добавляете новый pattern или recipe, обновите registry и запустите coverage check. Не создавайте вторую статическую таблицу во frontend.` },
      ] },
      { id: 'connection-center', title: 'Connection Center', description: 'Профили подключений для мастеров, обучения и production.', order: 15, pages: [
        { packageId: 'core', sectionId: 'connection-center', slug: 'overview', title: 'Connection Center: профили подключений', description: 'Как создать reusable profile для 1C OData, 1C HTTP Service, REST API, принтера, SMB и локальной директории.', order: 10, markdown: `# Connection Center: профили подключений

Connection Center — это пользовательский каталог подключений. Он скрывает технический слой \`connector_instances\` и показывает внедренцу понятные **профили подключения**.

::open-page{route="/connection-center" label="Открыть Connection Center"}
::open-page{route="/operation-catalog" label="Открыть Operation Catalog"}

## Что такое профиль подключения

Профиль подключения отвечает на вопрос: **куда OMH будет ходить из мастера интеграции**.

Если нужно переиспользовать конкретное действие внутри подключения, например \`POST /shipment-facts\` или \`POST /api/v2/integrations/omh/chz/codes/import\`, создайте **Operation Profile** в Operation Catalog. Связь такая: \`Connection Profile -> Operation Profile -> Pattern Wizard\`.

| Тип | Когда использовать | Пример |
| --- | --- | --- |
| 1C OData | Читать справочники, документы, регистры из 1С | \`OData ERP\` |
| 1C HTTP Service | Записывать результат в HTTP-сервис 1С | \`1C ERP HTTP Service\` |
| REST API | Отправлять payload во внешний сервис | \`DNP API\`, \`WMS API\` |
| Принтер | Dry-run/test печати и ZPL target | \`LINE-1-ZEBRA\` |
| SMB share | Копировать файл для лазера/станка | \`\\\\\\\\172.16.8.133\\\\DataMatrixCodes\` |
| Локальная директория | Архив/outbox на сервере OMH | \`/var/lib/omh/outbox\` |
| Training mock | Учебные безопасные endpoints | \`Training DNP API\` |

## Практическая таблица профилей

| Тип профиля | Минимальные поля | Безопасная проверка | Где используется |
| --- | --- | --- | --- |
| 1C OData | name, base_url \`/odata/standard.odata\`, auth, username, password secret | \`$metadata\` или sample resource | OData Master, Request -> OData, Poll OData |
| 1C HTTP Service | base_url \`/hs/omh\`, auth, health_path optional | configured-success или health endpoint | WMS -> 1C, XML Raw Bridge, writeback |
| REST API | base_url, default headers, token secret | dry-run final URL/headers | Send Endpoint, DNP, WMS target |
| Printer | printer name, host, port, protocol, dpi | dry-run ZPL, no physical print | Request -> Printer |
| SMB/local | UNC/local path, credentials secret, safe test path | path validation; write/delete only after confirmation | CHZ file outbox, laser copy |

## Как назвать профили

Используйте имя, которое понятно внедренцу: \`OData ERP production\`, \`1C ERP HTTP Service\`, \`DNP API staging\`, \`LINE-1-ZEBRA\`, \`Laser SMB share\`.

Не называйте профиль просто \`prod\`, \`test\` или \`connector1\`: в wizard dropdown пользователь должен сразу понять, куда пойдёт запрос.
## OData ERP vs 1C HTTP Service

\`1C OData\` — это чтение данных из опубликованной базы 1С. Обычно URL заканчивается на \`/odata/standard.odata\`. Этот профиль выбирают в OData Master и в шагах \`OData Query\`.

\`1C HTTP Service\` — это вызов обработчика 1С по URL вида \`/hs/omh/...\`. Этот профиль выбирают, когда OMH должен записать результат обратно в 1С: факт WMS, external_id сайта, raw XML.

Не смешивайте эти два профиля. Если один сервер 1С поддерживает оба режима, создайте два профиля с понятными именами.

## Secrets

Sensitive fields можно заполнить двумя способами:

- \`$secret:name\` — production-вариант, значение берётся из Secrets Store.
- raw value — допустимо для локального стенда, но Connection Center покажет warning.

Пароли и tokens не возвращаются в UI: в masked config они отображаются как \`***\` или как \`{"$secret":"name"}\`.

## Тестирование

| Тип | Что делает Test |
| --- | --- |
| 1C OData | Проверяет \`$metadata\` или sample resource. Training mock возвращает metadata без реальной 1С. |
| 1C HTTP Service | Если health endpoint не задан, показывает configured-success без внешнего запроса. |
| REST API | Dry-run: показывает method, URL и headers без отправки. |
| Printer | Dry-run ZPL. Реальная печать требует отдельного подтверждения. |
| SMB share | Проверяет формат пути. Write/delete probe требует подтверждения и safe share. |
| Local directory | Проверяет наличие каталога; write/delete probe требует подтверждения. |

## Где профили используются

Connection Center options уже используются в мастерах:

- Request → OData → Response.
- Request → OData → Send Endpoint.
- DnP CHZ wizard.
- WMS → 1C HTTP Service.
- XML Raw Bridge.
- Request → Printer.
- Poll OData → Send Target.
- CHZ Code Pool Workbench settings.

Мастера показывают только enabled-профили подходящего типа. Если профиль disabled, он остаётся в каталоге, но исчезает из dropdown мастеров.

## Training Sandbox

После установки Training Sandbox в Connection Center появляются профили с badge \`Training\`:

- \`Training OData ERP\`.
- \`Training OData WMS\`.
- \`Training DNP API\`.
- \`Training Printer\`.

Используйте их для обучения и демонстраций. Они не требуют реальной 1С, DnP или принтера.

## Частые ошибки

- Выбрали 1C HTTP Service вместо OData, и мастер не видит resources.
- Отключили профиль, а потом он исчез из dropdown мастера.
- Ввели production password raw value вместо \`$secret:name\`.
- Указали URL web-клиента 1С вместо \`/odata/standard.odata\`.
- Проверяете SMB запись на production share без безопасного test path.
` },
      ] },
      { id: 'operation-catalog', title: 'Операции', description: 'Переиспользуемые действия внутри подключений.', order: 16, pages: [
        { packageId: 'core', sectionId: 'operation-catalog', slug: 'overview', title: 'Операции: переиспользуемые действия внутри подключений', description: 'Как Operation Profile связывает подключение и pattern wizard.', order: 10, markdown: `# Операции: переиспользуемые действия внутри подключений

Operation Catalog — это пользовательский каталог **операций подключения**. Он стоит поверх Connection Center и отвечает на вопрос: **какое действие OMH должен выполнить внутри выбранного подключения**.

::open-page{route="/operation-catalog" label="Открыть Operation Catalog"}
::open-page{route="/connection-center" label="Открыть Connection Center"}

## Connection Profile vs Operation Profile

| Уровень | Отвечает на вопрос | Пример |
| --- | --- | --- |
| Connection Profile | Куда OMH может подключиться? | \`1C ERP HTTP Service\`, \`DNP API\`, \`WMS API\` |
| Operation Profile | Какое действие выполнить в этом подключении? | \`POST /shipment-facts\`, \`POST /order-external-id\`, \`POST /api/v2/integrations/omh/chz/codes/import\` |
| Pattern Wizard | В каком бизнес-сценарии использовать действие? | \`WMS -> 1C\`, \`Source -> Web API -> Write Back to 1C\`, \`XML Raw Bridge\` |

Правильная цепочка:

\`\`\`text
Connection Profile -> Operation Profile -> Pattern Wizard
\`\`\`

Не храните один и тот же URL в каждом мастере. Создайте Connection Profile один раз, затем создайте операции для типовых действий и выбирайте их в мастерах.

## Connection = куда, Operation = что

| Вопрос | Объект | Пример |
| --- | --- | --- |
| Куда OMH может ходить? | Connection Profile | \`DNP API\`, \`1C ERP HTTP Service\`, \`WMS API\` |
| Что OMH делает там? | Operation Profile | \`POST /chz/codes/import\`, \`POST /shipment-facts\` |
| Какие поля нужны? | Data Contract | \`payload.rows[]\`, \`external_id\`, \`status\` |
| Откуда взять поля? | Mapping | \`codes -> payload.rows\`, \`site_response.external_id -> external_id\` |

## Практические примеры

| Сценарий | Connection | Operation | Success condition | Extractors |
| --- | --- | --- | --- | --- |
| DNP импорт кодов ЧЗ | \`DNP API\` | \`dnp_import_chz_codes\` | HTTP 2xx + \`success=true\` если API возвращает JSON | \`status\`, \`import_id\` optional |
| Запись external_id в 1С | \`1C ERP HTTP Service\` | \`onec_write_order_external_id\` | HTTP 2xx + \`success=true\` | \`message\`, \`external_id\` |
| WMS факт отгрузки в 1С | \`1C ERP HTTP Service\` | \`onec_accept_wms_shipment_fact\` | HTTP 2xx; business error сохранять в body | \`external_document_id\`, \`status\` |

## Dry run и real test

Dry run показывает final URL, method, headers, body preview, success condition и extractors. Real test делает реальный вызов и должен требовать явного подтверждения, если это не training/mock endpoint.
## Что хранит операция

Операция содержит:

- тип: REST API, 1C HTTP Service, Printer, File/SMB или Training;
- Connection Profile, если действие привязано к подключению;
- HTTP method, path или full URL;
- headers, body type и sample request;
- success condition;
- response extractors;
- timeout, tags и package id.

REST API и 1C HTTP Service реализованы как рабочие операции. Printer и File/SMB уже можно каталогизировать и проверять dry-run, production runners будут развиваться отдельно.

## Примеры операций

| Code | Тип | Когда использовать |
| --- | --- | --- |
| \`dnp_import_chz_codes\` | REST API | CHZ Code Pool Workbench отправляет массив кодов в DNP. |
| \`onec_write_order_external_id\` | 1C HTTP | Сайт вернул external_id, OMH записывает его обратно в 1С. |
| \`onec_accept_wms_shipment_fact\` | 1C HTTP | WMS прислал факт отгрузки, OMH передаёт его в 1С. |
| \`onec_receive_raw_xml\` | 1C HTTP | XML Raw Bridge пересылает XML в 1С без изменения тела. |

Кнопка **Установить presets** создаёт эти операции только если найдено подходящее подключение. Presets не заменяют ваши production-настройки автоматически.

## Success condition

Операция поддерживает условия:

- \`http_status_2xx\`;
- \`http_status_equals\`;
- \`json_path_equals\`;
- \`json_path_exists\`;
- \`response_contains_text\`;
- \`always_success\`.

Формат:

\`\`\`json
{
  "mode": "all",
  "conditions": [
    {"type": "http_status_2xx"},
    {"type": "json_path_equals", "path": "success", "value": true}
  ]
}
\`\`\`

Используйте \`mode: "all"\`, когда должны пройти все проверки. Используйте \`mode: "any"\`, когда достаточно одного допустимого ответа.

## Response extractors

Extractors забирают значения из ответа:

\`\`\`json
[
  {"name": "external_id", "path": "external_id", "required": true},
  {"name": "status", "path": "status", "required": false}
]
\`\`\`

Если required extractor не найден, test операции считается failed. Это защищает от ситуации, когда API вернул HTTP 200, но не вернул нужный business id.

## Тестирование

Dry-run не вызывает сеть. Он показывает:

- base URL подключения;
- final URL;
- method;
- headers;
- body preview;
- success condition;
- response extractors.

Real test требует явного подтверждения. По умолчанию он может использовать sample/mock response, чтобы автотесты и обучение не отправляли реальные запросы во внешние системы.

## Где операция выбирается

Operation selectors уже встроены в:

- Request -> OData -> Send Endpoint;
- Request -> OData -> Foreach OData -> Send Endpoint;
- Poll OData -> Send Target;
- Source -> Web API -> Write Back to 1C;
- WMS -> 1C;
- XML Raw Bridge;
- CHZ Code Pool Workbench external forward.

Если операция не выбрана, старые поля Manual endpoint/raw URL продолжают работать. Это нужно для обратной совместимости существующих интеграций.

## Частые ошибки

- Операция REST привязана к 1C HTTP Service подключению. Выберите REST API Connection Profile.
- Операция 1C HTTP привязана к OData подключению. Для записи в 1С нужен 1C HTTP Service.
- Path указан без начального \`/\`. Используйте \`/shipment-facts\`, а не \`shipment-facts\`.
- Disabled operation не появляется в dropdown мастеров.
- Disabled connection скрывает связанные операции из options.
- Required extractor не найден в sample response. Исправьте path или сделайте extractor optional.
` },
      ] },
      { id: 'data-contracts-and-mappings', title: 'Контракты данных и сопоставления полей', description: 'Contract-aware payload mapping для операций и мастеров.', order: 17, pages: [
        { packageId: 'core', sectionId: 'data-contracts-and-mappings', slug: 'overview', title: 'Контракты данных и сопоставления полей', description: 'Как описать expected payload операции и переиспользовать mapping в мастерах.', order: 10, markdown: `# Контракты данных и сопоставления полей

Mapping Center добавляет слой между Operation Catalog и pattern wizards. Он нужен, чтобы пользователь не собирал JSON вслепую.

::open-page{route="/mapping-center" label="Открыть Mapping Center"}
::open-page{route="/operation-catalog" label="Открыть Operation Catalog"}

## Четыре уровня

| Уровень | Что означает | Пример |
| --- | --- | --- |
| Connection | Куда подключаемся | \`DNP API\`, \`1C ERP HTTP Service\` |
| Operation | Что делаем в этом подключении | \`POST /chz/codes/import\`, \`POST /shipment-facts\` |
| Data Contract | Какие поля операция ожидает | \`payload.rows\` должен быть array и required |
| Mapping | Откуда взять эти поля | \`payload.rows <- codes\`, \`order_number <- order.Number\` |

Правильная цепочка:

\`\`\`text
Connection Center -> Operation Catalog -> Data Contract -> Mapping Center -> Pattern Wizard
\`\`\`

Если у операции нет контракта, мастер не блокируется. Он показывает предупреждение и разрешает raw template. Это нужно для legacy endpoints и быстрого прототипа.

## Что такое Data Contract

Data Contract описывает expected request или response операции:

\`\`\`json
{
  "type": "object",
  "fields": [
    {
      "path": "payload.rows",
      "type": "array",
      "required": true,
      "label": "Коды маркировки",
      "description": "Массив кодов ЧЗ должен остаться array"
    }
  ]
}
\`\`\`

Поддерживаемые типы: \`string\`, \`number\`, \`boolean\`, \`null\`, \`object\`, \`array\`, \`date\`, \`datetime\`, \`guid\`, \`raw\`.

## Что такое Mapping Profile

Mapping Profile описывает правила:

- \`variable\` — взять значение из source context и сохранить тип array/object;
- \`constant\` — записать фиксированное значение;
- \`template\` — собрать строку с \`{{path}}\`;
- \`dynamic_object_entry\` — создать ключ объекта из одного source path и значение из другого.

Пример:

\`\`\`json
{
  "version": 1,
  "fields": [
    {"target_path": "payload.rows", "source_type": "variable", "source": "codes", "preserve_type": true},
    {"target_path": "payload.order_number", "source_type": "variable", "source": "order.Number"},
    {"target_path": "omh.event_type", "source_type": "constant", "value": "ChestniyZnakCodesSyncRequested"}
  ],
  "dynamic_entries": []
}
\`\`\`

Preview рендерит payload и возвращает понятные ошибки:

\`\`\`json
{
  "error_code": "MAPPING_SOURCE_NOT_FOUND",
  "message": "Переменная order.Number не найдена."
}
\`\`\`

## Step-by-step: DNP contract и mapping

1. В Operation Catalog выберите \`dnp_import_chz_codes\`.
2. Привяжите Data Contract \`dnp_chz_codes_import_request\`.
3. Откройте Mapping Center и выберите preset \`mapping_dnp_chz_codes_import\`.
4. Проверьте обязательные поля: \`payload.rows\`, \`payload.order_id\`, \`payload.order_name\`, \`payload.onec_order_number\`.
5. Для \`payload.rows\` используйте source type \`variable\`, source \`codes\`, \`preserve_type=true\`.
6. Для dynamic object keys добавьте entry: key source \`order.Ref_Key\`, value source \`order.Number\`, target object \`payload.order_numbers_by_basis\`.
7. Нажмите Preview на sample context.
8. Исправьте missing paths до открытия wizard.

## Dynamic object keys

Dynamic object key нужен, когда target JSON должен содержать ключ, которого заранее нет в контракте:

\`\`\`json
{
  "payload": {
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}
\`\`\`

Preview должен отрендерить:

\`\`\`json
{
  "payload": {
    "order_numbers_by_basis": {
      "66666666-6666-6666-6666-666666666666": "260666/6938"
    }
  }
}
\`\`\`

## Raw JSON fallback

Raw JSON нужен для legacy endpoint или прототипа. Для production prefer Data Contract + Mapping, потому что validator поймает missing required field и type mismatch до реальной отправки.
## Пример: DNP import CHZ codes

Операция: \`dnp_import_chz_codes\`.

Контракт: \`dnp_chz_codes_import_request\`.

Mapping: \`mapping_dnp_chz_codes_import\`.

Основные правила:

| Target | Source |
| --- | --- |
| \`omh.run_id\` | \`context.run_id\` |
| \`omh.event_id\` | \`context.event_id\` |
| \`payload.order_ref_key\` | \`order.Ref_Key\` |
| \`payload.order_number\` | \`order.Number\` |
| \`payload.rows\` | \`codes\` |

Важно: \`payload.rows\` маппится как \`variable\`, поэтому массив кодов не превращается в строку.

## Пример: WMS shipment fact to 1C

Операция: \`onec_accept_wms_shipment_fact\`.

Контракт: \`onec_shipment_fact_request\`.

Mapping берёт:

| Target | Source |
| --- | --- |
| \`omh.event_id\` | \`context.event_id\` |
| \`payload.wms_shipment_id\` | \`request.body.wms_shipment_id\` |
| \`payload.order_ref_key\` | \`order.Ref_Key\` |
| \`payload.items\` | \`request.body.items\` |

Если \`payload.items\` required, validator покажет ошибку до запуска интеграции.

## Пример: Website order import

Операция может быть REST API endpoint сайта. Контракт \`website_order_import_request\` ожидает:

| Target | Source |
| --- | --- |
| \`source\` | constant \`OMH\` |
| \`site_code\` | \`request.body.site_code\` |
| \`order.uuid\` | \`order.Ref_Key\` |
| \`order.number\` | \`order.Number\` |
| \`order.date\` | \`order.Date\` |

Этот template доступен в мастере Request -> OData -> Send Endpoint.

## Как использовать в мастере

1. Установите presets в Operation Catalog и Mapping Center.
2. Откройте нужный pattern wizard.
3. В payload step нажмите **Use mapping template**.
4. Проверьте rendered payload в Mapping Center.
5. Если endpoint legacy или нестандартный, переключитесь на raw JSON/XML template.

## Troubleshooting

| Ошибка | Что делать |
| --- | --- |
| \`MAPPING_SOURCE_NOT_FOUND\` | Добавьте переменную в source context или исправьте source path. |
| \`MAPPING_REQUIRED_FIELD_MISSING\` | Заполните required target field или измените контракт. |
| \`MAPPING_TYPE_MISMATCH\` | Проверьте тип: array не должен получать string, number не должен получать object. |
| Операция без контракта | Можно использовать raw template, но лучше добавить Data Contract. |
` },
      ] },
      { id: "pattern-wizards", title: "Pattern Wizards", description: "Как работают мастера сценариев: шаги, disabled by default и preview.", order: 18, pages: [
        { packageId: 'core', sectionId: "pattern-wizards", slug: "what-is-wizard", title: "7.1 Что такое wizard", description: "Мастер сценария как безопасный путь от задачи к integration.", order: 10, markdown: [
          "# Pattern Wizards",
          "",
          "## 7.1 Что такое wizard",
          "",
          "Wizard — это не форма для заполнения workflow JSON. Это пошаговый сценарий, который переводит бизнес-задачу в проверяемую интеграцию.",
          "",
          "```text",
          "Scenario -> sample input -> connections -> operations -> contracts -> mapping -> preview -> save disabled -> test -> enable",
          "```",
          "",
          "Wizard должен показывать пользователю язык задачи: “найти заказ”, “собрать payload”, “отправить в WMS”, “вернуть XML”, “напечатать labels”. Низкоуровневые details остаются в advanced блоках и artifacts."
        ].join('\n') },
        { packageId: 'core', sectionId: "pattern-wizards", slug: "common-steps", title: "7.2 Общие шаги wizard", description: "Общий порядок шагов в мастерах OMH.", order: 20, markdown: [
          "# Общие шаги wizard",
          "",
          "## 7.2 Общие шаги мастера",
          "",
          "1. Выбрать scenario или открыть wizard из Scenario Router.",
          "2. Вставить входящий JSON/XML/raw sample.",
          "3. Проверить input contract и route key.",
          "4. Выбрать connection profiles.",
          "5. Выбрать operation profiles, если есть target action.",
          "6. Настроить OData/XML/file/printer-specific шаги.",
          "7. Применить Data Contract и Mapping.",
          "8. Посмотреть Preview.",
          "9. Сохранить integration disabled by default.",
          "10. Запустить Saved Test Case или manual dry-run.",
          "11. Открыть Timeline и artifacts.",
          "12. Включить integration вручную.",
          "",
          "Если wizard пропускает preview, test или disabled-by-default поведение, он не готов для обучения пользователя."
        ].join('\n') },
        { packageId: 'core', sectionId: "pattern-wizards", slug: "disabled-by-default", title: "7.3 Disabled by default", description: "Почему новые интеграции не включаются автоматически.", order: 30, markdown: [
          "# Disabled by default",
          "",
          "## 7.3 Почему integration создаётся выключенной",
          "",
          "OMH работает с production системами: 1С, WMS, сайтами, DnP, принтерами, SMB. Автоматически включать новую интеграцию после wizard опасно.",
          "",
          "Правило:",
          "",
          "```text",
          "Create integration -> enabled=false -> saved test case -> Timeline checked -> manual enable",
          "```",
          "",
          "## Что должен увидеть пользователь",
          "",
          "- Явный статус `enabled=false` после сохранения.",
          "- Кнопку запуска test case.",
          "- Ссылку на Timeline/run history.",
          "- Кнопку enable отдельно от save.",
          "- Предупреждение, если target action может реально отправить данные или напечатать этикетку."
        ].join('\n') },
        { packageId: 'core', sectionId: "pattern-wizards", slug: "preview", title: "7.4 Preview", description: "Что проверять в preview до сохранения и запуска.", order: 40, markdown: [
          "# Preview",
          "",
          "## 7.4 Что проверять в preview",
          "",
          "Preview должен отвечать на вопрос: “что именно OMH сделает, если я сохраню и запущу этот сценарий”.",
          "",
          "| Шаг | Что проверить |",
          "| --- | --- |",
          "| Incoming request | route key, business key, обязательные поля |",
          "| OData | connection, resource, rendered filter, select, top |",
          "| Payload / Mapping | target JSON/XML, типы array/object, dynamic keys |",
          "| Operation | final URL, method, headers, success condition, extractors |",
          "| Response | что получит caller |",
          "| Safety | disabled by default, dry-run/real-send distinction |",
          "",
          "## Что является ошибкой preview",
          "",
          "- Placeholder не найден.",
          "- Array превратился в string.",
          "- Dynamic object key не отрендерился.",
          "- Target URL пустой или private URL без warning.",
          "- Required extractor отсутствует.",
          "- Wizard предлагает real send без явного подтверждения."
        ].join('\n') }
      ] },
      { id: 'choosing-integration-scenario', title: 'Как выбрать сценарий интеграции', description: 'Решение от бизнес-задачи к pattern wizard.', order: 20, pages: [
        { packageId: 'core', sectionId: 'choosing-integration-scenario', slug: 'overview', title: 'Как выбрать сценарий интеграции', description: 'Scenario Router, coverage matrix и pattern certification в одном процессе.', order: 10, markdown: `# Как выбрать сценарий интеграции

Используйте порядок:

1. Откройте Scenario Router.
2. Выберите, кто вызывает OMH, что приходит и какой результат нужен.
3. Проверьте Coverage Matrix: сценарий должен быть \`ready\` или осознанно \`partial\`.
4. Проверьте Pattern Certification: мастер должен быть \`ready_for_training\` или иметь понятные gaps.
5. Запустите preview/test и только потом включайте production.

::open-page{route="/integration-start" label="Открыть Scenario Router"}
::open-page{route="/integration-coverage" label="Открыть Coverage Matrix"}
::open-page{route="/integration-patterns/certification" label="Открыть Pattern Certification"}

## Почему не начинать с технических объектов

Пользователь знает задачу: 1С отправляет заказ, WMS присылает факт, внешний API ждёт ответ. Поэтому старт должен быть от сценария. Технические детали остаются внутри мастера и в advanced pages.

## Быстрые решения

| Задача | Паттерн |
| --- | --- |
| Caller ждёт данные из 1С | Request -> OData -> Response |
| 1С отправляет данные во внешний API | Request -> OData -> Send Endpoint |
| Нужно прочитать заказ и строки | Request -> Multiple OData -> Response |
| XML переслать без изменения | XML Raw Bridge |
| OMH сам читает 1С по расписанию | Poll OData -> Send Target |
| WMS пишет факт в 1С | WMS Fact -> 1C |` },
      ] },
      { id: 'pattern-readiness', title: 'Готовность паттернов', description: 'Certification statuses и quality gate для мастеров.', order: 30, pages: [
        { packageId: 'core', sectionId: 'pattern-readiness', slug: 'overview', title: 'Готовность паттернов', description: 'Чем readiness отличается от business coverage.', order: 10, markdown: `# Готовность паттернов

Pattern Certification отвечает на вопрос: **качественно ли реализован мастер для сценария**.

Coverage Matrix отвечает на другой вопрос: **покрывает ли OMH бизнес-требование**.

::open-page{route="/integration-patterns/certification" label="Открыть готовность сценариев"}

## Статусы

| Status | Значение |
| --- | --- |
| \`not_started\` | сценарий известен, но стартовать его нельзя |
| \`partial\` | мастер есть, но есть gaps по training, docs, tests или UX |
| \`ready_for_training\` | можно обучать и прогонять training example |
| \`ready_for_production\` | есть production evidence и smoke run |
| \`deprecated\` | используется только для поддержки и миграции |

## Gate

Паттерн проверяется по UI, docs, training, tests, Timeline/run history и Simple Mode.

\`\`\`bash
make pattern-docs-check
make pattern-smoke
make simple-mode-ux-check
\`\`\`

Не переводите паттерн в \`ready_for_production\`, пока нет реального smoke evidence и понятного rollback/support path.` },
      ] },
      { id: 'why-wizard-not-workflow', title: 'Почему wizard, а не workflow', description: 'Product rationale для Simple Mode.', order: 40, pages: [
        { packageId: 'core', sectionId: 'why-wizard-not-workflow', slug: 'overview', title: 'Почему wizard, а не workflow', description: 'Simple Mode должен вести пользователя по задаче, а не по внутренним объектам.', order: 10, markdown: `# Почему wizard, а не workflow

Simple Mode нужен внедренцу и оператору, которые формулируют задачу бизнес-языком:

- 1С отправляет заказ на сайт;
- внешний API спрашивает контрагента по ИНН;
- WMS сообщает факт отгрузки;
- OMH сам читает изменения из 1С.

Wizard переводит эту задачу в безопасные шаги: входящий sample, lookup, payload/response, preview, save, test.

## Что остаётся в advanced

Низкоуровневые runtime-детали, raw artifacts и ручное редактирование конфигурации должны быть в advanced/developer pages или collapsed advanced details. Это снижает риск случайного production enable и делает обучение воспроизводимым.

## Contract для wizard

- preview не пишет в БД;
- save создаёт выключенную интеграцию или требует явного действия оператора;
- test/run history доступны до production enable;
- ошибки объясняют, что исправить;
- Simple Mode не показывает internal labels как основной пользовательский язык.` },
      ] },
    ],
  },
  onecPackageSeed,
  {
    id: 'reference', title: 'Reference', description: 'API и runtime contracts для интеграций.', order: 25, accent: 'green',
    sections: [
      { id: 'integration-master', title: 'Integration Master', description: 'Scenario chooser и Input Contract первого шага.', order: 5, pages: [
      { packageId: 'reference', sectionId: 'integration-master', slug: 'overview', title: 'Reference: Integration Master', description: 'Scenario chooser, input parser, endpoint slug и draft Input Contract.', order: 5, markdown: `# Reference: Integration Master

\`/master\` — первый шаг общего мастера интеграции. Он отвечает на вопрос: кто вызывает OMH и что придет во входящем запросе.

Step 1 сохраняет \`InputContract\`. Step 2A добавляет один OData Query, Step 2B читает табличную часть, Step 2C повторяет OData по массиву, Step 3A собирает \`target_payload\`, Step 4A выбирает финальное действие.

## Product route

\`\`\`text
/master
\`\`\`

## Backend endpoints

\`\`\`text
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
POST /api/integration-master/payload/preview
POST /api/integration-master/payload/validate
POST /api/integration-master/drafts/{draft_id}/payload-steps
POST /api/integration-master/final-action/preview
POST /api/integration-master/final-action/test
POST /api/integration-master/final-action/validate
POST /api/integration-master/drafts/{draft_id}/final-action
POST /api/integration-master/drafts/{draft_id}/validate-for-compile
POST /api/integration-master/drafts/{draft_id}/compile-preview
POST /api/integration-master/drafts/{draft_id}/compile
POST /api/integration-master/compiled/{integration_flow_id}/run-test
POST /api/integration-master/compiled/{integration_flow_id}/enable
\`\`\`

## Input Contract

\`\`\`json
{
  "name": "DnP запрашивает пул кодов Честного знака",
  "slug": "dnp_sinc_pull_codes",
  "input_mode": "json",
  "source_system": "dnp",
  "scenario_key": "dnp_chz_code_pool",
  "fields": [
    {
      "name": "Number",
      "path": "request.body.Number",
      "type": "string",
      "required": true,
      "example": "260666/6938"
    }
  ],
  "operation_key": {
    "type": "field",
    "field_path": "request.body.sinc",
    "value": "dnp_sinc_pull_codes",
    "fallback_paths": ["request.body.operation"]
  },
  "business_key": {
    "path": "request.body.order_name",
    "fallback_paths": ["request.body.Number"]
  }
}
\`\`\`

## Step 2A: один OData Query

После сохранения Input Contract в \`/master\` появляется один OData Query Builder.

Пример production order lookup:

\`\`\`text
Resource: Document_ЗаказНаПроизводство2_2
Filter: Number eq '{{request.body.Number}}'
$select: Ref_Key, Number, Date, Posted
$top: 1
$orderby: Date desc
save_as: order
required: true
\`\`\`

Preview рендерит sample value:

\`\`\`text
Number eq '260666/6938'
\`\`\`

После test query следующие шаги смогут использовать \`order.Ref_Key\`. Если 1C вернула пустой список и \`required=true\`, test вернёт \`ODATA_RESULT_EMPTY\`.

## Step 2B: табличная часть объекта 1С

После сохранения \`odata_query\` можно прочитать вложенный resource найденного объекта:

\`\`\`text
Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция
\`\`\`

Настройка:

\`\`\`text
object_variable: order
key_field: Ref_Key
key_type: guid
base_resource: Document_ЗаказНаПроизводство2_2
nested_resource: Продукция
$select: Номенклатура_Key, Количество, КоличествоУпаковок
save_as: products
\`\`\`

Будущие переменные:

\`\`\`text
products[]
products[0].Номенклатура_Key
products[0].Количество
\`\`\`

Если строк нет и \`required=true\`, test вернёт \`ODATA_TABULAR_PART_EMPTY\`.

## Step 2C: foreach OData по массиву

После сохранения \`odata_object_query\` можно пройти по \`products[]\` и выполнить OData-запрос для каждой строки.

\`\`\`text
items: products
item_as: product
Resource: InformationRegister_ПулКодовМаркировкиСУЗ
Filter: Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')
$select: ПолныйКодМаркировки,ДокументОснование,Номенклатура_Key,Статус
$top: 500
paginate: true
merge: flatten
save_as: codes
\`\`\`

Будущие переменные:

\`\`\`text
codes[]
codes[0].ПолныйКодМаркировки
codes[0].Номенклатура_Key
\`\`\`

Validation проверяет source array, \`$top <= 500\`, collision \`save_as\` и safety limits: \`max_items\`, \`max_requests\`, \`max_result_rows\`.

## Step 3A: payload builder

После сохранения \`foreach_odata\` можно собрать body без финальной отправки:

\`\`\`text
body_type: json | xml | raw_text
save_as: target_payload
template/table fields: request.body, order, products, codes, context
\`\`\`

JSON exact placeholder сохраняет тип: \`"{{codes}}"\` станет массивом, \`"{{order}}"\` станет объектом. Mixed template всегда строка: \`"dnp:{{request.body.order_name}}"\`.

Dynamic keys поддерживаются для DnP:

\`\`\`json
{
  "payload": {
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}
\`\`\`

Step 3A сохраняет только \`build_payload\`. Endpoint send, caller response, queue, Timeline runtime и full integration compile не выполняются.

## Step 4A: final action

После сохранения \`build_payload\` можно сохранить один \`final_action\` в draft.

Поддержанные варианты:

- \`return_response\` — вернуть JSON/XML/raw caller-у.
- \`send_endpoint\` — отправить \`target_payload\` во внешний endpoint и вернуть configured response.
- \`send_and_return_response\` — отправить endpoint и проксировать endpoint response.
- \`accepted_event\` — вернуть \`event_id\` и \`queue_item_id\` для async обработки.

Endpoint send пример:

\`\`\`text
method: POST
url: http://172.16.3.10/api/v2/integrations/omh/chz/codes/import
headers: {"Content-Type":"application/json"}
body_source: target_payload
body_type: json
return_to_caller: fixed_success {"ok": true}
\`\`\`

\`Preview final action\` не вызывает network. \`Test final action\` по умолчанию dry-run; real test должен подтверждаться в UI.

Private/localhost URL разрешены, но validation вернет warning. Form body, production publish, queue/retry/DLQ и Timeline runtime остаются следующими этапами.

## Step 5A: compile draft into real integration

После сохранения \`final_action\` мастер может создать реальные OMH objects:

\`\`\`text
IntegrationEndpoint
IntegrationRoute
IntegrationFlow
Workflow
SavedTestCase
\`\`\`

Порядок: \`validate-for-compile\`, \`compile-preview\`, затем \`compile\`.

Default compile request создаёт интеграцию выключенной:

\`\`\`json
{
  "enabled": false,
  "create_saved_test_case": true
}
\`\`\`

Duplicate slug не перезаписывается. Backend вернет: \`Endpoint /api/bus/in/{slug} уже существует. Выберите другой slug.\`

После создания запустите saved test case, проверьте Timeline и только потом включите интеграцию через \`POST /api/integration-master/compiled/{integration_flow_id}/enable\`.

## Parser rules

- JSON paths look like \`request.body.operation\`.
- Arrays expose \`request.body.items[]\` and first item paths such as \`request.body.items[0].sku\`.
- XML paths look like \`xml./Документ/Номер\`, with display path \`/Документ/Номер\`.
- Raw text exposes \`request.raw_text\` and simple \`key=value\` fields when possible.
- Sample size limit is 256 KB.

## Slug rule

Endpoint slug allows only lowercase letters, numbers, \`-\` and \`_\`, and must start and end with a letter or number.` },
      { packageId: 'reference', sectionId: 'integration-master', slug: 'payload-builder', title: 'Reference: Payload Builder', description: 'Step 3A build_payload: JSON, XML, raw text, placeholders and dynamic JSON keys.', order: 6, markdown: [
        '# Reference: Payload Builder',
        '',
        'Payload Builder is `/master` Step 3A. It builds a body and saves it as a variable, usually `target_payload`.',
        '',
        'It does not send HTTP requests, does not call a 1C HTTP service, does not return caller response, does not compile the full integration and does not touch queue/DLQ/runtime Timeline.',
        '',
        '## Endpoints',
        '',
        '```text',
        'POST /api/integration-master/payload/preview',
        'POST /api/integration-master/payload/validate',
        'POST /api/integration-master/drafts/{draft_id}/payload-steps',
        '```',
        '',
        '## Variables',
        '',
        '- `request.body.*` comes from Input Contract sample.',
        '- `order.*` comes from Step 2A.',
        '- `products[]` comes from Step 2B.',
        '- `codes[]` comes from Step 2C.',
        '- `context.run_id` and `context.event_id` are runtime context values.',
        '',
        'Supported paths include `order.Ref_Key`, `products[0].Номенклатура_Key`, `codes[0].ПолныйКодМаркировки` and `codes.length`.',
        '',
        '## JSON Rules',
        '',
        '- Exact placeholder preserves arrays and objects: `"{{codes}}"` renders as JSON array.',
        '- Exact object placeholder preserves object type: `"{{order}}"` renders as JSON object.',
        '- Mixed template renders as string: `"dnp:{{request.body.order_name}}"`.',
        '- Dynamic keys are rendered as strings, so `{ "{{order.Ref_Key}}": "{{order.Number}}" }` is valid.',
        '- Missing path returns `VARIABLE_NOT_FOUND` and a message like `Переменная order.Ref_Key не найдена.`',
        '',
        '## DnP Example',
        '',
        '```json',
        '{',
        '  "omh": {',
        '    "run_id": "{{context.run_id}}",',
        '    "event_id": "{{context.event_id}}",',
        '    "entity_id": "{{request.body.order_name}}",',
        '    "event_type": "ChestniyZnakCodesSyncRequested",',
        '    "entity_type": "DnPOrder",',
        '    "source_system": "Open Manufacturing Hub",',
        '    "target_system": "DnP",',
        '    "correlation_id": "dnp-chz-sync:{{request.body.order_name}}"',
        '  },',
        '  "payload": {',
        '    "rows": "{{codes}}",',
        '    "order_id": "{{request.body.order_id}}",',
        '    "order_name": "{{request.body.order_name}}",',
        '    "onec_order_number": "{{order.Number}}",',
        '    "order_numbers_by_basis": {',
        '      "{{order.Ref_Key}}": "{{order.Number}}"',
        '    }',
        '  }',
        '}',
        '```',
        '',
        '## XML and Raw Text',
        '',
        'XML template example: `<Response><RowsCount>{{codes.length}}</RowsCount></Response>`. Values are XML-escaped and rendered XML must be well-formed.',
        '',
        'Raw text example: `OK order={{order.Number}} codes={{codes.length}}`.',
        '',
        '## Save Contract',
        '',
        'Saved draft step:',
        '',
        '```json',
        '{',
        '  "id": "build_dnp_payload",',
        '  "type": "build_payload",',
        '  "body_type": "json",',
        '  "save_as": "target_payload",',
        '  "last_preview_status": "success"',
        '}',
        '```',
      ].join('\n') },
    ] },
    { id: 'odata-master', title: 'OData Master', description: 'Wizard spec, API и компиляция в Integration Flow.', order: 10, pages: [
      { packageId: 'reference', sectionId: 'odata-master', slug: 'overview', title: 'Reference: OData Master', description: 'Backend endpoints, wizard spec, limits and compiler output.', order: 10, markdown: `# Reference: OData Master

Backend endpoints:

\`\`\`text
GET  /api/odata-master/examples
POST /api/odata-master/preview
POST /api/odata-master/save
POST /api/odata-master/run-test
\`\`\`

All endpoints belong to \`omh-package-onec\`.

## Step types

- \`odata_query\`
- \`odata_object_query\`
- \`foreach_odata\`

## Final actions

- \`return_response\`
- \`send_endpoint\`
- \`send_onec_http_service\`
- \`async_accepted\`

The compiler creates a normal \`IntegrationFlow\`: endpoint, route, compiled workflow, \`builder_json\` and saved test case.

## Run test diagnostics

\`POST /api/odata-master/run-test\` returns \`diagnostics\` with:

- \`event_id\`
- \`timeline_url\`
- \`artifact_checklist\`
- \`next_actions\`

Use \`artifact_checklist\` to guide the user to \`odata_query_request.json\`, \`odata_query_response.json\`, \`foreach_result.json\`, \`outgoing_request.json\` and \`return_response.json\` in Timeline.

## Limits

- OData \`$top <= 500\`.
- Pagination uses \`$skip\` until OData connection \`max_pages\`.
- Exact JSON placeholders such as \`"{{codes}}"\` preserve array/object types.` },
    ] }],
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

const localizedMarkdownHeadings: Record<'en' | 'zh', Record<string, string>> = {
  en: {
    '# Старт за 15 минут': '# Start in 15 minutes',
    '# Что вы настроите в учебном сценарии': '# What you will build',
    '# Глоссарий терминов для 1C': '# Glossary for 1C users',
    '# Базовые понятия для пользователей 1C': '# Basic concepts for 1C users',
    '# Создаём OData-подключение к 1С': '# Create OData Connection',
    '# Проверяем OData-запрос в OData Master': '# Test OData in OData Master',
    '# Ищем контрагента по ИНН': '# Find Contractor by INN',
    '# Создаём входную точку для POST-запроса из 1С': '# Create inbound endpoint for 1C POST',
    '# Читаем значения из входящего запроса': '# Read values from incoming request',
    '# Первая выборка OData: контрагент по ИНН': '# First OData query: contractor by INN',
    '# Вторая выборка OData: товар по артикулу': '# Second OData query: product by article',
    '# Собираем целевой JSON': '# Build target JSON',
    '# Отправляем JSON во внешний API': '# Send to external API',
    '# Проверяем весь интеграционный поток': '# Test full flow',
    '# Симптом: 1C вернула 401': '# Symptom: 1C returned 401',
    '# Симптом: OData resource не найден': '# Symptom: OData resource not found',
    '# Симптом: контрагент не найден по ИНН': '# Symptom: Contractor not found by INN',
    '# Симптом: товар не найден по артикулу': '# Symptom: Product not found by article',
    '# Симптом: target API вернул ошибку': '# Symptom: Target API returned error',
    '# Симптом: XML не парсится': '# Symptom: XML parse failed',
    '# Симптом: принтер недоступен': '# Symptom: Printer unavailable',
    '# Симптом: событие попало в DLQ': '# Symptom: Event moved to DLQ',
    '## Что вы настроите': '## What you will build',
    '## Зачем это нужно': '## Why this matters',
    '## Что нужно заранее': '## Before you start',
    '## Пошаговая настройка': '## Step-by-step',
    '## Пример значений': '## Example values',
    '## Что должно получиться': '## What should happen',
    '## Проверьте себя': '## Check yourself',
    '## Частые ошибки': '## Common mistakes',
    '## Следующий урок': '## Next lesson',
    '## Что вы видите': '## What you see',
    '## Что это означает': '## What it means',
    '## Что проверить': '## What to check',
    '## Как исправить': '## How to fix',
    '## Где смотреть в OMH': '## Where to look in OMH',
    '## Связанные страницы': '## Related pages',
    '## Когда использовать': '## When to use',
    '## Схема': '## Scheme',
    '## URL endpoint': '## Endpoint URL',
    '## Ответ для 1C': '## Response for 1C',
    '## Ответ': '## Response',
    '## Входящий JSON': '## Incoming JSON',
    '## Итоговый JSON': '## Target JSON',
    '## Таблица полей': '## Field table',
    '## Таблица сопоставления полей': '## Field mapping table',
    '## Необязательные transforms': '## Optional transforms',
    '## Переменные': '## Variables',
    '## Lookup контрагента по ИНН': '## Contractor lookup by INN',
    '## Lookup товара по product_code': '## Product lookup by product_code',
    '## Endpoint и режим': '## Endpoint and mode',
    '## Как проверить, что XML не изменился': '## How to verify XML was not changed',
    '## Пример XML': '## XML example',
    '## Path к ИНН': '## Path to INN',
    '## Подстановка contractor UUID': '## Inject contractor UUID',
    '## Пример бизнес-ошибки 1C': '## 1C business error example',
    '## Шаг': '## Step',
    '## Целевой REST connector': '## Target REST connector',
    '## Целевой JSON': '## Target JSON',
    '## Вызов целевого HTTP-сервиса 1C': '## Target 1C HTTP service call',
    '## Целевой HTTP-сервис 1C': '## Target 1C HTTP service',
    '## Коннектор принтера': '## Printer connector',
    '## Бизнес-правила': '## Business rules',
    '## Целевой JSON для ветки DNP': '## Target JSON for DNP branch',
    '## Целевой JSON для ветки PRINT': '## Target JSON for PRINT branch',
  },
  zh: {
    '# Старт за 15 минут': '# 15 分钟开始',
    '# Что вы настроите в учебном сценарии': '# 你将构建什么',
    '# Глоссарий терминов для 1C': '# 1C 用户术语表',
    '# Базовые понятия для пользователей 1C': '# 面向 1C 用户的基础概念',
    '# Создаём OData-подключение к 1С': '# 创建 OData Connection',
    '# Проверяем OData-запрос в OData Master': '# 在 OData Master 中测试 OData',
    '# Ищем контрагента по ИНН': '# 按 INN 查找客户',
    '# Создаём входную точку для POST-запроса из 1С': '# 为 1C POST 创建入站 endpoint',
    '# Читаем значения из входящего запроса': '# 从入站请求读取值',
    '# Первая выборка OData: контрагент по ИНН': '# 第一个 OData 查询：按 INN 查找客户',
    '# Вторая выборка OData: товар по артикулу': '# 第二个 OData 查询：按货号查找商品',
    '# Собираем целевой JSON': '# 组装 target JSON',
    '# Отправляем JSON во внешний API': '# 发送到外部 API',
    '# Проверяем весь интеграционный поток': '# 测试完整 flow',
    '# Симптом: 1C вернула 401': '# 症状：1C 返回 401',
    '# Симптом: OData resource не найден': '# 症状：找不到 OData resource',
    '# Симптом: контрагент не найден по ИНН': '# 症状：按 INN 找不到客户',
    '# Симптом: товар не найден по артикулу': '# 症状：按货号找不到商品',
    '# Симптом: target API вернул ошибку': '# 症状：target API 返回错误',
    '# Симптом: XML не парсится': '# 症状：XML 解析失败',
    '# Симптом: принтер недоступен': '# 症状：打印机不可用',
    '# Симптом: событие попало в DLQ': '# 症状：事件进入 DLQ',
    '## Что вы настроите': '## 你将构建什么',
    '## Зачем это нужно': '## 为什么重要',
    '## Что нужно заранее': '## 开始之前',
    '## Пошаговая настройка': '## 分步设置',
    '## Пример значений': '## 示例值',
    '## Что должно получиться': '## 应该看到什么',
    '## Проверьте себя': '## 自我检查',
    '## Частые ошибки': '## 常见错误',
    '## Следующий урок': '## 下一课',
    '## Что вы видите': '## 你会看到什么',
    '## Что это означает': '## 这意味着什么',
    '## Что проверить': '## 需要检查什么',
    '## Как исправить': '## 如何修复',
    '## Где смотреть в OMH': '## 在 OMH 哪里查看',
    '## Связанные страницы': '## 相关页面',
    '## Когда использовать': '## 何时使用',
    '## Схема': '## 方案',
    '## URL endpoint': '## Endpoint URL',
    '## Ответ для 1C': '## 给 1C 的响应',
    '## Ответ': '## 响应',
    '## Входящий JSON': '## 入站 JSON',
    '## Итоговый JSON': '## Target JSON',
    '## Таблица полей': '## 字段表',
    '## Таблица сопоставления полей': '## 字段映射表',
    '## Необязательные transforms': '## 可选 transforms',
    '## Переменные': '## 变量',
    '## Lookup контрагента по ИНН': '## 按 INN 查找客户',
    '## Lookup товара по product_code': '## 按 product_code 查找商品',
    '## Endpoint и режим': '## Endpoint 与模式',
    '## Как проверить, что XML не изменился': '## 如何验证 XML 未被修改',
    '## Пример XML': '## XML 示例',
    '## Path к ИНН': '## INN path',
    '## Подстановка contractor UUID': '## 注入 contractor UUID',
    '## Пример бизнес-ошибки 1C': '## 1C 业务错误示例',
    '## Шаг': '## 步骤',
    '## Целевой REST connector': '## 目标 REST connector',
    '## Целевой JSON': '## Target JSON',
    '## Вызов целевого HTTP-сервиса 1C': '## 调用目标 1C HTTP 服务',
    '## Целевой HTTP-сервис 1C': '## 目标 1C HTTP 服务',
    '## Коннектор принтера': '## 打印机 connector',
    '## Бизнес-правила': '## 业务规则',
    '## Целевой JSON для ветки DNP': '## DNP 分支的 target JSON',
    '## Целевой JSON для ветки PRINT': '## PRINT 分支的 target JSON',
  },
};

function localizeMarkdown(markdown: string, language: 'en' | 'zh') {
  const headings = localizedMarkdownHeadings[language];
  return markdown.split('\n').map((line) => headings[line] ?? line).join('\n');
}

function translateSeeds(language: 'en' | 'zh'): PackageSeed[] {
  const prefix = language === 'en'
    ? 'Translation in progress. This page follows the Russian original and will be expanded with implementation-specific screenshots.'
    : '翻译正在进行中。本页保留与俄文原版相同的结构，后续会补充完整截图和本地化说明。';
  const titleMap: Record<string, string> = language === 'en' ? {
    'Быстрый старт': 'Quick Start', 'Основа продукта': 'Product basics', 'Что такое OMH': 'What is OMH', 'Основные понятия': 'Core concepts', 'Как выбрать сценарий интеграции': 'Choose an integration scenario', 'Готовность паттернов': 'Pattern readiness', 'Почему wizard, а не workflow': 'Why wizard, not workflow', 'Обзор 1C': '1C Overview', 'Обзор 1C Package': '1C Package overview', 'Настройка 1C': '1C Setup', '1C Connector Setup': '1C Connector Setup', 'Secrets и static token': 'Secrets and static token', 'Инструменты 1C': '1C Tools', '1C Connector': '1C Connector', 'OData Master': 'OData Master', 'XML Tools': 'XML Tools', '1C Cockpit': '1C Cockpit', 'Visual Flow Builder для 1C': 'Visual Flow Builder for 1C', 'Практические сценарии 1C': 'Practical 1C scenarios', '1C -> внешний API / сайт': '1C -> External API / site', '1C POST -> две OData выборки -> JSON -> endpoint': '1C POST -> two OData lookups -> JSON -> endpoint', '1C XML -> OMH -> 1C raw forwarding': '1C XML -> OMH -> 1C raw forwarding', '1C XML + INN lookup': '1C XML + INN lookup', '1C -> принтер': '1C -> Printer', 'Website/API -> 1C': 'Website/API -> 1C', '1C OData polling -> target system': '1C OData polling -> target system', 'WMS/API -> OMH -> 1C': 'WMS/API -> OMH -> 1C', 'Ошибки, Timeline и очередь': 'Errors, Timeline and queue', 'Ошибки 1C, Timeline и Artifacts': '1C errors, Timeline and Artifacts', 'Queue, Retry и DLQ для 1C': 'Queue, Retry and DLQ for 1C', 'Примеры 1C': '1C Examples', '1C → внешний API': '1C -> External API', 'Сайт/API → 1C': 'Website/API -> 1C', '1C XML → 1C': '1C XML -> 1C', '1C → принтер': '1C -> Printer', 'Ошибки и диагностика': 'Errors and diagnostics', 'Ошибки и Timeline': 'Errors and Timeline', 'Частые проблемы 1C': '1C Troubleshooting', 'Печать': 'Printing', 'Printer Overview': 'Printer Overview', 'ZPL печать': 'ZPL printing', 'Ошибки принтера': 'Printer troubleshooting', 'Авторизация': 'Auth', 'Включение авторизации': 'Enable Auth', 'Пользователи': 'Users', 'Recovery keys': 'Recovery keys', 'Secrets Store': 'Secrets Store', 'Что такое Secrets Store': 'What is Secrets Store', 'Использование secret в connector': 'Use secret in connector', 'Пакеты': 'Packages', 'Старт за 15 минут': 'Start in 15 minutes', 'Что вы настроите в учебном сценарии': 'What you will build', 'Глоссарий терминов для 1C': 'Glossary for 1C users', 'Глубокий курс OData': 'Deep OData course', 'Что такое OData в 1C и зачем оно OMH': 'What OData is in 1C and why OMH needs it', 'Создание нескольких OData-подключений': 'Create multiple OData connections', 'Как выбрать OData-подключение в интеграционном потоке': 'Select an OData connection in a flow', 'Как строить $filter': 'Build $filter', '$select, $top и $orderby': '$select, $top and $orderby', 'Как использовать результат OData дальше': 'Use OData results in later steps', 'Пустой результат OData: диагностика': 'Debug empty OData results', 'Артефакты OData в Timeline': 'OData artifacts in Timeline', 'Базовые понятия для пользователя 1C': 'Basic concepts for 1C users', 'Создаём OData-подключение к 1С': 'Create OData Connection', 'Проверяем OData-запрос в OData Master': 'Test OData in OData Master', 'Ищем контрагента по ИНН': 'Find Contractor by INN', 'Создаём входную точку для POST-запроса из 1С': 'Create inbound endpoint for 1C POST', 'Читаем значения из входящего запроса': 'Read values from incoming request', 'Первая выборка OData: контрагент по ИНН': 'First OData query: contractor by INN', 'Вторая выборка OData: товар по артикулу': 'Second OData query: product by article', 'Собираем целевой JSON': 'Build target JSON', 'Отправляем JSON во внешний API': 'Send to external API', 'Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint': 'Configure the full exchange: 1C POST → two OData lookups → JSON → endpoint', 'Проверяем весь интеграционный поток': 'Test full flow'
  } : {
    'Быстрый старт': '快速开始', 'Основа продукта': '产品基础', 'Что такое OMH': '什么是 OMH', 'Основные понятия': '核心概念', 'Как выбрать сценарий интеграции': '选择集成场景', 'Готовность паттернов': '模式就绪度', 'Почему wizard, а не workflow': '为什么使用向导而不是工作流', 'Обзор 1C': '1C 概览', 'Обзор 1C Package': '1C 软件包概览', 'Настройка 1C': '1C 设置', '1C Connector Setup': '1C 连接器设置', 'Secrets и static token': '密钥和静态令牌', 'Инструменты 1C': '1C 工具', '1C Connector': '1C 连接器', 'OData Master': 'OData Master', 'XML Tools': 'XML 工具', '1C Cockpit': '1C 驾驶舱', 'Visual Flow Builder для 1C': '1C 可视化流程构建器', 'Практические сценарии 1C': '1C 实战场景', '1C -> внешний API / сайт': '1C -> 外部 API / 网站', '1C POST -> две OData выборки -> JSON -> endpoint': '1C POST -> 两次 OData 查询 -> JSON -> 端点', '1C XML -> OMH -> 1C raw forwarding': '1C XML -> OMH -> 1C 原样转发', '1C XML + INN lookup': '1C XML + INN 查询', '1C -> принтер': '1C -> 打印机', 'Website/API -> 1C': '网站/API -> 1C', '1C OData polling -> target system': '1C OData 轮询 -> 目标系统', 'WMS/API -> OMH -> 1C': 'WMS/API -> OMH -> 1C', 'Ошибки, Timeline и очередь': '错误、时间线和队列', 'Ошибки 1C, Timeline и Artifacts': '1C 错误、时间线和工件', 'Queue, Retry и DLQ для 1C': '1C 队列、重试和 DLQ', 'Примеры 1C': '1C 示例', '1C → внешний API': '1C → 外部 API', 'Сайт/API → 1C': '网站/API → 1C', '1C XML → 1C': '1C XML → 1C', '1C → принтер': '1C → 打印机', 'Ошибки и диагностика': '错误与诊断', 'Ошибки и Timeline': '错误与时间线', 'Частые проблемы 1C': '1C 常见问题', 'Печать': '打印', 'Printer Overview': '打印概览', 'ZPL печать': 'ZPL 打印', 'Ошибки принтера': '打印机错误', 'Авторизация': '认证', 'Включение авторизации': '启用认证', 'Пользователи': '用户', 'Recovery keys': '恢复密钥', 'Secrets Store': '密钥库', 'Что такое Secrets Store': '什么是密钥库', 'Использование secret в connector': '在连接器中使用密钥', 'Пакеты': '软件包', 'Старт за 15 минут': '15 分钟开始', 'Что вы настроите в учебном сценарии': '你将构建什么', 'Глоссарий терминов для 1C': '1C 用户术语表', 'Глубокий курс OData': 'OData 深度课程', 'Что такое OData в 1C и зачем оно OMH': '1C 中的 OData 以及 OMH 为什么需要它', 'Создание нескольких OData-подключений': '创建多个 OData 连接', 'Как выбрать OData-подключение в интеграционном потоке': '在流程中选择 OData 连接', 'Как строить $filter': '构建 $filter', '$select, $top и $orderby': '$select、$top 和 $orderby', 'Как использовать результат OData дальше': '在后续步骤中使用 OData 结果', 'Пустой результат OData: диагностика': '调试空 OData 结果', 'Артефакты OData в Timeline': 'Timeline 中的 OData 工件', 'Базовые понятия для пользователя 1C': '面向 1C 用户的基础概念', 'Создаём OData-подключение к 1С': '创建 OData Connection', 'Проверяем OData-запрос в OData Master': '在 OData Master 中测试 OData', 'Ищем контрагента по ИНН': '按 INN 查找客户', 'Создаём входную точку для POST-запроса из 1С': '为 1C POST 创建入站 endpoint', 'Читаем значения из входящего запроса': '从入站请求读取值', 'Первая выборка OData: контрагент по ИНН': '第一个 OData 查询：按 INN 查找客户', 'Вторая выборка OData: товар по артикулу': '第二个 OData 查询：按货号查找商品', 'Собираем целевой JSON': '组装 target JSON', 'Отправляем JSON во внешний API': '发送到外部 API', 'Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint': '配置完整交换：1C POST → 两次 OData 查询 → JSON → endpoint', 'Проверяем весь интеграционный поток': '测试完整 flow'
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
        markdown: `# ${titleMap[page.title] ?? page.title}\n\n> ${prefix}\n\n${localizeMarkdown(page.markdown.replace(/^# .+\n\n/, ''), language)}`,
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
