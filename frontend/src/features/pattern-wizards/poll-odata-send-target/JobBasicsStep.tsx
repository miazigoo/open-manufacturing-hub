import { slugify } from '../../integration-master/EndpointSlugEditor';
import type { PollODataJobBasicsConfig, PollODataScheduleType } from './types';

interface JobBasicsStepProps {
  job: PollODataJobBasicsConfig;
  onChange: (value: PollODataJobBasicsConfig) => void;
}

export function JobBasicsStep({ job, onChange }: JobBasicsStepProps) {
  const patch = (value: Partial<PollODataJobBasicsConfig>) => onChange({ ...job, ...value });
  return (
    <section className="wizard-step integration-master-step poll-job-basics-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Polling job</span>
          <h2>Задача, которую запускает OMH</h2>
          <p>В этом pattern нет входящего запроса. OMH сам запускает задачу вручную или каждые N минут.</p>
        </div>
        <span className="status-card neutral"><small>Default</small><strong>manual only</strong><span>Сначала тестируем, потом включаем расписание.</span></span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название задачи
          <input value={job.name} onChange={(event) => patch({ name: event.target.value })} placeholder="Sync 1C orders to WMS" />
        </label>
        <label className="field-label">Код задачи / slug
          <input value={job.slug} onChange={(event) => patch({ slug: slugify(event.target.value) })} placeholder="sync-1c-orders-to-wms" />
          <small>Используется для polling job и IntegrationFlow artifact.</small>
        </label>
        <label className="check-row odata-check"><input type="checkbox" checked={job.enabled_after_create} onChange={(event) => patch({ enabled_after_create: event.target.checked })} /> Enabled after create</label>
      </div>
      <div className="metadata-grid compact-grid no-margin request-action-cards">
        <button type="button" className={`builder-help-card action-card ${job.schedule_type === 'manual_only' ? 'active' : ''}`} onClick={() => patch({ schedule_type: 'manual_only' })}>
          <strong>manual_only</strong><span>Запуск только вручную из UI. Безопасный режим для первого теста.</span>
        </button>
        <button type="button" className={`builder-help-card action-card ${job.schedule_type === 'interval_minutes' ? 'active' : ''}`} onClick={() => patch({ schedule_type: 'interval_minutes' })}>
          <strong>interval_minutes</strong><span>OMH будет запускать задачу каждые N минут, если scheduler loop включён.</span>
        </button>
      </div>
      <label className="field-label">Interval minutes
        <input type="number" min={1} max={1440} value={job.interval_minutes} disabled={job.schedule_type === 'manual_only'} onChange={(event) => patch({ interval_minutes: Number(event.target.value) || 5, schedule_type: job.schedule_type as PollODataScheduleType })} />
        <small>Для task 076 cron не реализуется: только manual или простой interval.</small>
      </label>
    </section>
  );
}
