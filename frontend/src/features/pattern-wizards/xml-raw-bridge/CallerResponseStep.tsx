import { CodeEditor } from '../../../components/CodeEditor';
import { CodeBlock } from '../../../components/CodeBlock';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { XmlRawBridgeCallerResponseConfig, XmlRawBridgeCallerResponseType } from './types';

interface CallerResponseStepProps {
  response: XmlRawBridgeCallerResponseConfig;
  onChange: (value: XmlRawBridgeCallerResponseConfig) => void;
}

const RETURN_OPTIONS: Array<{ value: XmlRawBridgeCallerResponseType; label: string }> = [
  { value: 'proxy_target_response', label: 'Return target response' },
  { value: 'fixed_success', label: 'Fixed success body' },
  { value: 'accepted_event', label: 'Accepted event' },
  { value: 'custom_json', label: 'Custom JSON' },
  { value: 'custom_xml', label: 'Custom XML' },
  { value: 'custom_raw', label: 'Custom raw text' },
];

export function CallerResponseStep({ response, onChange }: CallerResponseStepProps) {
  const patch = (patchValue: Partial<XmlRawBridgeCallerResponseConfig>) => onChange({ ...response, ...patchValue });
  const bodyText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? defaultCallerBody(), null, 2);

  function changeType(type: XmlRawBridgeCallerResponseType) {
    onChange({ ...response, type, status_code: type === 'accepted_event' ? 202 : 200, body: defaultBodyFor(type), headers: { 'Content-Type': type === 'custom_xml' ? 'application/xml' : 'application/json' } });
  }

  return (
    <section className="wizard-step integration-master-step xml-raw-caller-response-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Caller response</span>
          <h2>Что вернуть отправителю XML</h2>
          <p>Default: вернуть ответ принимающей 1С как есть. Для async-contract можно вернуть accepted event.</p>
        </div>
        <span className="status-card success"><small>Default</small><strong>proxy target response</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Return mode<select value={response.type} onChange={(event) => changeType(event.target.value as XmlRawBridgeCallerResponseType)}>{RETURN_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patch({ status_code: Number(event.target.value) || 200 })} /></label>
      </div>

      {['fixed_success', 'custom_json', 'custom_xml', 'custom_raw'].includes(response.type) ? (
        <label className="field-label full-span">Response body
          <CodeEditor value={bodyText} onChange={(value) => patch({ body: value })} language={response.type === 'custom_xml' ? 'xml' : response.type === 'custom_raw' ? 'text' : 'json'} minRows={7} />
        </label>
      ) : (
        <div className="status-card neutral">
          <strong>Selected response mode</strong>
          <CodeBlock code={response.type === 'proxy_target_response' ? '{{target_response}}' : JSON.stringify({ accepted: true, event_id: '{{context.event_id}}', run_id: '{{context.run_id}}' }, null, 2)} language={response.type === 'accepted_event' ? 'json' : 'text'} showToolbar={false} />
        </div>
      )}

      <EndpointHeadersEditor value={response.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} label="Caller response headers" />
    </section>
  );
}

export function defaultCallerBody() {
  return { success: true, xml_forwarded: true, unchanged: '{{xml_hashes.unchanged}}', target_response: '{{target_response}}' };
}

function defaultBodyFor(type: XmlRawBridgeCallerResponseType) {
  if (type === 'fixed_success' || type === 'custom_json') return defaultCallerBody();
  if (type === 'custom_xml') return '<Response><Success>true</Success></Response>';
  if (type === 'custom_raw') return 'accepted';
  return null;
}
