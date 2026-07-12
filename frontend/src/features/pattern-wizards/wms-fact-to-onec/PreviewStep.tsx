import { CodeBlock } from '../../../components/CodeBlock';
import type { WmsFactToOneCPreviewResponse } from './types';

interface PreviewStepProps {
  preview?: WmsFactToOneCPreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onPreview: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, onPreview }: PreviewStepProps) {
  const endpoint = preview?.endpoint ?? {};
  const odataRequest = preview?.odata_request ?? {};
  const onecRequest = preview?.onec_request ?? {};

  return (
    <section className="wizard-step integration-master-step wms-preview-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Проверить весь WMS → 1С flow</h2>
          <p>Preview показывает incoming WMS JSON, optional OData lookup, payload для 1С, HTTP service call и ответ WMS/API. Builder JSON спрятан в Advanced.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>

      {disabled ? <div className="status-card warning"><strong>Нужно разобрать sample</strong><span>Нажмите «Разобрать поля» в шаге 1, чтобы wizard построил Input Contract.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Flow preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно создавать интеграцию.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}

      {preview ? (
        <div className="pattern-flow-preview-grid wms-preview-grid">
          <PreviewCard title="Endpoint" value={`${String(endpoint.method ?? 'POST')} ${String(endpoint.url ?? '')}`} language="text" />
          <PreviewCard title="Incoming WMS request" value={preview.incoming_request} language="json" />
          <PreviewCard title="OData request" value={odataRequest.enabled === false ? 'OData lookup disabled' : String(odataRequest.rendered_url ?? odataRequest.template_url ?? '')} language="odata" />
          <PreviewCard title="OData result" value={preview.odata_result ?? { enabled: odataRequest.enabled, empty: true }} language="json" />
          <PreviewCard title="Payload to 1C" value={preview.onec_payload ?? { empty: true }} language={typeof preview.onec_payload === 'string' ? 'text' : 'json'} />
          <PreviewCard title="1C HTTP service call" value={onecRequest} language="json" />
          <PreviewCard title="1C response" value={preview.onec_response ?? { empty: true }} language="json" />
          <PreviewCard title="Response to WMS/API" value={preview.response_to_caller} language={typeof preview.response_to_caller === 'string' ? 'text' : 'json'} />
          <section className="panel stack-form">
            <div className="panel-toolbar"><div><span className="eyebrow">Timeline labels</span><h3>Понятные шаги</h3></div></div>
            <ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol>
          </section>
        </div>
      ) : (
        <div className="pattern-flow compact">
          <span>WMS/API</span>
          <span>OMH endpoint</span>
          <span>1C OData</span>
          <span>Payload builder</span>
          <span>1C HTTP Service</span>
          <span>WMS response</span>
        </div>
      )}

      {preview ? (
        <details className="variable-card">
          <summary><span>Advanced details</span><strong>JSON</strong></summary>
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
