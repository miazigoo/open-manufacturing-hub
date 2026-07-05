import { useMemo, useState } from 'react';
import { asJson } from '../api/client';
import { useT } from '../i18n/useI18n';
import { CodeBlock } from './CodeBlock';

interface JsonBlockProps {
  value: unknown;
  title?: string;
  searchable?: boolean;
}

export function JsonBlock({ value, title, searchable = true }: JsonBlockProps) {
  const t = useT();
  const [raw, setRaw] = useState(false);
  const [query, setQuery] = useState('');
  const pretty = useMemo(() => asJson(value), [value]);
  const display = raw ? JSON.stringify(value) : pretty;
  const filtered = query ? display.split('\n').filter((line) => line.toLowerCase().includes(query.toLowerCase())).join('\n') : display;

  async function copy() {
    await navigator.clipboard?.writeText(display);
  }

  return (
    <section className="json-panel">
      <div className="panel-toolbar">
        <div>
          {title && <h3>{title}</h3>}
          <span className="microcopy">{t('common.chars', { count: display.length.toLocaleString() })}</span>
        </div>
        <div className="toolbar-actions">
          {searchable && <input className="micro-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('common.searchJson')} />}
          <button className="ghost-button" onClick={() => setRaw((current) => !current)}>{raw ? t('common.pretty') : t('common.raw')}</button>
          <button className="ghost-button" onClick={copy}>{t('common.copy')}</button>
        </div>
      </div>
      <CodeBlock code={filtered} language="json" copyLabel={t('common.copy')} copiedLabel={t('common.copied')} failedLabel={t('docs.copyUnavailable')} showToolbar={false} />
    </section>
  );
}
