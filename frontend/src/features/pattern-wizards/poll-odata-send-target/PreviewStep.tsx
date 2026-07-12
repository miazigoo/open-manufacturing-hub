import { CodeBlock } from '../../../components/CodeBlock';
import type { PollODataSendTargetPreviewResponse } from './types';

interface PreviewStepProps {
  preview?: PollODataSendTargetPreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onPreview: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, onPreview }: PreviewStepProps) {
  return (
    <section className="wizard-step integration-master-step poll-preview-step">
      <span className="step-index">07</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Проверить OData, payload и target request</h2>
          <p>Preview рендерит first-run filter, показывает sample rows и outgoing request. Target request здесь не отправляется.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Slug или payload нужно исправить</strong><span>Preview доступен после минимальной настройки job, OData и target URL.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно запускать manual test и сохранять polling job.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}
      {preview ? (
        <div className="pattern-flow-preview-grid send-endpoint-preview-grid">
          <PreviewCard title="Schedule" value={preview.schedule} language="json" />
          <PreviewCard title="OData request" value={preview.odata_request} language="json" />
          <PreviewCard title="First run filter" value={preview.first_run_filter} language="odata" />
          <PreviewCard title="OData result sample" value={preview.odata_result} language="json" />
          <PreviewCard title="Target payload" value={preview.target_payload} language={typeof preview.target_payload === 'string' ? 'text' : 'json'} />
          <PreviewCard title="Target request" value={preview.target_request} language="json" />
          <PreviewCard title="Run history hint" value={preview.run_history_hint} language="json" />
          <section className="panel stack-form">
            <div className="panel-toolbar"><div><span className="eyebrow">Steps</span><h3>Что выполнит OMH</h3></div></div>
            <ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol>
          </section>
        </div>
      ) : (
        <div className="pattern-flow compact">
          <span>OMH Scheduler</span><span>1C OData</span><span>Payload Builder</span><span>External API/WMS</span><span>Run History</span>
        </div>
      )}
      {preview ? (
        <details className="variable-card">
          <summary><span>Advanced config</span><strong>JSON</strong></summary>
          <CodeBlock code={JSON.stringify(preview.advanced, null, 2)} language="json" showToolbar={false} />
        </details>
      ) : null}
    </section>
  );
}

function PreviewCard({ title, value, language }: { title: string; value: unknown; language: string }) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">{title}</span><h3>{title}</h3></div></div>
      <CodeBlock code={formatValue(value)} language={language} showToolbar={false} />
    </section>
  );
}

function formatValue(value: unknown) {
  if (typeof value === 'string') return value;
  return JSON.stringify(value ?? null, null, 2);
}
