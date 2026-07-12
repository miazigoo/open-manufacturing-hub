import type { PollODataFirstRunStrategy, PollODataFirstRunStrategyConfig } from './types';

interface FirstRunStrategyStepProps {
  firstRun: PollODataFirstRunStrategyConfig;
  onChange: (value: PollODataFirstRunStrategyConfig) => void;
}

const options: Array<{ value: PollODataFirstRunStrategy; title: string; description: string }> = [
  { value: 'fixed_start_date', title: 'Начать с указанной даты', description: 'Подставить fixed start date в cursor.last_success_at при первом запуске.' },
  { value: 'last_n_hours', title: 'Взять последние N часов', description: 'Полезно для начального запуска в свежей базе.' },
  { value: 'no_cursor_filter', title: 'Без cursor-фильтра', description: 'Прочитать первые $top записей. Может отправить старые данные.' },
];

export function FirstRunStrategyStep({ firstRun, onChange }: FirstRunStrategyStepProps) {
  const patch = (value: Partial<PollODataFirstRunStrategyConfig>) => onChange({ ...firstRun, ...value });
  return (
    <section className="wizard-step integration-master-step poll-first-run-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">First run</span>
          <h2>Что делать, если cursor ещё пустой</h2>
          <p>Без first-run strategy фильтр с <code>{'{{cursor.last_success_at}}'}</code> может отрендериться в пустое значение.</p>
        </div>
      </div>
      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {options.map((option) => (
          <button key={option.value} type="button" className={`builder-help-card action-card ${firstRun.strategy === option.value ? 'active' : ''}`} onClick={() => patch({ strategy: option.value })}>
            <strong>{option.title}</strong><span>{option.description}</span>
          </button>
        ))}
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Fixed start date
          <input value={firstRun.fixed_start_at} disabled={firstRun.strategy !== 'fixed_start_date'} onChange={(event) => patch({ fixed_start_at: event.target.value })} placeholder="2026-01-01T00:00:00" />
        </label>
        <label className="field-label">Last N hours
          <input type="number" min={1} max={8760} value={firstRun.hours} disabled={firstRun.strategy !== 'last_n_hours'} onChange={(event) => patch({ hours: Number(event.target.value) || 24 })} />
        </label>
        <span className="status-card warning"><small>Warning</small><strong>No cursor filter</strong><span>Режим без cursor-фильтра может отправить старые данные. Используйте только для контролируемой первой выборки.</span></span>
      </div>
    </section>
  );
}
