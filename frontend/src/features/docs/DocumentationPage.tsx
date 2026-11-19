import { Link, useLocation, useParams } from 'react-router-dom';
import { DocsSearch } from './DocsSearch';
import { DocsSidebar } from './DocsSidebar';
import { DocsToc } from './DocsToc';
import { LanguageSwitcher } from './LanguageSwitcher';
import { DocsPrintButton } from './DocsPrintButton';
import { DocsActionBar } from './DocsActionBar';
import { DocsLessonNavigation } from './DocsLessonNavigation';
import { findDocPage, getDocsBundle, pagePath } from './content';
import { extractToc, MarkdownRenderer } from './MarkdownRenderer';
import { useI18n } from '../../i18n/useI18n';

const copy = {
  ru: {
    eyebrow: 'Документация в продукте',
    title: 'Документация OMH',
    subtitle: 'Научитесь настраивать интеграции между 1С, WMS, сайтами, API, XML, принтерами и файловыми обменами.',
    open: 'Открыть текущий раздел',
    pdf: 'Печать / PDF',
    updated: 'Обновлено 2026-07-13',
    packages: 'пакетов',
    languages: 'языка',
    planned: 'запланирован',
    translation: 'Перевод страницы ещё дорабатывается. Структура стабильна и соответствует русскому оригиналу.',
    startEyebrow: 'Учебная карта продукта',
    startTitle: 'Полный путь настройки интеграции в OMH',
    startSubtitle: 'Начните с понятного маршрута: Integration Start -> Connection Center -> Operation Catalog -> Data Contracts -> Mapping Center -> Pattern Wizards -> Test/Timeline/Troubleshooting -> Enable integration.',
    blocks: [
      { title: 'Быстрый старт', items: [
        { label: 'Что такое OMH', detail: 'Простая схема продукта и роль Timeline/artifacts.', to: '/docs/core/learning-path/what-is-omh', action: 'Открыть' },
        { label: 'Как выбрать сценарий интеграции', detail: 'Integration Start examples и правила выбора wizard.', to: '/docs/core/learning-path/choose-scenario', action: 'Выбрать' },
        { label: 'Первая интеграция за 15 минут', detail: 'Минимальный путь от sample до Timeline.', to: '/docs/onec/start-here/beginner-path', action: 'Начать' },
        { label: 'Training Sandbox', detail: 'Учебные примеры без реальной 1С, WMS и принтера.', to: '/docs/onec/academy/training-sandbox-executable-docs', action: 'Учиться' },
      ] },
      { title: 'Основные понятия', items: [
        { label: 'Scenario / Pattern', detail: 'Бизнес-сценарий и технический шаблон.', to: '/docs/core/concepts', action: 'Понятия' },
        { label: 'Connection', detail: 'Куда OMH может подключаться.', to: '/docs/core/connection-center', action: 'Профили' },
        { label: 'Operation', detail: 'Что OMH делает внутри подключения.', to: '/docs/core/operation-catalog', action: 'Операции' },
        { label: 'Data Contract', detail: 'Какие поля и типы ожидает операция.', to: '/docs/core/data-contracts-and-mappings', action: 'Контракты' },
        { label: 'Mapping', detail: 'Как переложить поля без потери типов.', to: '/docs/core/data-contracts-and-mappings', action: 'Mapping' },
        { label: 'Wizard', detail: 'Пошаговый мастер сценария.', to: '/docs/core/pattern-wizards', action: 'Wizards' },
        { label: 'Timeline', detail: 'История выполнения события.', to: '/docs/onec/troubleshooting/by-scenario', action: 'Диагностика' },
        { label: 'Artifact', detail: 'Сохранённый request/response шага.', to: '/docs/core/concepts', action: 'Artifacts' },
      ] },
      { title: 'Практические сценарии', items: [
        { label: 'Внешний сервис спрашивает данные из 1С', detail: 'Request -> OData -> Response.', to: '/docs/onec/recipes/external-service-lookup-contractor', action: 'Инструкция' },
        { label: '1С отправляет данные во внешний API', detail: 'Request -> OData -> Send Endpoint.', to: '/docs/onec/recipes/request-odata-send-endpoint', action: 'Инструкция' },
        { label: 'DnP запрашивает пул кодов ЧЗ', detail: 'Order -> products -> foreach codes -> DnP.', to: '/docs/onec/recipes/dnp-chz-code-pool-sync', action: 'Инструкция' },
        { label: '1С отправляет пул кодов ЧЗ в файл', detail: 'Local archive, SMB/laser, optional forward.', to: '/docs/onec/recipes/onec-sends-chz-code-pool-file', action: 'Инструкция' },
        { label: 'WMS отправляет складской факт в 1С', detail: 'Отгрузки, остатки, инвентаризация, перемещения.', to: '/docs/onec/recipes/wms-shipment-fact-to-onec', action: 'Инструкция' },
        { label: 'XML без изменений в другую 1С', detail: 'Raw XML forwarding with hash artifacts.', to: '/docs/onec/recipes/xml-raw-forwarding', action: 'Инструкция' },
        { label: 'XML -> OData -> XML ответ', detail: 'Extract XML, lookup 1C, render XML response.', to: '/docs/onec/recipes/xml-input-odata-xml-response', action: 'Инструкция' },
        { label: '1С отправляет этикетки на печать', detail: 'labels[] -> ZPL -> printer status.', to: '/docs/onec/recipes/onec-print-labels', action: 'Инструкция' },
        { label: 'OMH сам читает OData по расписанию', detail: 'Polling job, cursor, target send.', to: '/docs/onec/recipes/poll-odata-send-target', action: 'Инструкция' },
      ] },
      { title: 'Справочник', items: [
        { label: 'Connection Center', detail: 'Reusable profiles for 1C, API, printers and files.', to: '/docs/core/connection-center', action: 'Открыть' },
        { label: 'Operation Catalog', detail: 'Reusable operations, success conditions and extractors.', to: '/docs/core/operation-catalog', action: 'Открыть' },
        { label: 'Data Contracts', detail: 'Request/response schemas for operations.', to: '/docs/core/data-contracts-and-mappings', action: 'Открыть' },
        { label: 'Mapping Center', detail: 'Field mapping, dynamic keys and raw JSON fallback.', to: '/docs/core/data-contracts-and-mappings', action: 'Открыть' },
        { label: 'Pattern Wizards', detail: 'Common wizard steps, preview and disabled-by-default.', to: '/docs/core/pattern-wizards', action: 'Открыть' },
        { label: 'Training Sandbox', detail: 'Safe examples and mock systems.', to: '/docs/onec/academy/training-sandbox-executable-docs', action: 'Открыть' },
        { label: 'Production', detail: 'Readiness gate before enable.', to: '/docs/core/learning-path/setup-flow', action: 'Открыть' },
        { label: 'Troubleshooting', detail: 'Timeline-first playbooks by scenario.', to: '/docs/onec/troubleshooting/by-scenario', action: 'Открыть' },
      ] },
    ],
  },
  en: {
    eyebrow: 'In-app documentation',
    title: 'OMH Documentation',
    subtitle: 'Learn to configure integrations between 1C, WMS, websites, APIs, XML, printers and file exchanges.',
    open: 'Open current guide',
    pdf: 'Print / PDF',
    updated: 'Updated 2026-07-13',
    packages: 'packages',
    languages: 'languages',
    planned: 'planned',
    translation: 'Translation is in progress. The structure is stable and follows the Russian source page.',
    startEyebrow: 'Learning map',
    startTitle: 'Full OMH integration setup path',
    startSubtitle: 'Start with a guided path: scenario selection, connections, operations, contracts, mappings, wizards, tests, Timeline and enable.',
    blocks: [
      { title: 'Quick start', items: [
        { label: 'What is OMH', detail: 'Product map and core runtime concepts.', to: '/docs/core/learning-path/what-is-omh', action: 'Open' },
        { label: 'Choose a scenario', detail: 'Integration Start examples.', to: '/docs/core/learning-path/choose-scenario', action: 'Choose' },
        { label: 'First integration', detail: 'A short practical path.', to: '/docs/onec/start-here/beginner-path', action: 'Start' },
        { label: 'Training Sandbox', detail: 'Safe examples without real systems.', to: '/docs/onec/academy/training-sandbox-executable-docs', action: 'Learn' },
      ] },
      { title: 'Core concepts', items: [
        { label: 'Scenario / Pattern', detail: 'Business scenario and technical pattern.', to: '/docs/core/concepts', action: 'Open' },
        { label: 'Connection', detail: 'Where OMH connects.', to: '/docs/core/connection-center', action: 'Open' },
        { label: 'Operation', detail: 'What OMH does there.', to: '/docs/core/operation-catalog', action: 'Open' },
        { label: 'Data Contract', detail: 'Expected fields and types.', to: '/docs/core/data-contracts-and-mappings', action: 'Open' },
        { label: 'Mapping', detail: 'Field mapping without type loss.', to: '/docs/core/data-contracts-and-mappings', action: 'Open' },
        { label: 'Wizard', detail: 'Guided scenario setup.', to: '/docs/core/pattern-wizards', action: 'Open' },
        { label: 'Timeline', detail: 'Execution history.', to: '/docs/onec/troubleshooting/by-scenario', action: 'Open' },
        { label: 'Artifact', detail: 'Saved step payloads.', to: '/docs/core/concepts', action: 'Open' },
      ] },
      { title: 'Practical scenarios', items: [
        { label: 'External service asks 1C', detail: 'Request -> OData -> Response.', to: '/docs/onec/recipes/external-service-lookup-contractor', action: 'Guide' },
        { label: '1C sends to external API', detail: 'Request -> OData -> Send Endpoint.', to: '/docs/onec/recipes/request-odata-send-endpoint', action: 'Guide' },
        { label: 'DnP asks CHZ codes', detail: 'Foreach OData and DnP send.', to: '/docs/onec/recipes/dnp-chz-code-pool-sync', action: 'Guide' },
        { label: '1C sends CHZ file', detail: 'Archive, SMB and forward.', to: '/docs/onec/recipes/onec-sends-chz-code-pool-file', action: 'Guide' },
        { label: 'WMS warehouse facts', detail: 'Shipments, balances, inventory, movements.', to: '/docs/onec/recipes/wms-shipment-fact-to-onec', action: 'Guide' },
        { label: 'Raw XML forwarding', detail: 'No XML changes.', to: '/docs/onec/recipes/xml-raw-forwarding', action: 'Guide' },
        { label: 'XML -> OData -> XML', detail: 'Lookup and XML response.', to: '/docs/onec/recipes/xml-input-odata-xml-response', action: 'Guide' },
        { label: 'Print labels', detail: 'labels[] -> ZPL -> printer.', to: '/docs/onec/recipes/onec-print-labels', action: 'Guide' },
        { label: 'Poll OData', detail: 'Scheduler, cursor and target send.', to: '/docs/onec/recipes/poll-odata-send-target', action: 'Guide' },
      ] },
      { title: 'Reference', items: [
        { label: 'Connection Center', detail: 'Reusable profiles.', to: '/docs/core/connection-center', action: 'Open' },
        { label: 'Operation Catalog', detail: 'Reusable operations.', to: '/docs/core/operation-catalog', action: 'Open' },
        { label: 'Data Contracts', detail: 'Schemas.', to: '/docs/core/data-contracts-and-mappings', action: 'Open' },
        { label: 'Mapping Center', detail: 'Mappings.', to: '/docs/core/data-contracts-and-mappings', action: 'Open' },
        { label: 'Pattern Wizards', detail: 'Wizard rules.', to: '/docs/core/pattern-wizards', action: 'Open' },
        { label: 'Training Sandbox', detail: 'Safe examples.', to: '/docs/onec/academy/training-sandbox-executable-docs', action: 'Open' },
        { label: 'Production', detail: 'Enable gate.', to: '/docs/core/learning-path/setup-flow', action: 'Open' },
        { label: 'Troubleshooting', detail: 'Timeline-first playbooks.', to: '/docs/onec/troubleshooting/by-scenario', action: 'Open' },
      ] },
    ],
  },
  zh: {
    eyebrow: '应用内文档',
    title: 'OMH 文档',
    subtitle: '学习配置 1C、WMS、网站、API、XML、打印机和文件交换集成。',
    open: '打开当前指南',
    pdf: '打印 / PDF',
    updated: '更新于 2026-07-13',
    packages: '软件包',
    languages: '语言',
    planned: '计划中',
    translation: '翻译正在完善中。页面结构稳定，并与俄文原版保持一致。',
    startEyebrow: '学习地图',
    startTitle: 'OMH 集成配置完整路径',
    startSubtitle: '从场景选择到连接、操作、契约、映射、向导、测试、Timeline 和启用。',
    blocks: [
      { title: '快速开始', items: [
        { label: '什么是 OMH', detail: '产品地图和核心概念。', to: '/docs/core/learning-path/what-is-omh', action: '打开' },
        { label: '选择场景', detail: 'Integration Start 示例。', to: '/docs/core/learning-path/choose-scenario', action: '选择' },
        { label: '第一个集成', detail: '简短实践路径。', to: '/docs/onec/start-here/beginner-path', action: '开始' },
        { label: 'Training Sandbox', detail: '安全示例。', to: '/docs/onec/academy/training-sandbox-executable-docs', action: '学习' },
      ] },
      { title: '核心概念', items: [
        { label: 'Scenario / Pattern', detail: '业务场景和技术模式。', to: '/docs/core/concepts', action: '打开' },
        { label: 'Connection', detail: 'OMH 连接到哪里。', to: '/docs/core/connection-center', action: '打开' },
        { label: 'Operation', detail: 'OMH 执行动作。', to: '/docs/core/operation-catalog', action: '打开' },
        { label: 'Data Contract', detail: '字段和类型。', to: '/docs/core/data-contracts-and-mappings', action: '打开' },
        { label: 'Mapping', detail: '字段映射。', to: '/docs/core/data-contracts-and-mappings', action: '打开' },
        { label: 'Wizard', detail: '场景向导。', to: '/docs/core/pattern-wizards', action: '打开' },
        { label: 'Timeline', detail: '执行历史。', to: '/docs/onec/troubleshooting/by-scenario', action: '打开' },
        { label: 'Artifact', detail: '保存的步骤数据。', to: '/docs/core/concepts', action: '打开' },
      ] },
      { title: '实践场景', items: [
        { label: '外部服务查询 1C', detail: 'Request -> OData -> Response。', to: '/docs/onec/recipes/external-service-lookup-contractor', action: '指南' },
        { label: '1C 发送到外部 API', detail: 'Request -> OData -> Send Endpoint。', to: '/docs/onec/recipes/request-odata-send-endpoint', action: '指南' },
        { label: 'DnP 查询 CHZ 码', detail: 'Foreach OData。', to: '/docs/onec/recipes/dnp-chz-code-pool-sync', action: '指南' },
        { label: '1C 发送 CHZ 文件', detail: '文件、SMB、转发。', to: '/docs/onec/recipes/onec-sends-chz-code-pool-file', action: '指南' },
        { label: 'WMS 仓储事实', detail: '发货、库存、盘点、调拨。', to: '/docs/onec/recipes/wms-shipment-fact-to-onec', action: '指南' },
        { label: 'XML 原样转发', detail: '不修改 XML。', to: '/docs/onec/recipes/xml-raw-forwarding', action: '指南' },
        { label: 'XML -> OData -> XML', detail: '查询并返回 XML。', to: '/docs/onec/recipes/xml-input-odata-xml-response', action: '指南' },
        { label: '打印标签', detail: 'labels[] -> ZPL。', to: '/docs/onec/recipes/onec-print-labels', action: '指南' },
        { label: '轮询 OData', detail: '计划任务和 cursor。', to: '/docs/onec/recipes/poll-odata-send-target', action: '指南' },
      ] },
      { title: '参考', items: [
        { label: 'Connection Center', detail: '可复用连接。', to: '/docs/core/connection-center', action: '打开' },
        { label: 'Operation Catalog', detail: '可复用操作。', to: '/docs/core/operation-catalog', action: '打开' },
        { label: 'Data Contracts', detail: '数据契约。', to: '/docs/core/data-contracts-and-mappings', action: '打开' },
        { label: 'Mapping Center', detail: '字段映射。', to: '/docs/core/data-contracts-and-mappings', action: '打开' },
        { label: 'Pattern Wizards', detail: '向导规则。', to: '/docs/core/pattern-wizards', action: '打开' },
        { label: 'Training Sandbox', detail: '安全示例。', to: '/docs/onec/academy/training-sandbox-executable-docs', action: '打开' },
        { label: 'Production', detail: '启用前检查。', to: '/docs/core/learning-path/setup-flow', action: '打开' },
        { label: 'Troubleshooting', detail: 'Timeline 优先排错。', to: '/docs/onec/troubleshooting/by-scenario', action: '打开' },
      ] },
    ],
  },
};
export function DocumentationPage() {
  const { language, setLanguage } = useI18n();
  const bundle = getDocsBundle(language);
  const texts = copy[language];
  const location = useLocation();
  const params = useParams();
  const isSearch = location.pathname === '/docs/search';
  const isLanding = !isSearch && !params.packageId;
  const page = findDocPage(bundle, params.packageId, params.sectionId, params.pageId);
  const toc = extractToc(page.markdown);
  const practicalSections = new Set(['start-here', 'academy', 'exercises', 'odata-course', 'recipes', 'troubleshooting', 'readiness-checklist', 'tools', 'scenarios', 'request-examples', 'error-playbooks', 'setup', 'support']);
  const showActionBar = page.packageId === 'onec' && practicalSections.has(page.sectionId);
  const endpointUrl = extractEndpointUrl(page.markdown);
  const academyPages = bundle.packages.find((pkg) => pkg.id === 'onec')?.sections.find((section) => section.id === 'academy')?.pages ?? [];
  const academyIndex = academyPages.findIndex((item) => item.id === page.id);
  const academyNavigation = academyIndex >= 0 ? {
    index: academyIndex,
    total: academyPages.length,
    previous: academyPages[academyIndex - 1],
    next: academyPages[academyIndex + 1],
  } : null;

  return (
    <div className="docs-portal-page">
      <section className="hero-panel docs-hero product-page-header">
        <div>
          <span className="eyebrow">{texts.eyebrow}</span>
          <h1>{texts.title}</h1>
          <p>{texts.subtitle}</p>
          <div className="hero-meta">
            <Link className="primary-link" to={pagePath(page)}>{texts.open}</Link>
            <DocsPrintButton label={texts.pdf} />
            <span className="microcopy">{texts.updated}</span>
          </div>
        </div>
        <div className="docs-hero-card">
          <LanguageSwitcher value={language} onChange={setLanguage} />
          <div className="docs-hero-stats">
            <span><strong>{bundle.packages.length}</strong> {texts.packages}</span>
            <span><strong>3</strong> {texts.languages}</span>
            <span><strong>PDF</strong> {texts.planned}</span>
          </div>
        </div>
      </section>

      <div className="docs-layout-grid">
        <DocsSidebar bundle={bundle} />
        <main className="docs-main-panel">
          {!isSearch && <DocsSearch bundle={bundle} compact />}
          {isSearch ? (
            <DocsSearch bundle={bundle} />
          ) : (
            <>
              {isLanding && (
                <section className="docs-start-panel">
                  <div>
                    <span className="eyebrow">{texts.startEyebrow}</span>
                    <h2>{texts.startTitle}</h2>
                    <p>{texts.startSubtitle}</p>
                  </div>
                  <div className="docs-landing-blocks">
                    {texts.blocks.map((block) => (
                      <section className="docs-landing-block" key={block.title}>
                        <h3>{block.title}</h3>
                        <div className="docs-start-grid">
                          {block.items.map((item) => (
                            <Link key={`${block.title}:${item.label}:${item.to}`} className="docs-start-card" to={item.to}>
                              <strong>{item.label}</strong>
                              <span>{item.detail}</span>
                              <em>{item.action}</em>
                            </Link>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                </section>
              )}
              {page.translationStatus === 'in_progress' && <div className="docs-translation-note">{texts.translation}</div>}
              <div className="docs-page-header">
                <span className="eyebrow">{page.packageId} / {page.sectionId}</span>
                <h1>{page.title}</h1>
                <p>{page.description}</p>
              </div>
              {showActionBar && <DocsActionBar endpointUrl={endpointUrl} />}
              {academyNavigation && (
                <DocsLessonNavigation
                  current={page}
                  previous={academyNavigation.previous}
                  next={academyNavigation.next}
                  index={academyNavigation.index}
                  total={academyNavigation.total}
                />
              )}
              <MarkdownRenderer markdown={page.markdown} />
              {academyNavigation && (
                <DocsLessonNavigation
                  current={page}
                  previous={academyNavigation.previous}
                  next={academyNavigation.next}
                  index={academyNavigation.index}
                  total={academyNavigation.total}
                />
              )}
            </>
          )}
        </main>
        {!isSearch && <DocsToc items={toc} />}
      </div>
    </div>
  );
}

function extractEndpointUrl(markdown: string) {
  return markdown.match(/(?:https?:\/\/[^\s`"')]+)?\/api\/bus\/in\/[a-z0-9-]+/i)?.[0] ?? null;
}
