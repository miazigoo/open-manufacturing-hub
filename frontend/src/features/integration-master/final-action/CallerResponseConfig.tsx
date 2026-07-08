import { CodeEditor } from '../../../components/CodeEditor';
import { EndpointHeadersEditor } from './EndpointHeadersEditor';
import type { FinalActionConfig, FinalActionReturnType } from '../types';

interface CallerResponseConfigProps {
  action: FinalActionConfig;
  onChange: (action: FinalActionConfig) => void;
}

const RETURN_OPTIONS: Array<{ value: FinalActionReturnType; label: string }> = [
  { value: 'fixed_success', label: 'Fixed success {ok:true}' },
  { value: 'proxy_response', label: 'Proxy endpoint response' },
  { value: 'accepted_event', label: 'Accepted event_id/queue_item_id' },
  { value: 'custom_json', label: 'Custom JSON' },
  { value: 'custom_xml', label: 'Custom XML' },
  { value: 'custom_raw', label: 'Custom raw text' },
];

export function CallerResponseConfig({ action, onChange }: CallerResponseConfigProps) {
  const response = action.return_to_caller;
  const lockedProxy = action.type === 'send_and_return_response';
  const patch = (patchValue: Partial<typeof response>) => onChange({ ...action, return_to_caller: { ...response, ...patchValue } });

  return (
    <section className="panel stack-form final-action-config-card">
      <div className="panel-toolbar"><div><span className="eyebrow">Caller return</span><h3>Что вернуть вызывающей системе</h3><p className="microcopy">Для shortcut `send_and_return_response` ответ всегда проксируется из endpoint.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Return mode
          <select value={lockedProxy ? 'proxy_response' : response.type} disabled={lockedProxy} onChange={(event) => patch({ type: event.target.value as FinalActionReturnType })}>
            {RETURN_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="field-label">HTTP status
          <input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patch({ status_code: Number(event.target.value) || 200 })} />
        </label>
      </div>
      {['fixed_success', 'custom_json', 'custom_xml', 'custom_raw'].includes(response.type) && !lockedProxy ? (
        <label className="field-label full-span">Caller response body
          <CodeEditor
            value={typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? {}, null, 2)}
            onChange={(value) => patch({ body: value })}
            language={response.type === 'custom_xml' ? 'xml' : response.type === 'custom_raw' ? 'text' : 'json'}
            minRows={6}
          />
          <small>Для custom JSON можно использовать placeholders: {`{{target_payload.payload.order_id}}`}.</small>
        </label>
      ) : null}
      <EndpointHeadersEditor value={response.headers ?? {}} onChange={(headers) => patch({ headers })} label="Caller response headers" />
    </section>
  );
}
