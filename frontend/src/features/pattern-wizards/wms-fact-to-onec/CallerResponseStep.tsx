import { CodeEditor } from '../../../components/CodeEditor';
import { CodeBlock } from '../../../components/CodeBlock';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { WmsCallerResponseType, WmsFactToOneCCallerResponseConfig } from './types';

interface CallerResponseStepProps {
  response: WmsFactToOneCCallerResponseConfig;
  onChange: (value: WmsFactToOneCCallerResponseConfig) => void;
}

const RETURN_OPTIONS: Array<{ value: WmsCallerResponseType; label: string }> = [
  { value: 'normalized', label: 'Return normalized response' },
  { value: 'raw_onec_response', label: 'Return raw 1C response' },
  { value: 'accepted_event', label: 'Accepted event' },
];

export function CallerResponseStep({ response, onChange }: CallerResponseStepProps) {
  const patch = (patchValue: Partial<WmsFactToOneCCallerResponseConfig>) => onChange({ ...response, ...patchValue });
  const bodyText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? defaultCallerBody(), null, 2);

  function changeType(type: WmsCallerResponseType) {
    onChange({ ...response, type, status_code: type === 'accepted_event' ? 202 : 200, body: type === 'normalized' ? defaultCallerBody() : null, headers: { 'Content-Type': 'application/json' } });
  }

  return (
    <section className="wizard-step integration-master-step wms-caller-response-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Response to WMS/API</span>
          <h2>Что вернуть WMS</h2>
          <p>Default normalized response возвращает бизнес-ключи и полный оригинальный ответ 1С, включая business error.</p>
        </div>
        <span className="status-card success"><small>Default</small><strong>normalized</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Return mode<select value={response.type} onChange={(event) => changeType(event.target.value as WmsCallerResponseType)}>{RETURN_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patch({ status_code: Number(event.target.value) || 200 })} /></label>
      </div>

      {response.type === 'normalized' ? (
        <label className="field-label full-span">Caller response JSON
          <CodeEditor value={bodyText} onChange={(value) => patch({ body: value })} language="json" minRows={8} />
        </label>
      ) : null}

      {response.type !== 'normalized' ? (
        <div className="status-card neutral">
          <strong>Selected response mode</strong>
          <CodeBlock code={response.type === 'raw_onec_response' ? '{{onec_response}}' : JSON.stringify({ accepted: true, event_id: '{{context.event_id}}', run_id: '{{context.run_id}}' }, null, 2)} language={response.type === 'accepted_event' ? 'json' : 'text'} showToolbar={false} />
        </div>
      ) : null}

      <EndpointHeadersEditor value={response.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} label="Caller response headers" />
    </section>
  );
}

export function defaultCallerBody() {
  return {
    success: '{{onec_response.success}}',
    wms_shipment_id: '{{request.body.wms_shipment_id}}',
    order_number: '{{request.body.order_number}}',
    onec_response: '{{onec_response}}',
  };
}
