import type { ODataObjectStepPreviewResponse } from '../types';

interface ObjectResourcePreviewProps {
  preview?: ODataObjectStepPreviewResponse;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function ObjectResourcePreview({ preview, error, loading, onPreview }: ObjectResourcePreviewProps) {
  return (
    <section className="panel odata-preview-panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Resource preview</span><h3>Template и rendered resource</h3></div><button type="button" className="ghost-button" onClick={onPreview} disabled={loading}>{loading ? 'Собираю...' : 'Preview resource'}</button></div>
      {error ? <div className="error-state compact">{error}</div> : null}
      {preview ? (
        <>
          <div className={preview.valid ? 'success-note' : 'error-state compact'}><strong>{preview.valid ? 'Resource валиден' : 'Нужно исправить'}</strong><span>{preview.valid ? preview.rendered_resource : preview.errors.join('; ')}</span></div>
          <div className="metadata-grid compact-grid no-margin">
            <span><small>Template resource</small><strong className="mono">{preview.template_resource || 'нет'}</strong></span>
            <span><small>Rendered resource</small><strong className="mono">{preview.rendered_resource || 'нет sample value'}</strong></span>
            <span><small>Key preview</small><strong>{formatValue(preview.key_preview)}</strong></span>
          </div>
          {preview.rendered_url ? <div className="success-note"><strong>Rendered URL</strong><span>{preview.rendered_url}</span></div> : null}
          <div className="odata-variable-list"><strong>После шага будут доступны:</strong>{preview.variables_after_step.map((item) => <code key={item}>{item}</code>)}</div>
        </>
      ) : <p className="microcopy">Template использует переменную, например <code>{"Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция"}</code>. Rendered показывает запрос на тестовых данных.</p>}
    </section>
  );
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'нет';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}
