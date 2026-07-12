import { CodeBlock } from '../../../components/CodeBlock';
import type { DnpChzPreviewResponse } from './types';

interface PreviewStepProps {
  preview?: DnpChzPreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onPreview: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, onPreview }: PreviewStepProps) {
  return (
    <section className="wizard-step integration-master-step dnp-preview-step">
      <span className="step-index">07</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Проверить весь DnP flow</h2>
          <p>Preview показывает incoming request, OData order, products, foreach codes, payload, final send и caller response.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Нужно разобрать sample</strong><span>Нажмите «Разобрать поля» в шаге 1.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Flow preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно создавать интеграцию.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}
      {preview ? (
        <div className="pattern-flow-preview-grid dnp-preview-grid">
          <PreviewCard title="Incoming request" value={preview.incoming_request} />
          <PreviewCard title="OData request 1" value={preview.order_request} />
          <PreviewCard title="Order result" value={preview.order_result} />
          <PreviewCard title="OData object query" value={preview.products_request} />
          <PreviewCard title="Products" value={preview.products_result} />
          <PreviewCard title="Foreach OData" value={{ requests: preview.codes_requests, summary: preview.codes_summary }} />
          <PreviewCard title="Payload to DnP" value={preview.target_payload} />
          <PreviewCard title="Final send" value={preview.target_request} />
          <PreviewCard title="Caller response" value={preview.response_to_caller} />
          <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">Timeline labels</span><h3>Человеческие шаги</h3></div></div><ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol></section>
        </div>
      ) : null}
      {preview ? <details className="variable-card"><summary><span>Advanced details</span><strong>JSON</strong></summary><CodeBlock code={JSON.stringify(preview.advanced, null, 2)} language="json" showToolbar={false} /></details> : null}
    </section>
  );
}

function PreviewCard({ title, value }: { title: string; value: unknown }) {
  return <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">{title}</span><h3>{title}</h3></div></div><CodeBlock code={typeof value === 'string' ? value : JSON.stringify(value ?? null, null, 2)} language={typeof value === 'string' ? 'text' : 'json'} showToolbar={false} /></section>;
}
