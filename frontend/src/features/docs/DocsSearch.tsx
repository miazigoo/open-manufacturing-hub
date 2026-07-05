import { FormEvent, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { flattenDocs, pagePath } from './content';
import type { DocsLanguageBundle } from './types';

const labels = {
  ru: { search: 'Поиск', title: 'Поиск по документации', results: 'Результаты', matches: 'совпадений', empty: 'По этому запросу ничего не найдено.', matched: 'matched term', language: 'language' },
  en: { search: 'Search', title: 'Search documentation', results: 'Results', matches: 'matches', empty: 'No documentation pages matched this query.', matched: 'matched term', language: 'language' },
  zh: { search: '搜索', title: '搜索文档', results: '搜索结果', matches: '条匹配', empty: '没有找到匹配的文档页面。', matched: '匹配词', language: '语言' },
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
              <span>{result.packageTitle} / {result.sectionTitle}</span>
              <strong>{result.page.title}</strong>
              <p>{result.snippet}</p>
              <div className="docs-result-meta">
                <small>{copy.language}: {bundle.language}</small>
                <small>{copy.matched}: <mark>{result.term}</mark></small>
                <small>{result.page.packageId}</small>
              </div>
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
  const sections = new Map(bundle.packages.flatMap((pkg) => pkg.sections.map((section) => [`${pkg.id}.${section.id}`, section.title])));
  return flattenDocs(bundle)
    .map((page) => {
      const source = `${page.title}\n${page.description}\n${page.markdown.replace(/[`#*_[\](){}|>-]/g, ' ')}`;
      const haystack = source.toLowerCase();
      const matchIndex = haystack.indexOf(needle);
      return {
        page,
        packageTitle: packages.get(page.packageId) ?? page.packageId,
        sectionTitle: sections.get(`${page.packageId}.${page.sectionId}`) ?? page.sectionId,
        snippet: buildSnippet(source, matchIndex, query.trim()),
        term: query.trim(),
        score: matchIndex >= 0 ? needle.length + (page.title.toLowerCase().includes(needle) ? 20 : 0) : 0,
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 12);
}

function buildSnippet(source: string, index: number, term: string) {
  if (index < 0) return source.replace(/\s+/g, ' ').trim().slice(0, 180);
  const start = Math.max(0, index - 70);
  const end = Math.min(source.length, index + term.length + 110);
  const snippet = source.slice(start, end).replace(/\s+/g, ' ').trim();
  return `${start > 0 ? '...' : ''}${snippet}${end < source.length ? '...' : ''}`;
}
