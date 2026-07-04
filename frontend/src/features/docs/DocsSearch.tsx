import { FormEvent, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { flattenDocs, pagePath } from './content';
import type { DocsLanguageBundle } from './types';

const labels = {
  ru: { search: 'Поиск', title: 'Поиск по документации', results: 'Результаты', matches: 'совпадений', empty: 'По этому запросу ничего не найдено.' },
  en: { search: 'Search', title: 'Search documentation', results: 'Results', matches: 'matches', empty: 'No documentation pages matched this query.' },
  zh: { search: '搜索', title: '搜索文档', results: '搜索结果', matches: '条匹配', empty: '没有找到匹配的文档页面。' },
};

export function DocsSearch({ bundle, compact = false }: { bundle: DocsLanguageBundle; compact?: boolean }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') ?? '';
  const [query, setQuery] = useState(initialQuery);
  const results = useMemo(() => searchDocs(bundle, initialQuery), [bundle, initialQuery]);
  const copy = labels[bundle.language];

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    navigate(trimmed ? `/docs/search?q=${encodeURIComponent(trimmed)}` : '/docs');
  }

  return (
    <section className={`docs-search-panel ${compact ? 'compact' : ''}`}>
      <form className="docs-search-form" onSubmit={submit}>
        <label>
          <span>{copy.title}</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="OData, XML, printer, auth..." />
        </label>
        <button className="primary-button" type="submit">{copy.search}</button>
      </form>
      {!compact && (
        <div className="docs-search-results">
          <div className="panel-toolbar compact-toolbar">
            <h2>{initialQuery ? `${copy.results}: "${initialQuery}"` : copy.search}</h2>
            <span className="microcopy">{results.length} {copy.matches}</span>
          </div>
          {initialQuery && results.length === 0 && <p>{copy.empty}</p>}
          {results.map((result) => (
            <Link key={result.page.id} to={pagePath(result.page)} className="docs-result-card">
              <span>{result.packageTitle}</span>
              <strong>{result.page.title}</strong>
              <p>{result.page.description}</p>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

function searchDocs(bundle: DocsLanguageBundle, query: string) {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  const packages = new Map(bundle.packages.map((pkg) => [pkg.id, pkg.title]));
  return flattenDocs(bundle)
    .map((page) => {
      const haystack = `${page.title} ${page.description} ${page.markdown}`.toLowerCase();
      return { page, packageTitle: packages.get(page.packageId) ?? page.packageId, score: haystack.includes(needle) ? needle.length : 0 };
    })
    .filter((item) => item.score > 0)
    .slice(0, 12);
}
