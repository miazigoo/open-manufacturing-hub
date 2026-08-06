import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { dataInboxApi } from '../../api/dataInbox';
import { CodeEditor } from '../../components/CodeEditor';

const EXAMPLES: Array<{ title: string; query: string }> = [
  { title: 'Последние события', query: "select event_type, status, count(*) as cnt from integration_events group by event_type, status order by cnt desc" },
  { title: 'Записи приемника', query: "select status, count(*) as cnt from inbox_records group by status" },
  { title: 'Экспорты пулов ЧЗ', query: "select order_number, status, total_codes, created_at from marking_code_pool_exports order by created_at desc" },
];

export function SqlConsolePage() {
  const [query, setQuery] = useState(EXAMPLES[0].query);
  const [limit, setLimit] = useState('200');
  const run = useMutation({ mutationFn: () => dataInboxApi.runSql(query, Number(limit) || 200) });
  const result = run.data;

  const exportCsv = () => {
    if (!result) return;
    const lines = [result.columns.join(';')];
    for (const row of result.rows) {
      lines.push(result.columns.map((column) => JSON.stringify(row[column] ?? '')).join(';'));
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'omh-sql-result.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-stack">
      <section className="page-header onec-hero">
        <span className="eyebrow">SQL-консоль (только чтение)</span>
        <h1>Запросы к базе данных OMH</h1>
        <p>Разрешены только SELECT-запросы. Записывать и менять данные здесь нельзя — для этого есть страницы управления.</p>
      </section>

      <section className="info-panel">
        <div className="hint-chip-row">
          {EXAMPLES.map((example) => (
            <button key={example.title} type="button" className="hint-chip" onClick={() => setQuery(example.query)} title={example.query}>{example.title}</button>
          ))}
        </div>
        <label className="field-label">SQL-запрос</label>
        <CodeEditor value={query} onChange={setQuery} language="sql" minRows={6} />
        <div className="action-row wrap-actions">
          <label className="field-label no-margin" style={{ maxWidth: 140 }}>Лимит строк<input value={limit} onChange={(event) => setLimit(event.target.value)} /></label>
          <button className="primary-button" onClick={() => run.mutate()} disabled={run.isPending || !query.trim()}>Выполнить</button>
          {result && <button className="ghost-button" onClick={exportCsv}>Экспорт CSV</button>}
        </div>
        {run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}
      </section>

      {result && (
        <section className="info-panel">
          <div className="section-title-row">
            <div><span className="eyebrow">Результат</span><h2>{result.row_count} строк{result.truncated ? ' (показан лимит)' : ''}</h2></div>
            <span className="microcopy">{result.elapsed_ms} мс</span>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
              <tbody>
                {result.rows.map((row, index) => (
                  <tr key={index}>{result.columns.map((column) => <td key={column}>{formatCell(row[column])}</td>)}</tr>
                ))}
                {!result.rows.length && <tr><td colSpan={result.columns.length || 1}>Пустой результат.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
