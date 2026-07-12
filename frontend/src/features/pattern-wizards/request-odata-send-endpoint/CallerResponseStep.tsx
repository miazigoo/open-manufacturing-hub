import { CodeEditor } from '../../../components/CodeEditor';
import { CodeBlock } from '../../../components/CodeBlock';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionReturnType } from '../../integration-master/types';
import type { RequestODataSendEndpointResponseConfig } from './types';

interface CallerResponseStepProps {
  response: RequestODataSendEndpointResponseConfig;
  onChange: (value: RequestODataSendEndpointResponseConfig) => void;
}

const RETURN_OPTIONS: Array<{ value: FinalActionReturnType; label: string }> = [
  { value: 'proxy_response', label: 'Вернуть ответ внешнего endpoint' },
  { value: 'custom_json', label: 'Вернуть fixed success JSON' },
  { value: 'accepted_event', label: 'Вернуть accepted event_id/queue_item_id' },
  { value: 'custom_xml', label: 'Вернуть свой XML' },
  { value: 'custom_raw', label: 'Вернуть свой raw text' },
  { value: 'fixed_success', label: 'HTTP 200 {"ok": true}' },
];

export function CallerResponseStep({ response, onChange }: CallerResponseStepProps) {
  const patch = (patchValue: Partial<RequestODataSendEndpointResponseConfig>) => onChange({ ...response, ...patchValue });
  const bodyText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? defaultResponseBody(response.type), null, 2);

  function changeType(type: FinalActionReturnType) {
    onChange({ ...response, type, status_code: type === 'accepted_event' ? 202 : 200, body: defaultResponseBody(type), headers: defaultResponseHeaders(type) });
  }

  return (
    <section className="wizard-step integration-master-step pattern-caller-response-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Caller response</span>
          <h2>Что вернуть тому, кто вызвал OMH</h2>
          <p>По умолчанию OMH вернёт ответ внешнего endpoint. Если 1С не должна ждать target response, выберите accepted или fixed success.</p>
        </div>
        <span className="status-card success"><small>Default</small><strong>proxy_response</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Return mode
          <select value={response.type} onChange={(event) => changeType(event.target.value as FinalActionReturnType)}>
            {RETURN_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="field-label">HTTP status
          <input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patch({ status_code: Number(event.target.value) || 200 })} />
        </label>
      </div>

      {response.type === 'proxy_response' ? (
        <div className="status-card neutral">
          <strong>OMH проксирует target response</strong>
          <span>Если внешний endpoint вернёт 4xx/5xx, оригинальный status/body сохраняется в Timeline и возвращается caller-у по proxy mode.</span>
        </div>
      ) : null}

      {response.type === 'fixed_success' ? (
        <div className="status-card success">
          <strong>Будет возвращено вызывающей системе</strong>
          <CodeBlock code={JSON.stringify({ ok: true }, null, 2)} language="json" showToolbar={false} />
          <span>Если нужен другой JSON, выберите режим fixed success JSON.</span>
        </div>
      ) : null}

      {['custom_json', 'custom_xml', 'custom_raw'].includes(response.type) ? (
        <label className="field-label full-span">Caller response body
          <CodeEditor
            value={bodyText}
            onChange={(value) => patch({ body: value })}
            language={response.type === 'custom_xml' ? 'xml' : response.type === 'custom_raw' ? 'text' : 'json'}
            minRows={6}
          />
          <small>Можно использовать placeholders из `target_payload`, `request.body` и `context`.</small>
        </label>
      ) : null}

      <EndpointHeadersEditor value={response.headers ?? {}} onChange={(headers) => patch({ headers })} label="Caller response headers" />
    </section>
  );
}

function defaultResponseBody(type: FinalActionReturnType) {
  if (type === 'custom_xml') return '<Response><Success>true</Success></Response>';
  if (type === 'custom_raw') return 'accepted';
  if (type === 'accepted_event') return null;
  if (type === 'fixed_success') return { ok: true };
  if (type === 'proxy_response') return null;
  return {
    success: true,
    status: 'sent',
    order_number: '{{request.body.order_number}}',
  };
}

function defaultResponseHeaders(type: FinalActionReturnType) {
  if (type === 'custom_xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (type === 'custom_raw') return { 'Content-Type': 'text/plain; charset=utf-8' };
  if (type === 'custom_json' || type === 'fixed_success') return { 'Content-Type': 'application/json' };
  return {};
}
