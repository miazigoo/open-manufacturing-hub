import type { FinalActionPreviewResponse } from '../types';

interface FinalActionPreviewPanelProps {
  preview?: FinalActionPreviewResponse;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function FinalActionPreviewPanel({ preview, error, loading, onPreview }: FinalActionPreviewPanelProps) {
  return (
    <section className="panel stack-form odata-preview-panel final-action-preview-panel">
      <div className="panel-toolbar"><div><span className="eyebrow">Preview</span><h3>Предпросмотр финального действия</h3><p className="microcopy">Dry preview не вызывает target endpoint.</p></div><button type="button" className="primary-button" disabled={loading} onClick={onPreview}>{loading ? 'Собираю...' : 'Preview final action'}</button></div>
      {error ? <div className="error-state compact"><strong>Preview failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.success ? 'success' : 'danger'}`}><strong>{preview.success ? 'Final action valid' : preview.error_code ?? 'Final action invalid'}</strong><span>{preview.errors.join('; ') || preview.human_preview}</span></div> : null}
      {preview?.warnings.length ? <div className="status-card warning"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}
      {preview?.send_preview ? <PreviewBlock title="Would send" value={preview.send_preview} /> : null}
      {preview && preview.caller_response_preview !== undefined ? <PreviewBlock title="Would return to caller" value={preview.caller_response_preview} /> : null}
    </section>
  );
}

function PreviewBlock({ title, value }: { title: string; value: unknown }) {
  return <div className="stack-form"><strong>{title}</strong><pre className="code-block"><code>{typeof value === 'string' ? value : JSON.stringify(value, null, 2)}</code></pre></div>;
}
