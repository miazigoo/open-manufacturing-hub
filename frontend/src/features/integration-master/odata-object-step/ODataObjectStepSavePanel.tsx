import type { InputDraftRead, ODataObjectStepConfig } from '../types';

interface ODataObjectStepSavePanelProps {
  draft: InputDraftRead;
  step: ODataObjectStepConfig;
  error?: string | null;
  saving: boolean;
  onSave: () => void;
}

export function ODataObjectStepSavePanel({ draft, step, error, saving, onSave }: ODataObjectStepSavePanelProps) {
  return (
    <section className="panel odata-save-panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Save</span><h3>Сохранить шаг чтения табличной части</h3><p className="microcopy">Сохраняем только `odata_object_query`. Foreach, JSON/XML builder, endpoint send и full integration compile пока не выполняются.</p></div><button type="button" className="primary-button" disabled={saving} onClick={onSave}>{saving ? 'Сохраняю...' : 'Сохранить шаг'}</button></div>
      {error ? <div className="error-state compact">{error}</div> : null}
      <div className="metadata-grid compact-grid no-margin"><span><small>Draft</small><strong>{draft.id}</strong></span><span><small>save_as</small><strong>{step.save_as || 'products'}</strong></span><span><small>Всего OData steps</small><strong>{draft.odata_steps.length}</strong></span></div>
    </section>
  );
}
