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
  },
};

export function DocumentationPage() {
  const { language, setLanguage } = useI18n();
  const bundle = getDocsBundle(language);
  const texts = copy[language];
  const location = useLocation();
  const params = useParams();
  const isSearch = location.pathname === '/docs/search';
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
