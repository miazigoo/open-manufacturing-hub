import type { RequestPrintPrintModeConfig } from './types';

interface PrintModeStepProps {
  mode: RequestPrintPrintModeConfig;
  onChange: (value: RequestPrintPrintModeConfig) => void;
}

export function PrintModeStep({ mode, onChange }: PrintModeStepProps) {
  return (
    <section className="wizard-step integration-master-step request-print-mode-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading"><div><span className="eyebrow">Print mode</span><h2>Dry-run, test print или print all</h2><p>В wizard и saved test case безопасный default — dry-run. Реальная печать требует явного выбора.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <ModeCard active={mode.mode === 'dry_run'} title="Dry Run" text="Только rendered ZPL и статус, без отправки на принтер." onClick={() => onChange({ mode: 'dry_run' })} />
        <ModeCard active={mode.mode === 'test_one_label'} title="Test print" text="Отправить одну этикетку после подтверждения." onClick={() => onChange({ mode: 'test_one_label' })} />
        <ModeCard active={mode.mode === 'print_all'} title="Print all labels" text="Печатать все labels[] при реальном запуске." onClick={() => onChange({ mode: 'print_all' })} />
      </div>
      {mode.mode !== 'dry_run' ? <div className="status-card warning"><strong>Нужна осторожность</strong><span>При live запуске будет отправлена реальная этикетка на выбранный принтер.</span></div> : null}
    </section>
  );
}

function ModeCard({ active, title, text, onClick }: { active: boolean; title: string; text: string; onClick: () => void }) {
  return <button type="button" className={`selectable-card ${active ? 'active' : ''}`} onClick={onClick}><strong>{title}</strong><span>{text}</span></button>;
}
