import type { ForeachODataStepConfig, InputDraftRead, IntegrationMasterODataStep } from '../types';

interface ForeachSavePanelProps {
  draft: InputDraftRead;
  step: ForeachODataStepConfig;
  error?: string | null;
  saving: boolean;
  onSave: () => void;
}

export function ForeachSavePanel({ draft, step, error, saving, onSave }: ForeachSavePanelProps) {
  return (
    <section className="panel stack-form save-panel">
      <div className="panel-toolbar"><div><span className="eyebrow">Save</span><h3>Сохранить foreach OData step</h3><p className="microcopy">Сохраняем только `foreach_odata`. JSON/XML builder, endpoint send и full integration compile пока не выполняются.</p></div><button type="button" className="primary-button" disabled={saving} onClick={onSave}>{saving ? 'Сохраняю...' : 'Сохранить foreach'}</button></div>
      {error ? <div className="error-state compact"><strong>Не удалось сохранить</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span><small>save_as</small><strong>{step.save_as}</strong></span>
        <span><small>source</small><strong>{step.items}[]</strong></span>
        <span><small>merge</small><strong>{step.merge}</strong></span>
        <span><small>Сохранённых OData steps</small><strong>{draft.odata_steps.length}</strong></span>
      </div>
      {draft.odata_steps.length ? <div className="saved-step-list">{draft.odata_steps.map((item, index) => <span key={item.id ?? `${item.type}-${index}`}>{savedStepLabel(item, index)}</span>)}</div> : null}
    </section>
  );
}

function savedStepLabel(step: IntegrationMasterODataStep, index: number) {
  const name = step.id ?? `step_${index + 1}`;
  if (step.type === 'foreach_odata') return `${name} · foreach ${step.items}[] -> ${step.resource} · save_as=${step.save_as}`;
  if (step.type === 'odata_object_query') return `${name} · ${step.base_resource}/${step.nested_resource} · save_as=${step.save_as}`;
  return `${name} · ${step.resource} · save_as=${step.save_as}`;
}
