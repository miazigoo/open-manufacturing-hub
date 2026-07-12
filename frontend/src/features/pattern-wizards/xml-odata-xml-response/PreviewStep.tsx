import { CodeBlock } from '../../../components/CodeBlock';
import type { XmlODataXmlResponsePreviewResponse } from './types';

interface PreviewStepProps {
  preview?: XmlODataXmlResponsePreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onPreview: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, onPreview }: PreviewStepProps) {
  const endpoint = preview?.endpoint ?? {};

  return (
    <section className="wizard-step integration-master-step xml-odata-preview-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Проверить XML → OData → ответ</h2>
          <p>Preview показывает incoming XML, extracted variables, OData request/result и rendered response.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>

      {disabled ? <div className="status-card warning"><strong>Нужно разобрать XML sample</strong><span>Нажмите «Разобрать поля» и проверьте extract table.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Flow preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно создавать интеграцию.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}

      {preview ? (
        <div className="pattern-flow-preview-grid xml-odata-preview-grid">
          <PreviewCard title="Endpoint" value={`${String(endpoint.method ?? 'POST')} ${String(endpoint.url ?? '')}`} language="text" />
          <PreviewCard title="Incoming XML" value={preview.incoming_xml} language="xml" />
          <PreviewCard title="Extracted variables" value={preview.extracted_variables} language="json" />
          <PreviewCard title="OData request" value={preview.odata_request} language="json" />
          <PreviewCard title="OData result" value={preview.odata_result ?? { empty: true }} language="json" />
          <PreviewCard title="Response to caller" value={preview.response_to_caller} language={typeof preview.response_to_caller === 'string' && String(preview.response_to_caller).trim().startsWith('<') ? 'xml' : typeof preview.response_to_caller === 'string' ? 'text' : 'json'} />
          <section className="panel stack-form">
            <div className="panel-toolbar"><div><span className="eyebrow">Timeline labels</span><h3>Понятные шаги</h3></div></div>
            <ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol>
          </section>
        </div>
      ) : (
        <div className="pattern-flow compact"><span>External XML</span><span>OMH endpoint</span><span>XML extract</span><span>1C OData</span><span>Response builder</span><span>Caller</span></div>
      )}

      {preview ? <details className="variable-card"><summary><span>Advanced details</span><strong>JSON</strong></summary><CodeBlock code={JSON.stringify(preview.advanced, null, 2)} language="json" showToolbar={false} /></details> : null}
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
