import type { FinalActionTestResponse } from '../types';

interface FinalActionTestPanelProps {
  result?: FinalActionTestResponse;
  error?: string | null;
  testing: boolean;
  onDryRun: () => void;
  onRealTest: () => void;
}

export function FinalActionTestPanel({ result, error, testing, onDryRun, onRealTest }: FinalActionTestPanelProps) {
  return (
    <section className="panel stack-form odata-test-panel final-action-test-panel">
      <div className="panel-toolbar"><div><span className="eyebrow">Test</span><h3>Проверить финальное действие</h3><p className="microcopy">Dry run не ходит в сеть. Real test отправит запрос на endpoint после подтверждения.</p></div></div>
      <div className="action-row wrap-actions">
        <button type="button" className="ghost-button" disabled={testing} onClick={onDryRun}>{testing ? 'Проверяю...' : 'Dry run'}</button>
        <button type="button" className="primary-button" disabled={testing} onClick={onRealTest}>{testing ? 'Отправляю...' : 'Real test endpoint'}</button>
      </div>
      {error ? <div className="error-state compact"><strong>Test failed</strong><span>{error}</span></div> : null}
      {result ? <div className={`status-card ${result.success ? 'success' : 'danger'}`}><strong>{result.success ? (result.dry_run ? 'Dry run OK' : 'Real test OK') : result.error_code ?? 'Test failed'}</strong><span>{result.message ?? (result.dry_run ? 'Network call was not executed.' : `Target status ${result.target_status ?? 'n/a'}`)}</span></div> : null}
      {result?.would_send ? <PreviewBlock title="Would send" value={result.would_send} /> : null}
      {result && result.would_return_to_caller !== undefined ? <PreviewBlock title="Would return to caller" value={result.would_return_to_caller} /> : null}
      {result && result.target_response !== undefined ? <PreviewBlock title={`Target response${result.target_status ? ` · ${result.target_status}` : ''}`} value={result.target_response} /> : null}
      {result && result.caller_response !== undefined ? <PreviewBlock title="Caller response" value={result.caller_response} /> : null}
    </section>
  );
}

function PreviewBlock({ title, value }: { title: string; value: unknown }) {
  return <div className="stack-form"><strong>{title}</strong><pre className="code-block"><code>{typeof value === 'string' ? value : JSON.stringify(value, null, 2)}</code></pre></div>;
}
