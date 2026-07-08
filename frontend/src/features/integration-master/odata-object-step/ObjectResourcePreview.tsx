import type { ODataObjectStepPreviewResponse } from '../types';

export interface ObjectLivePreview {
  template_resource: string | null;
  rendered_resource: string | null;
  rendered_url: string | null;
  full_rendered_url: string | null;
  key_preview: unknown;
}

interface ObjectResourcePreviewProps {
  livePreview: ObjectLivePreview;
  preview?: ODataObjectStepPreviewResponse;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function ObjectResourcePreview({ livePreview, preview, error, loading, onPreview }: ObjectResourcePreviewProps) {
  const templateResource = preview?.template_resource ?? livePreview.template_resource;
  const renderedResource = preview?.rendered_resource ?? livePreview.rendered_resource;
  const renderedUrl = preview?.rendered_url ?? livePreview.rendered_url;
  const keyPreview = preview?.key_preview ?? livePreview.key_preview;

  return (
    <section className="panel odata-preview-panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Live OData URL</span><h3>Итоговая ссылка для сверки</h3><p className="microcopy">Ссылка ниже меняется сразу при вводе. Кириллица показана читаемо, как оператор привык видеть в OData.</p></div><button type="button" className="ghost-button" onClick={onPreview} disabled={loading}>{loading ? 'Проверяю...' : 'Проверить ресурс'}</button></div>
      <div className="success-note odata-live-url"><strong>Полная ссылка</strong><span>{livePreview.full_rendered_url ?? renderedUrl ?? 'Заполните объект, поле ссылки и табличную часть.'}</span></div>
      {error ? <div className="error-state compact">{error}</div> : null}
      {preview ? (
        <>
          <div className={preview.valid ? 'success-note' : 'error-state compact'}><strong>{preview.valid ? 'Resource валиден' : 'Нужно исправить'}</strong><span>{preview.valid ? preview.rendered_resource : preview.errors.join('; ')}</span></div>
          <div className="metadata-grid compact-grid no-margin">
            <span><small>Template resource</small><strong className="mono">{templateResource || 'нет'}</strong></span>
            <span><small>Rendered resource</small><strong className="mono">{renderedResource || 'нет sample value'}</strong></span>
            <span><small>Key preview</small><strong>{formatValue(keyPreview)}</strong></span>
          </div>
          {renderedUrl ? <div className="success-note"><strong>Rendered URL без base URL</strong><span>{renderedUrl}</span></div> : null}
          <div className="odata-variable-list"><strong>После шага будут доступны:</strong>{preview.variables_after_step.map((item) => <code key={item}>{item}</code>)}</div>
        </>
      ) : (
        <>
          <div className="metadata-grid compact-grid no-margin">
            <span><small>Template resource</small><strong className="mono">{templateResource || 'нет'}</strong></span>
            <span><small>Rendered resource</small><strong className="mono">{renderedResource || 'нет sample value'}</strong></span>
            <span><small>Key preview</small><strong>{formatValue(keyPreview)}</strong></span>
          </div>
          {renderedUrl ? <div className="success-note"><strong>Rendered URL без base URL</strong><span>{renderedUrl}</span></div> : null}
        </>
      )}
    </section>
  );
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'нет';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}
