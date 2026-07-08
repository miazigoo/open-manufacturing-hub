import { CodeBlock } from '../../../components/CodeBlock';
import type { PayloadStepPreviewResponse } from '../types';

interface PayloadPreviewPanelProps {
  preview?: PayloadStepPreviewResponse;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function PayloadPreviewPanel({ preview, error, loading, onPreview }: PayloadPreviewPanelProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Preview</span><h3>Предпросмотр body</h3><p className="microcopy">Preview ничего не отправляет во внешние системы.</p></div><button type="button" className="primary-button" disabled={loading} onClick={onPreview}>{loading ? 'Собираю...' : 'Preview payload'}</button></div>
      {error ? <div className="error-state compact"><strong>Preview failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Payload valid' : preview.error_code ?? 'Payload invalid'}</strong><span>{preview.errors.join('; ') || `${preview.body_type}, ${preview.size_bytes} bytes`}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}
      {preview && preview.rendered_preview !== undefined ? <CodeBlock code={typeof preview.rendered_preview === 'string' ? preview.rendered_preview : JSON.stringify(preview.rendered_preview, null, 2)} language={preview.body_type === 'json' ? 'json' : preview.body_type === 'xml' ? 'xml' : 'text'} title="Rendered preview" showToolbar={false} /> : null}
    </section>
  );
}
