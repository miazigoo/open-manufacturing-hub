import type { PayloadStepConfig } from '../types';

interface PayloadSavePanelProps {
  step: PayloadStepConfig;
  error?: string | null;
  saving: boolean;
  onSave: () => void;
}

export function PayloadSavePanel({ step, error, saving, onSave }: PayloadSavePanelProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Save</span><h3>Сохранить Step 3A</h3><p className="microcopy">Будет добавлен draft-шаг `build_payload`; endpoint send и caller response пока не создаются.</p></div><button type="button" className="primary-button" disabled={saving} onClick={onSave}>{saving ? 'Сохраняю...' : `Сохранить ${step.save_as || 'target_payload'}`}</button></div>
      {error ? <div className="error-state compact"><strong>Save failed</strong><span>{error}</span></div> : null}
    </section>
  );
}
