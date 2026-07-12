import { CodeBlock } from '../../../components/CodeBlock';
import type { PollODataSendTargetCreateResponse, PollODataSendTargetRunTestResponse } from './types';

interface ManualTestStepProps {
  result?: PollODataSendTargetRunTestResponse;
  createResult?: PollODataSendTargetCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  dryRun: boolean;
  updateCursor: boolean;
  onDryRunChange: (value: boolean) => void;
  onUpdateCursorChange: (value: boolean) => void;
  onRun: () => void;
}

export function ManualTestStep({ result, createResult, error, loading, disabled, dryRun, updateCursor, onDryRunChange, onUpdateCursorChange, onRun }: ManualTestStepProps) {
  const run = result?.run;
  return (
    <section className="wizard-step integration-master-step poll-manual-test-step">
      <span className="step-index">08</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Manual test run</span>
          <h2>Запустить тестовый polling</h2>
          <p>Dry Run читает OData и строит payload, но не отправляет target. Real send отправит target; cursor обновляется только если включить checkbox.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onRun}>{loading ? 'Запускаю...' : 'Запустить тестовый polling'}</button>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="check-row odata-check"><input type="checkbox" checked={dryRun} onChange={(event) => onDryRunChange(event.target.checked)} /> Dry Run</label>
        <label className="check-row odata-check"><input type="checkbox" checked={updateCursor} disabled={dryRun} onChange={(event) => onUpdateCursorChange(event.target.checked)} /> Обновить cursor после успешного теста</label>
        <span className="status-card neutral"><small>Mode</small><strong>{dryRun ? 'query + build only' : 'real send'}</strong><span>{createResult ? 'Тест будет запущен по сохранённому polling job.' : 'До сохранения backend создаст временный job и откатит его после run.'}</span></span>
      </div>
      {disabled ? <div className="status-card warning"><strong>Нужен valid preview</strong><span>Manual test доступен после успешного preview, чтобы не запускать некорректный target.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Manual test failed</strong><span>{error}</span></div> : null}
      {result ? <div className={`status-card ${result.success ? 'success' : 'danger'}`}><strong>{result.success ? 'Run success' : 'Run failed'}</strong><span>{String(run?.error_message ?? run?.status ?? '')}</span></div> : null}
      {run ? (
        <div className="pattern-flow-preview-grid send-endpoint-preview-grid">
          <PreviewCard title="Run summary" value={{ status: run.status, items_read: run.items_read, sent_count: run.sent_count, started_at: run.started_at, finished_at: run.finished_at }} />
          <PreviewCard title="Cursor before" value={run.cursor_before_json} />
          <PreviewCard title="Cursor after" value={run.cursor_after_json} />
          <PreviewCard title="Run details" value={run.details_json} />
        </div>
      ) : null}
    </section>
  );
}

function PreviewCard({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">{title}</span><h3>{title}</h3></div></div>
      <CodeBlock code={JSON.stringify(value ?? null, null, 2)} language="json" showToolbar={false} />
    </section>
  );
}
