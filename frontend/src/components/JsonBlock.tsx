import { useMemo, useState } from 'react';
import { asJson } from '../api/client';

interface JsonBlockProps {
  value: unknown;
  title?: string;
  searchable?: boolean;
}

export function JsonBlock({ value, title, searchable = true }: JsonBlockProps) {
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
          <span className="microcopy">{display.length.toLocaleString()} chars</span>
        </div>
        <div className="toolbar-actions">
          {searchable && <input className="micro-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search JSON" />}
          <button className="ghost-button" onClick={() => setRaw((current) => !current)}>{raw ? 'Pretty' : 'Raw'}</button>
          <button className="ghost-button" onClick={copy}>Copy</button>
        </div>
      </div>
      <pre className="json-block">{filtered}</pre>
    </section>
  );
}
