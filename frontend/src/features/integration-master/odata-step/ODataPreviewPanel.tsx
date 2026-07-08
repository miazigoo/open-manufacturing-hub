import type { ODataStepPreviewResponse } from '../types';

interface ODataPreviewPanelProps {
  preview?: ODataStepPreviewResponse;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function ODataPreviewPanel({ preview, error, loading, onPreview }: ODataPreviewPanelProps) {
  return (
    <section className="panel odata-preview-panel stack-form">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Preview</span><h3>Проверка URL и переменных</h3></div>
        <button type="button" className="ghost-button" onClick={onPreview} disabled={loading}>{loading ? 'Собираю...' : 'Проверить URL'}</button>
      </div>
      {error ? <div className="error-state compact">{error}</div> : null}
      {preview ? (
        <>
          <div className={preview.valid ? 'success-note' : 'error-state compact'}><strong>{preview.valid ? 'URL валиден' : 'Нужно исправить'}</strong><span>{preview.valid ? preview.rendered_url : preview.errors.join('; ')}</span></div>
          <div className="metadata-grid compact-grid no-margin">
            <span><small>Template filter</small><strong className="mono">{preview.template_filter || 'нет'}</strong></span>
            <span><small>Rendered filter</small><strong className="mono">{preview.rendered_filter || 'нет'}</strong></span>
            <span><small>save_as</small><strong>{preview.saved_as}</strong></span>
          </div>
          {preview.warnings.length ? <div className="warning-note"><strong>Warnings</strong><span>{preview.warnings.join('; ')}</span></div> : null}
          <div className="odata-variable-list"><strong>После шага будут доступны:</strong>{preview.variables_after_step.map((item) => <code key={item}>{item}</code>)}</div>
        </>
      ) : <p className="microcopy">Preview рендерит шаблон, например <code>{"Number eq '{{request.body.Number}}'"}</code>, на sample из Input Contract.</p>}
    </section>
  );
}
