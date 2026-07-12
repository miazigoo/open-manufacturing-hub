import { CodeEditor } from '../../../components/CodeEditor';
import { CodeBlock } from '../../../components/CodeBlock';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { SourceWebApiWritebackCallerResponseConfig, SourceWebApiWritebackCallerResponseType } from './types';

interface CallerResponseStepProps {
  response: SourceWebApiWritebackCallerResponseConfig;
  onChange: (value: SourceWebApiWritebackCallerResponseConfig) => void;
}

const RETURN_OPTIONS: Array<{ value: SourceWebApiWritebackCallerResponseType; label: string }> = [
  { value: 'custom_json', label: 'Свой JSON: order + external_id + writeback status' },
  { value: 'site_response', label: 'Вернуть ответ сайта' },
  { value: 'onec_writeback_response', label: 'Вернуть ответ 1С writeback' },
  { value: 'accepted_event', label: 'Вернуть accepted event/run id' },
];

export function CallerResponseStep({ response, onChange }: CallerResponseStepProps) {
  const patch = (patchValue: Partial<SourceWebApiWritebackCallerResponseConfig>) => onChange({ ...response, ...patchValue });
  const bodyText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? defaultCallerBody(), null, 2);

  function changeType(type: SourceWebApiWritebackCallerResponseType) {
    onChange({ ...response, type, status_code: type === 'accepted_event' ? 202 : 200, body: type === 'custom_json' ? defaultCallerBody() : null, headers: { 'Content-Type': 'application/json' } });
  }

  return (
    <section className="wizard-step integration-master-step source-caller-response-step">
      <span className="step-index">08</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Caller response</span>
          <h2>Что вернуть тому, кто вызвал OMH</h2>
          <p>Default custom JSON возвращает номер заказа, внешний ID сайта, статус сайта и результат записи в 1С.</p>
        </div>
        <span className="status-card success"><small>Default</small><strong>custom_json</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Return mode<select value={response.type} onChange={(event) => changeType(event.target.value as SourceWebApiWritebackCallerResponseType)}>{RETURN_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patch({ status_code: Number(event.target.value) || 200 })} /></label>
      </div>

      {response.type === 'custom_json' ? (
        <label className="field-label full-span">Caller response JSON
          <CodeEditor value={bodyText} onChange={(value) => patch({ body: value })} language="json" minRows={7} />
        </label>
      ) : null}

      {response.type !== 'custom_json' ? (
        <div className="status-card neutral">
          <strong>Selected response mode</strong>
          <CodeBlock code={response.type === 'site_response' ? '{{site_response}}' : response.type === 'onec_writeback_response' ? '{{onec_writeback_response}}' : JSON.stringify({ accepted: true, event_id: '{{context.event_id}}', run_id: '{{context.run_id}}' }, null, 2)} language={response.type === 'accepted_event' ? 'json' : 'text'} showToolbar={false} />
        </div>
      ) : null}

      <EndpointHeadersEditor value={response.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} label="Caller response headers" />
    </section>
  );
}

export function defaultCallerBody() {
  return {
    success: true,
    order_number: '{{order.Number}}',
    external_id: '{{site_response.external_id}}',
    site_status: '{{site_response.status}}',
    onec_writeback_success: '{{onec_writeback_response.success}}',
  };
}
