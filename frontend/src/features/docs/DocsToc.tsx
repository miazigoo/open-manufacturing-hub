import { useT } from '../../i18n/useI18n';
import type { TocItem } from './types';

export function DocsToc({ items }: { items: TocItem[] }) {
  const t = useT();
  return (
    <aside className="docs-toc-panel">
      <span className="eyebrow">{t('docs.onThisPage')}</span>
      {items.length ? <nav>{items.map((item) => <a key={item.id} className={`toc-level-${item.level}`} href={`#${item.id}`}>{item.text}</a>)}</nav> : <span className="microcopy">{t('docs.noSections')}</span>}
    </aside>
  );
}
