import { CodeBlock } from '../../../components/CodeBlock';
import type { RequestMultipleODataResponsePreviewResponse } from './types';

interface PreviewStepProps {
  preview?: RequestMultipleODataResponsePreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onPreview: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, onPreview }: PreviewStepProps) {
  return (
    <section className="wizard-step integration-master-step request-multiple-preview-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Проверить flow до сохранения</h2>
          <p>Preview показывает incoming request, OData request 1, OData request 2 и response to caller. Raw builder JSON спрятан в advanced.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Нужно разобрать sample</strong><span>Нажмите «Разобрать поля» в шаге 1.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Flow preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно создавать интеграцию.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}

      {preview ? (
        <div className="pattern-flow-preview-grid request-multiple-preview-grid">
          <PreviewCard title="Incoming request" value={preview.incoming_request} />
          <PreviewCard title="OData request 1" value={preview.order_request} />
          <PreviewCard title="Order result" value={preview.order_result} />
          <PreviewCard title="OData request 2" value={preview.items_request} />
          <PreviewCard title="Items result" value={preview.items_result} />
          <PreviewCard title="Response to caller" value={preview.response_to_caller} language={typeof preview.response_to_caller === 'string' ? 'xml' : 'json'} />
          <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">Timeline labels</span><h3>Человеческие шаги</h3></div></div><ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol></section>
        </div>
      ) : (
        <div className="pattern-flow compact">
          <span>External API</span>
          <span>OMH endpoint</span>
          <span>OData order</span>
          <span>OData Товары</span>
          <span>XML response</span>
        </div>
      )}
      {preview ? <details className="variable-card"><summary><span>Advanced details</span><strong>JSON</strong></summary><CodeBlock code={JSON.stringify(preview.advanced, null, 2)} language="json" showToolbar={false} /></details> : null}
    </section>
  );
}

function PreviewCard({ title, value, language }: { title: string; value: unknown; language?: string }) {
  const code = typeof value === 'string' ? value : JSON.stringify(value ?? null, null, 2);
  return <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">{title}</span><h3>{title}</h3></div></div><CodeBlock code={code} language={language ?? (typeof value === 'string' ? 'text' : 'json')} showToolbar={false} /></section>;
}
