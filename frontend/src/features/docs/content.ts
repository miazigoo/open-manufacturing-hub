import type { Language } from '../../i18n/dictionary';
import type { DocsLanguageBundle, DocsPackageId, DocsPageRecord, DocsPackageRecord } from './types';
import { onecPackageSeed } from './onecContent';

const updatedAt = '2026-07-04';

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
  onecPackageSeed,
  {
    id: 'reference', title: 'Reference', description: 'API и runtime contracts для интеграций.', order: 25, accent: 'green',
    sections: [
      { id: 'integration-master', title: 'Integration Master', description: 'Scenario chooser и Input Contract первого шага.', order: 5, pages: [
      { packageId: 'reference', sectionId: 'integration-master', slug: 'overview', title: 'Reference: Integration Master', description: 'Scenario chooser, input parser, endpoint slug и draft Input Contract.', order: 5, markdown: `# Reference: Integration Master

\`/master\` — первый шаг общего мастера интеграции. Он отвечает на вопрос: кто вызывает OMH и что придет во входящем запросе.

Step 1 сохраняет \`InputContract\`. Step 2A добавляет один OData Query, Step 2B читает табличную часть, Step 2C повторяет OData по массиву. Response builder и final action остаются следующими шагами мастера.

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
$top: 500
paginate: true
merge: flatten
save_as: codes
\`\`\`

Будущие переменные:

\`\`\`text
codes[]
codes[0].КодМаркировки
codes[0].Номенклатура_Key
\`\`\`

Validation проверяет source array, \`$top <= 500\`, collision \`save_as\` и safety limits: \`max_items\`, \`max_requests\`, \`max_result_rows\`.

## Parser rules

- JSON paths look like \`request.body.operation\`.
- Arrays expose \`request.body.items[]\` and first item paths such as \`request.body.items[0].sku\`.
- XML paths look like \`xml./Документ/Номер\`, with display path \`/Документ/Номер\`.
- Raw text exposes \`request.raw_text\` and simple \`key=value\` fields when possible.
- Sample size limit is 256 KB.

## Slug rule

Endpoint slug allows only lowercase letters, numbers, \`-\` and \`_\`, and must start and end with a letter or number.` },
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
    'Быстрый старт': 'Quick Start', 'Основа продукта': 'Product basics', 'Что такое OMH': 'What is OMH', 'Основные понятия': 'Core concepts', 'Обзор 1C': '1C Overview', 'Обзор 1C Package': '1C Package overview', 'Настройка 1C': '1C Setup', '1C Connector Setup': '1C Connector Setup', 'Secrets и static token': 'Secrets and static token', 'Инструменты 1C': '1C Tools', '1C Connector': '1C Connector', 'OData Master': 'OData Master', 'XML Tools': 'XML Tools', '1C Cockpit': '1C Cockpit', 'Visual Flow Builder для 1C': 'Visual Flow Builder for 1C', 'Практические сценарии 1C': 'Practical 1C scenarios', '1C -> внешний API / сайт': '1C -> External API / site', '1C POST -> две OData выборки -> JSON -> endpoint': '1C POST -> two OData lookups -> JSON -> endpoint', '1C XML -> OMH -> 1C raw forwarding': '1C XML -> OMH -> 1C raw forwarding', '1C XML + INN lookup': '1C XML + INN lookup', '1C -> принтер': '1C -> Printer', 'Website/API -> 1C': 'Website/API -> 1C', '1C OData polling -> target system': '1C OData polling -> target system', 'WMS/API -> OMH -> 1C': 'WMS/API -> OMH -> 1C', 'Ошибки, Timeline и очередь': 'Errors, Timeline and queue', 'Ошибки 1C, Timeline и Artifacts': '1C errors, Timeline and Artifacts', 'Queue, Retry и DLQ для 1C': 'Queue, Retry and DLQ for 1C', 'Примеры 1C': '1C Examples', '1C → внешний API': '1C -> External API', 'Сайт/API → 1C': 'Website/API -> 1C', '1C XML → 1C': '1C XML -> 1C', '1C → принтер': '1C -> Printer', 'Ошибки и диагностика': 'Errors and diagnostics', 'Ошибки и Timeline': 'Errors and Timeline', 'Частые проблемы 1C': '1C Troubleshooting', 'Печать': 'Printing', 'Printer Overview': 'Printer Overview', 'ZPL печать': 'ZPL printing', 'Ошибки принтера': 'Printer troubleshooting', 'Авторизация': 'Auth', 'Включение авторизации': 'Enable Auth', 'Пользователи': 'Users', 'Recovery keys': 'Recovery keys', 'Secrets Store': 'Secrets Store', 'Что такое Secrets Store': 'What is Secrets Store', 'Использование secret в connector': 'Use secret in connector', 'Пакеты': 'Packages', 'Старт за 15 минут': 'Start in 15 minutes', 'Что вы настроите в учебном сценарии': 'What you will build', 'Глоссарий терминов для 1C': 'Glossary for 1C users', 'Глубокий курс OData': 'Deep OData course', 'Что такое OData в 1C и зачем оно OMH': 'What OData is in 1C and why OMH needs it', 'Создание нескольких OData-подключений': 'Create multiple OData connections', 'Как выбрать OData-подключение в интеграционном потоке': 'Select an OData connection in a flow', 'Как строить $filter': 'Build $filter', '$select, $top и $orderby': '$select, $top and $orderby', 'Как использовать результат OData дальше': 'Use OData results in later steps', 'Пустой результат OData: диагностика': 'Debug empty OData results', 'Артефакты OData в Timeline': 'OData artifacts in Timeline', 'Базовые понятия для пользователя 1C': 'Basic concepts for 1C users', 'Создаём OData-подключение к 1С': 'Create OData Connection', 'Проверяем OData-запрос в OData Master': 'Test OData in OData Master', 'Ищем контрагента по ИНН': 'Find Contractor by INN', 'Создаём входную точку для POST-запроса из 1С': 'Create inbound endpoint for 1C POST', 'Читаем значения из входящего запроса': 'Read values from incoming request', 'Первая выборка OData: контрагент по ИНН': 'First OData query: contractor by INN', 'Вторая выборка OData: товар по артикулу': 'Second OData query: product by article', 'Собираем целевой JSON': 'Build target JSON', 'Отправляем JSON во внешний API': 'Send to external API', 'Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint': 'Configure the full exchange: 1C POST → two OData lookups → JSON → endpoint', 'Проверяем весь интеграционный поток': 'Test full flow'
  } : {
    'Быстрый старт': '快速开始', 'Основа продукта': '产品基础', 'Что такое OMH': '什么是 OMH', 'Основные понятия': '核心概念', 'Обзор 1C': '1C 概览', 'Обзор 1C Package': '1C 软件包概览', 'Настройка 1C': '1C 设置', '1C Connector Setup': '1C 连接器设置', 'Secrets и static token': '密钥和静态令牌', 'Инструменты 1C': '1C 工具', '1C Connector': '1C 连接器', 'OData Master': 'OData Master', 'XML Tools': 'XML 工具', '1C Cockpit': '1C 驾驶舱', 'Visual Flow Builder для 1C': '1C 可视化流程构建器', 'Практические сценарии 1C': '1C 实战场景', '1C -> внешний API / сайт': '1C -> 外部 API / 网站', '1C POST -> две OData выборки -> JSON -> endpoint': '1C POST -> 两次 OData 查询 -> JSON -> 端点', '1C XML -> OMH -> 1C raw forwarding': '1C XML -> OMH -> 1C 原样转发', '1C XML + INN lookup': '1C XML + INN 查询', '1C -> принтер': '1C -> 打印机', 'Website/API -> 1C': '网站/API -> 1C', '1C OData polling -> target system': '1C OData 轮询 -> 目标系统', 'WMS/API -> OMH -> 1C': 'WMS/API -> OMH -> 1C', 'Ошибки, Timeline и очередь': '错误、时间线和队列', 'Ошибки 1C, Timeline и Artifacts': '1C 错误、时间线和工件', 'Queue, Retry и DLQ для 1C': '1C 队列、重试和 DLQ', 'Примеры 1C': '1C 示例', '1C → внешний API': '1C → 外部 API', 'Сайт/API → 1C': '网站/API → 1C', '1C XML → 1C': '1C XML → 1C', '1C → принтер': '1C → 打印机', 'Ошибки и диагностика': '错误与诊断', 'Ошибки и Timeline': '错误与时间线', 'Частые проблемы 1C': '1C 常见问题', 'Печать': '打印', 'Printer Overview': '打印概览', 'ZPL печать': 'ZPL 打印', 'Ошибки принтера': '打印机错误', 'Авторизация': '认证', 'Включение авторизации': '启用认证', 'Пользователи': '用户', 'Recovery keys': '恢复密钥', 'Secrets Store': '密钥库', 'Что такое Secrets Store': '什么是密钥库', 'Использование secret в connector': '在连接器中使用密钥', 'Пакеты': '软件包', 'Старт за 15 минут': '15 分钟开始', 'Что вы настроите в учебном сценарии': '你将构建什么', 'Глоссарий терминов для 1C': '1C 用户术语表', 'Глубокий курс OData': 'OData 深度课程', 'Что такое OData в 1C и зачем оно OMH': '1C 中的 OData 以及 OMH 为什么需要它', 'Создание нескольких OData-подключений': '创建多个 OData 连接', 'Как выбрать OData-подключение в интеграционном потоке': '在流程中选择 OData 连接', 'Как строить $filter': '构建 $filter', '$select, $top и $orderby': '$select、$top 和 $orderby', 'Как использовать результат OData дальше': '在后续步骤中使用 OData 结果', 'Пустой результат OData: диагностика': '调试空 OData 结果', 'Артефакты OData в Timeline': 'Timeline 中的 OData 工件', 'Базовые понятия для пользователя 1C': '面向 1C 用户的基础概念', 'Создаём OData-подключение к 1С': '创建 OData Connection', 'Проверяем OData-запрос в OData Master': '在 OData Master 中测试 OData', 'Ищем контрагента по ИНН': '按 INN 查找客户', 'Создаём входную точку для POST-запроса из 1С': '为 1C POST 创建入站 endpoint', 'Читаем значения из входящего запроса': '从入站请求读取值', 'Первая выборка OData: контрагент по ИНН': '第一个 OData 查询：按 INN 查找客户', 'Вторая выборка OData: товар по артикулу': '第二个 OData 查询：按货号查找商品', 'Собираем целевой JSON': '组装 target JSON', 'Отправляем JSON во внешний API': '发送到外部 API', 'Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint': '配置完整交换：1C POST → 两次 OData 查询 → JSON → endpoint', 'Проверяем весь интеграционный поток': '测试完整 flow'
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
