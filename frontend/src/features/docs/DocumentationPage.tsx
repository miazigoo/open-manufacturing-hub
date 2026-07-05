import { Link, useLocation, useParams } from 'react-router-dom';
import { DocsSearch } from './DocsSearch';
import { DocsSidebar } from './DocsSidebar';
import { DocsToc } from './DocsToc';
import { LanguageSwitcher } from './LanguageSwitcher';
import { DocsPrintButton } from './DocsPrintButton';
import { findDocPage, getDocsBundle, pagePath } from './content';
import { extractToc, MarkdownRenderer } from './MarkdownRenderer';
import { useI18n } from '../../i18n/useI18n';

const copy = {
  ru: {
    eyebrow: 'Документация в продукте',
    title: 'Документация, которая помогает внедрять, а не угадывать.',
    subtitle: 'Пакетные инструкции, 1C OData/XML маршруты, печать, авторизация, секреты и troubleshooting живут внутри продукта и переключаются вместе с языком UI.',
    open: 'Открыть текущий раздел',
    pdf: 'Печать / PDF',
    updated: 'Обновлено 2026-07-04',
    packages: 'пакетов',
    languages: 'языка',
    planned: 'запланирован',
    translation: 'Перевод страницы ещё дорабатывается. Структура стабильна и соответствует русскому оригиналу.',
    startTitle: 'Если вы здесь впервые, начните с понятного маршрута',
    startSubtitle: 'Не нужно читать все подряд. Выберите задачу, повторите пример в Test Console, затем откройте Timeline и проверьте результат.',
    paths: [
      { label: 'Первый обмен с 1C', detail: 'Что установить, где создать OData profile, как собрать flow и куда смотреть после теста.', to: '/docs/onec/start-here/beginner-path', action: 'Открыть маршрут' },
      { label: 'Готовые запросы', detail: 'HTTP, 1C-код, payload, OData filter и ожидаемый ответ для типовых сценариев.', to: '/docs/onec/request-examples/request-03-two-lookups-order', action: 'Посмотреть пример' },
      { label: 'Ошибка в production', detail: 'Понятные playbooks: симптом, где смотреть artifact, как исправить и когда делать replay.', to: '/docs/onec/error-playbooks/odata-empty-required', action: 'Разобрать ошибку' },
    ],
  },
  en: {
    eyebrow: 'In-app documentation',
    title: 'Documentation built for implementation work.',
    subtitle: 'Package guides, 1C OData/XML routes, printing, auth, secrets and troubleshooting live inside the product.',
    open: 'Open current guide',
    pdf: 'Print / PDF',
    updated: 'Updated 2026-07-04',
    packages: 'packages',
    languages: 'languages',
    planned: 'planned',
    translation: 'Translation is in progress. The structure is stable and follows the Russian source page.',
    startTitle: 'First time here? Start with a guided path',
    startSubtitle: 'Do not read everything in order. Pick the job, run the example in Test Console, then inspect Timeline.',
    paths: [
      { label: 'First 1C exchange', detail: 'Install package, create OData profile, build a flow and verify the event.', to: '/docs/onec/start-here/beginner-path', action: 'Open path' },
      { label: 'Ready requests', detail: 'HTTP, 1C code, payload, OData filter and expected response for common scenarios.', to: '/docs/onec/request-examples/request-03-two-lookups-order', action: 'View example' },
      { label: 'Production error', detail: 'Symptom, artifact, fix and replay guidance in practical playbooks.', to: '/docs/onec/error-playbooks/odata-empty-required', action: 'Open playbook' },
    ],
  },
  zh: {
    eyebrow: '应用内文档',
    title: '面向实施工作的产品文档。',
    subtitle: '软件包指南、1C OData/XML 路由、打印、认证、密钥与故障排查都在产品内部。',
    open: '打开当前指南',
    pdf: '打印 / PDF',
    updated: '更新于 2026-07-04',
    packages: '软件包',
    languages: '语言',
    planned: '计划中',
    translation: '翻译正在完善中。页面结构稳定，并与俄文原版保持一致。',
    startTitle: '第一次使用？从引导路径开始',
    startSubtitle: '无需按顺序阅读所有内容。选择任务，在 Test Console 运行示例，然后检查 Timeline。',
    paths: [
      { label: '第一个 1C 交换', detail: '安装包、创建 OData 配置、构建 flow 并验证事件。', to: '/docs/onec/start-here/beginner-path', action: '打开路径' },
      { label: '现成请求', detail: '常见场景的 HTTP、1C 代码、payload、OData filter 和预期响应。', to: '/docs/onec/request-examples/request-03-two-lookups-order', action: '查看示例' },
      { label: '生产错误', detail: '通过 playbook 查看症状、artifact、修复和 replay。', to: '/docs/onec/error-playbooks/odata-empty-required', action: '打开 playbook' },
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
          <DocsSearch bundle={bundle} compact={!isSearch} />
          {isSearch ? (
            <DocsSearch bundle={bundle} />
          ) : (
            <>
              {isLanding && (
                <section className="docs-start-panel">
                  <div>
                    <span className="eyebrow">Start here</span>
                    <h2>{texts.startTitle}</h2>
                    <p>{texts.startSubtitle}</p>
                  </div>
                  <div className="docs-start-grid">
                    {texts.paths.map((item) => (
                      <Link key={item.to} className="docs-start-card" to={item.to}>
                        <strong>{item.label}</strong>
                        <span>{item.detail}</span>
                        <em>{item.action}</em>
                      </Link>
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
              <MarkdownRenderer markdown={page.markdown} />
            </>
          )}
        </main>
        {!isSearch && <DocsToc items={toc} />}
      </div>
    </div>
  );
}
