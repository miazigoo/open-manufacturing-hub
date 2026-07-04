import { useI18n } from '../../i18n/useI18n';
import type { TocItem } from './types';

const labels = {
  ru: { title: 'На этой странице', empty: 'Нет разделов' },
  en: { title: 'On this page', empty: 'No sections' },
  zh: { title: '本页内容', empty: '无章节' },
};

export function DocsToc({ items }: { items: TocItem[] }) {
  const { language } = useI18n();
  const copy = labels[language];
  return (
    <aside className="docs-toc-panel">
      <span className="eyebrow">{copy.title}</span>
      {items.length ? <nav>{items.map((item) => <a key={item.id} className={`toc-level-${item.level}`} href={`#${item.id}`}>{item.text}</a>)}</nav> : <span className="microcopy">{copy.empty}</span>}
    </aside>
  );
}
