import { CodeBlock } from '../../../components/CodeBlock';
import type { RequestPrintPreviewResponse, RequestPrintTestPrintResponse } from './types';

interface PreviewStepProps {
  preview?: RequestPrintPreviewResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  testPrint?: RequestPrintTestPrintResponse;
  testPrintError?: string | null;
  testPrintLoading: boolean;
  onPreview: () => void;
  onTestPrint: () => void;
}

export function PreviewStep({ preview, error, loading, disabled, testPrint, testPrintError, testPrintLoading, onPreview, onTestPrint }: PreviewStepProps) {
  const endpoint = preview?.endpoint ?? {};
  return (
    <section className="wizard-step integration-master-step request-print-preview-step">
      <span className="step-index">07</span>
      <div className="odata-step-heading">
        <div><span className="eyebrow">Preview</span><h2>Проверить ZPL и print status</h2><p>Preview показывает incoming JSON, выбранный принтер, labels count, rendered ZPL и response caller-у.</p></div>
        <div className="button-row"><button type="button" className="primary-button" disabled={loading || disabled} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button><button type="button" className="secondary-button" disabled={testPrintLoading || disabled} onClick={onTestPrint}>{testPrintLoading ? 'Печатаю...' : 'Test print / dry-run'}</button></div>
      </div>
      {disabled ? <div className="status-card warning"><strong>Нужно разобрать JSON sample</strong><span>Нажмите «Разобрать поля» и проверьте labels[].</span></div> : null}
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {testPrintError ? <div className="status-card danger"><strong>Test print failed</strong><span>{testPrintError}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Print preview valid' : 'Нужно исправить'}</strong><span>{preview.errors.join('; ') || 'Можно создавать интеграцию.'}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}

      {preview ? (
        <div className="pattern-flow-preview-grid request-print-preview-grid">
          <PreviewCard title="Endpoint" value={`${String(endpoint.method ?? 'POST')} ${String(endpoint.url ?? '')}`} language="text" />
          <PreviewCard title="Incoming request" value={preview.incoming_request} language="json" />
          <PreviewCard title="Selected printer" value={preview.selected_printer ?? { missing: true }} language="json" />
          <PreviewCard title="Rendered ZPL first label" value={preview.rendered_zpl_first_label} language="text" />
          <PreviewCard title="Response to caller" value={preview.response_to_caller} language="json" />
          <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">Timeline labels</span><h3>Понятные шаги</h3></div></div><ol className="compile-summary-list">{preview.human_steps.map((step) => <li key={step}>{step}</li>)}</ol></section>
        </div>
      ) : <div className="pattern-flow compact"><span>1C / WMS</span><span>OMH endpoint</span><span>labels[]</span><span>ZPL template</span><span>Printer</span><span>Status</span></div>}

      {testPrint ? <details className="variable-card" open><summary><span>Test print result</span><strong>JSON</strong></summary><CodeBlock code={JSON.stringify(testPrint.print_result, null, 2)} language="json" showToolbar={false} /></details> : null}
      {preview ? <details className="variable-card"><summary><span>Advanced details</span><strong>JSON</strong></summary><CodeBlock code={JSON.stringify(preview.advanced, null, 2)} language="json" showToolbar={false} /></details> : null}
    </section>
  );
}

function PreviewCard({ title, value, language }: { title: string; value: unknown; language: string }) {
  return <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">{title}</span><h3>{title}</h3></div></div><CodeBlock code={formatValue(value)} language={language} showToolbar={false} /></section>;
}

function formatValue(value: unknown) {
  if (typeof value === 'string') return value;
  return JSON.stringify(value ?? null, null, 2);
}
