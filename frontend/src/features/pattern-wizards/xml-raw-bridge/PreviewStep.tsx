import { CodeBlock } from '../../../components/CodeBlock';
import type { XmlRawBridgePreviewResponse } from './types';

interface PreviewStepProps {
  preview?: XmlRawBridgePreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onPreview: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, onPreview }: PreviewStepProps) {
  const endpoint = preview?.endpoint ?? {};
  const hash = preview?.hash_check ?? {};

  return (
    <section className="wizard-step integration-master-step xml-raw-preview-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Проверить XML raw bridge</h2>
          <p>Preview показывает incoming endpoint, original XML, target request, target response sample и SHA256 check.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>

      {disabled ? <div className="status-card warning"><strong>Нужно разобрать XML sample</strong><span>Нажмите «Разобрать поля» в шаге 1, чтобы wizard построил Input Contract и XML paths.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Flow preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно создавать интеграцию.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}

      {preview ? (
        <div className="pattern-flow-preview-grid xml-raw-preview-grid">
          <PreviewCard title="Endpoint" value={`${String(endpoint.method ?? 'POST')} ${String(endpoint.url ?? '')}`} language="text" />
          <PreviewCard title="Original XML" value={preview.incoming_xml} language="xml" />
          <PreviewCard title="Hash check" value={hash} language="json" />
          <PreviewCard title="Target request" value={preview.target_request ?? { empty: true }} language="json" />
          <PreviewCard title="Target response sample" value={preview.target_response ?? { empty: true }} language={typeof preview.target_response === 'string' ? 'text' : 'json'} />
          <PreviewCard title="Caller response" value={preview.response_to_caller} language={typeof preview.response_to_caller === 'string' ? 'text' : 'json'} />
          <section className="panel stack-form">
            <div className="panel-toolbar"><div><span className="eyebrow">XML paths</span><h3>Поля для видимости</h3></div></div>
            <div className="xml-path-grid">
              <div className="xml-path-head"><span>Path</span><span>Preview value</span><span>Type</span></div>
              {preview.xml_paths.slice(0, 80).map((item) => <div className="xml-path-row" key={String(item.path)}><code>{String(item.path)}</code><span>{String(item.value_preview ?? '')}</span><span>{String(item.type ?? 'text')}</span></div>)}
            </div>
          </section>
          <section className="panel stack-form">
            <div className="panel-toolbar"><div><span className="eyebrow">Timeline labels</span><h3>Понятные шаги</h3></div></div>
            <ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol>
          </section>
        </div>
      ) : (
        <div className="pattern-flow compact">
          <span>1C XML</span>
          <span>OMH endpoint</span>
          <span>raw XML artifact</span>
          <span>target endpoint</span>
          <span>hash check</span>
          <span>caller response</span>
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
