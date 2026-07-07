import type { InputDraftRead, IntegrationMasterODataStep, ODataStepConfig } from '../types';

interface ODataStepSavePanelProps {
  draft: InputDraftRead;
  step: ODataStepConfig;
  error?: string | null;
  saving: boolean;
  onSave: () => void;
}

export function ODataStepSavePanel({ draft, step, error, saving, onSave }: ODataStepSavePanelProps) {
  return (
    <section className="panel odata-save-panel stack-form">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Save</span><h3>Сохранить OData step в draft</h3><p className="microcopy">Этот шаг сохраняет только один OData query после Input Contract. Compile, foreach и endpoint send будут следующими шагами мастера.</p></div>
        <button type="button" className="primary-button" disabled={saving} onClick={onSave}>{saving ? 'Сохраняю...' : 'Save OData step'}</button>
      </div>
      {error ? <div className="error-state compact">{error}</div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span><small>Draft</small><strong>{draft.id}</strong></span>
        <span><small>save_as</small><strong>{step.save_as || 'order'}</strong></span>
        <span><small>Сохранённых OData steps</small><strong>{draft.odata_steps.length}</strong></span>
      </div>
      {draft.odata_steps.length ? <div className="odata-saved-list">{draft.odata_steps.map((savedStep, index) => <code key={`${savedStep.id ?? index}-${savedStep.save_as}`}>{savedStepLabel(savedStep, index)}</code>)}</div> : null}
    </section>
  );
}

function savedStepLabel(step: IntegrationMasterODataStep, index: number) {
  const name = step.id ?? `step_${index + 1}`;
  if (step.type === 'odata_object_query') return `${name} · ${step.base_resource}/${step.nested_resource} · save_as=${step.save_as}`;
  return `${name} · ${step.resource} · save_as=${step.save_as}`;
}
