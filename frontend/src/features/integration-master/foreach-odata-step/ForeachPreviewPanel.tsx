import type { ForeachODataStepPreviewResponse } from '../types';

interface ForeachPreviewPanelProps {
  preview?: ForeachODataStepPreviewResponse;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function ForeachPreviewPanel({ preview, error, loading, onPreview }: ForeachPreviewPanelProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Preview</span><h3>Проверить rendered OData</h3><p className="microcopy">Preview берёт первый элемент массива и показывает реальный filter/url без выполнения запроса.</p></div><button type="button" className="ghost-button" disabled={loading} onClick={onPreview}>{loading ? 'Рендерю...' : 'Preview'}</button></div>
      {error ? <div className="error-state compact"><strong>Preview failed</strong><span>{error}</span></div> : null}
      {preview ? <div className={`status-card ${preview.valid ? 'success' : 'danger'}`}><strong>{preview.valid ? 'Preview valid' : 'Preview invalid'}</strong><span>Источник: {preview.items}[] · строк: {preview.source_count} · item_as={preview.item_as}</span></div> : null}
      {preview?.errors.length ? <ul className="issue-list">{preview.errors.map((item) => <li key={item}>{item}</li>)}</ul> : null}
      {preview?.warnings.length ? <ul className="issue-list warning-list">{preview.warnings.map((item) => <li key={item}>{item}</li>)}</ul> : null}
      {preview?.rendered_url ? <pre className="code-block"><code>{preview.rendered_url}</code></pre> : null}
      {preview?.first_item_preview ? <pre className="code-block"><code>{JSON.stringify(preview.first_item_preview, null, 2)}</code></pre> : null}
      {preview?.variables_after_step.length ? <div className="variable-chip-row"><strong>После шага появится</strong>{preview.variables_after_step.map((item) => <code key={item}>{item}</code>)}</div> : null}
    </section>
  );
}
