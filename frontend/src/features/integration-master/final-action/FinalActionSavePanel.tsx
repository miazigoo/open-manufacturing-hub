import type { FinalActionConfig, InputDraftRead } from '../types';

interface FinalActionSavePanelProps {
  draft: InputDraftRead;
  action: FinalActionConfig;
  error?: string | null;
  saving: boolean;
  onSave: () => void;
}

export function FinalActionSavePanel({ draft, action, error, saving, onSave }: FinalActionSavePanelProps) {
  return (
    <section className="panel stack-form odata-save-panel final-action-save-panel">
      <div className="panel-toolbar"><div><span className="eyebrow">Save</span><h3>Сохранить Step 4A</h3><p className="microcopy">Сохраняем только draft-конфигурацию final_action. Compile/publish не запускается.</p></div><button type="button" className="primary-button" disabled={saving} onClick={onSave}>{saving ? 'Сохраняю...' : 'Сохранить final action'}</button></div>
      <div className="metadata-grid compact-grid no-margin">
        <span><small>Draft</small><strong>{draft.id}</strong></span>
        <span><small>Action</small><strong>{action.type}</strong></span>
        <span><small>Saved</small><strong>{draft.final_action ? draft.final_action.type : 'not yet'}</strong></span>
      </div>
      {error ? <div className="error-state compact"><strong>Save failed</strong><span>{error}</span></div> : null}
    </section>
  );
}
