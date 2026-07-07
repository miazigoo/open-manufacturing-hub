import type { ForeachODataStepTestResponse } from '../types';

interface ForeachTestPanelProps {
  result?: ForeachODataStepTestResponse;
  error?: string | null;
  loading: boolean;
  onTest: () => void;
}

export function ForeachTestPanel({ result, error, loading, onTest }: ForeachTestPanelProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Test</span><h3>Выполнить foreach OData</h3><p className="microcopy">Test выполняет OData-запросы только в рамках test_limit и safety limits.</p></div><button type="button" className="primary-button" disabled={loading} onClick={onTest}>{loading ? 'Тестирую...' : 'Test foreach'}</button></div>
      {error ? <div className="error-state compact"><strong>Test failed</strong><span>{error}</span></div> : null}
      {result ? <div className={`status-card ${result.success ? 'success' : 'danger'}`}><strong>{result.success ? 'Foreach test passed' : result.error_code ?? 'Foreach test failed'}</strong><span>{result.message}</span>{result.hint ? <small>{result.hint}</small> : null}</div> : null}
      {result ? <div className="metadata-grid compact-grid no-margin">
        <span><small>source_count</small><strong>{result.source_count}</strong></span>
        <span><small>items_processed</small><strong>{result.items_processed}</strong></span>
        <span><small>OData requests</small><strong>{result.odata_requests}</strong></span>
        <span><small>rows_found</small><strong>{result.rows_found}</strong></span>
      </div> : null}
      {result?.result_preview !== undefined ? <pre className="code-block"><code>{JSON.stringify(result.result_preview, null, 2)}</code></pre> : null}
      {result?.requests.length ? <details><summary>Показать OData requests</summary><pre className="code-block"><code>{JSON.stringify(result.requests, null, 2)}</code></pre></details> : null}
    </section>
  );
}
