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
    'Быстрый старт': 'Quick Start', 'Основа продукта': 'Product basics', 'Что такое OMH': 'What is OMH', 'Основные понятия': 'Core concepts', 'Обзор 1C': '1C Overview', 'Обзор 1C Package': '1C Package overview', 'Настройка 1C': '1C Setup', '1C Connector Setup': '1C Connector Setup', 'Secrets и static token': 'Secrets and static token', 'Инструменты 1C': '1C Tools', '1C Connector': '1C Connector', 'OData Explorer': 'OData Explorer', 'XML Tools': 'XML Tools', '1C Cockpit': '1C Cockpit', 'Visual Flow Builder для 1C': 'Visual Flow Builder for 1C', 'Практические сценарии 1C': 'Practical 1C scenarios', '1C -> внешний API / сайт': '1C -> External API / site', '1C POST -> две OData выборки -> JSON -> endpoint': '1C POST -> two OData lookups -> JSON -> endpoint', '1C XML -> OMH -> 1C raw forwarding': '1C XML -> OMH -> 1C raw forwarding', '1C XML + INN lookup': '1C XML + INN lookup', '1C -> принтер': '1C -> Printer', 'Website/API -> 1C': 'Website/API -> 1C', '1C OData polling -> target system': '1C OData polling -> target system', 'WMS/API -> OMH -> 1C': 'WMS/API -> OMH -> 1C', 'Ошибки, Timeline и очередь': 'Errors, Timeline and queue', 'Ошибки 1C, Timeline и Artifacts': '1C errors, Timeline and Artifacts', 'Queue, Retry и DLQ для 1C': 'Queue, Retry and DLQ for 1C', 'Примеры 1C': '1C Examples', '1C → внешний API': '1C -> External API', 'Сайт/API → 1C': 'Website/API -> 1C', '1C XML → 1C': '1C XML -> 1C', '1C → принтер': '1C -> Printer', 'Ошибки и диагностика': 'Errors and diagnostics', 'Ошибки и Timeline': 'Errors and Timeline', 'Частые проблемы 1C': '1C Troubleshooting', 'Печать': 'Printing', 'Printer Overview': 'Printer Overview', 'ZPL печать': 'ZPL printing', 'Ошибки принтера': 'Printer troubleshooting', 'Авторизация': 'Auth', 'Включение авторизации': 'Enable Auth', 'Пользователи': 'Users', 'Recovery keys': 'Recovery keys', 'Secrets Store': 'Secrets Store', 'Что такое Secrets Store': 'What is Secrets Store', 'Использование secret в connector': 'Use secret in connector', 'Пакеты': 'Packages'
  } : {
    'Быстрый старт': '快速开始', 'Основа продукта': '产品基础', 'Что такое OMH': '什么是 OMH', 'Основные понятия': '核心概念', 'Обзор 1C': '1C 概览', 'Обзор 1C Package': '1C 软件包概览', 'Настройка 1C': '1C 设置', '1C Connector Setup': '1C 连接器设置', 'Secrets и static token': '密钥和静态令牌', 'Инструменты 1C': '1C 工具', '1C Connector': '1C 连接器', 'OData Explorer': 'OData 浏览器', 'XML Tools': 'XML 工具', '1C Cockpit': '1C 驾驶舱', 'Visual Flow Builder для 1C': '1C 可视化流程构建器', 'Практические сценарии 1C': '1C 实战场景', '1C -> внешний API / сайт': '1C -> 外部 API / 网站', '1C POST -> две OData выборки -> JSON -> endpoint': '1C POST -> 两次 OData 查询 -> JSON -> 端点', '1C XML -> OMH -> 1C raw forwarding': '1C XML -> OMH -> 1C 原样转发', '1C XML + INN lookup': '1C XML + INN 查询', '1C -> принтер': '1C -> 打印机', 'Website/API -> 1C': '网站/API -> 1C', '1C OData polling -> target system': '1C OData 轮询 -> 目标系统', 'WMS/API -> OMH -> 1C': 'WMS/API -> OMH -> 1C', 'Ошибки, Timeline и очередь': '错误、时间线和队列', 'Ошибки 1C, Timeline и Artifacts': '1C 错误、时间线和工件', 'Queue, Retry и DLQ для 1C': '1C 队列、重试和 DLQ', 'Примеры 1C': '1C 示例', '1C → внешний API': '1C → 外部 API', 'Сайт/API → 1C': '网站/API → 1C', '1C XML → 1C': '1C XML → 1C', '1C → принтер': '1C → 打印机', 'Ошибки и диагностика': '错误与诊断', 'Ошибки и Timeline': '错误与时间线', 'Частые проблемы 1C': '1C 常见问题', 'Печать': '打印', 'Printer Overview': '打印概览', 'ZPL печать': 'ZPL 打印', 'Ошибки принтера': '打印机错误', 'Авторизация': '认证', 'Включение авторизации': '启用认证', 'Пользователи': '用户', 'Recovery keys': '恢复密钥', 'Secrets Store': '密钥库', 'Что такое Secrets Store': '什么是密钥库', 'Использование secret в connector': '在连接器中使用密钥', 'Пакеты': '软件包'
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
