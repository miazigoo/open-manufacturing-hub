import { Link } from 'react-router-dom';
import type { PollODataSendTargetCreateResponse } from './types';

interface SaveStepProps {
  result?: PollODataSendTargetCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onCreate: () => void;
}

export function SaveStep({ result, error, loading, disabled, onCreate }: SaveStepProps) {
  if (result) {
    return (
      <section className="wizard-step integration-master-step poll-save-step">
        <span className="step-index">09</span>
        <div className="odata-step-heading">
          <div>
            <span className="eyebrow">Saved</span>
            <h2>Polling-интеграция создана</h2>
            <p>Задача создана disabled by default. Проверьте manual run и историю запусков перед включением расписания.</p>
          </div>
          <span className="status-card success"><small>Polling job</small><strong>{result.polling_job_id}</strong></span>
        </div>
        <div className="metadata-grid compact-grid no-margin">
          <span className="status-card neutral"><small>Enabled</small><strong>{String(result.enabled)}</strong><span>По умолчанию выключено для безопасной проверки.</span></span>
          <span className="status-card neutral"><small>Run now</small><strong>{result.run_now_url}</strong><span>Endpoint ручного запуска.</span></span>
          <span className="status-card neutral"><small>Runs</small><strong>{result.runs_url}</strong><span>История запусков и cursor before/after.</span></span>
        </div>
        <ol className="compile-summary-list">{result.next_steps.map((step) => <li key={step}>{step}</li>)}</ol>
        <div className="action-row wrap-actions">
          <Link className="primary-button" to={`/polling?jobId=${result.polling_job_id}`}>Запустить вручную / история</Link>
          <Link className="ghost-button" to="/polling">Открыть Polling Jobs</Link>
          <Link className="ghost-button" to="/docs/onec/recipes/poll-odata-send-target">Открыть рецепт</Link>
          <button type="button" className="ghost-button" onClick={() => copySetup(result)}>Скопировать описание настройки</button>
        </div>
      </section>
    );
  }

  return (
    <section className="wizard-step integration-master-step poll-save-step">
      <span className="step-index">09</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Save polling integration</span>
          <h2>Создать Polling Job и IntegrationFlow artifact</h2>
          <p>Backend создаст dedicated polling job, builder_json с OData/Payload/Target steps и run history. Production enable остаётся ручным действием.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onCreate}>{loading ? 'Создаю...' : 'Создать polling-интеграцию'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Сначала нужен valid preview</strong><span>Создание доступно после успешного preview.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Create failed</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span className="status-card neutral"><small>Runtime</small><strong>PollingJob</strong><span>Manual run работает через `/api/polling-jobs/{'{id}'}/run-now`.</span></span>
        <span className="status-card neutral"><small>Cursor</small><strong>watermark</strong><span>Обновляется только при успешном real run.</span></span>
        <span className="status-card neutral"><small>Status</small><strong>partial</strong><span>Без enterprise scheduler locks/retry/DLQ в этом task.</span></span>
      </div>
    </section>
  );
}

function copySetup(result: PollODataSendTargetCreateResponse) {
  const text = [
    'Polling-интеграция создана',
    `Polling job: ${result.polling_job_id}`,
    `Integration flow: ${result.integration_flow_id ?? 'n/a'}`,
    `Run now: ${result.run_now_url}`,
    `Runs: ${result.runs_url}`,
    `Enabled: ${result.enabled}`,
  ].join('\n');
  void navigator.clipboard?.writeText(text);
}
