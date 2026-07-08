import { CodeEditor } from '../../../components/CodeEditor';
import { CodeBlock } from '../../../components/CodeBlock';
import { EndpointHeadersEditor } from './EndpointHeadersEditor';
import type { FinalActionConfig, FinalActionReturnType } from '../types';

interface CallerResponseConfigProps {
  action: FinalActionConfig;
  onChange: (action: FinalActionConfig) => void;
}

const RETURN_OPTIONS: Array<{ value: FinalActionReturnType; label: string }> = [
  { value: 'fixed_success', label: 'Вернуть HTTP 200 {"ok": true}' },
  { value: 'proxy_response', label: 'Вернуть ответ внешнего endpoint' },
  { value: 'accepted_event', label: 'Вернуть accepted event_id/queue_item_id' },
  { value: 'custom_json', label: 'Вернуть свой JSON' },
  { value: 'custom_xml', label: 'Вернуть свой XML' },
  { value: 'custom_raw', label: 'Вернуть свой raw text' },
];

export function CallerResponseConfig({ action, onChange }: CallerResponseConfigProps) {
  const response = action.return_to_caller;
  const lockedProxy = action.type === 'send_and_return_response';
  const patch = (patchValue: Partial<typeof response>) => onChange({ ...action, return_to_caller: { ...response, ...patchValue } });

  return (
    <section className="panel stack-form final-action-config-card">
      <div className="panel-toolbar"><div><span className="eyebrow">Caller response</span><h3>Что вернуть вызывающей системе</h3><p className="microcopy">Это HTTP-ответ старому вызывающему сервису. Для DnP обычно оставляем HTTP 200 и JSON {"{\"ok\": true}"}.</p></div></div>
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
      {response.type === 'fixed_success' && !lockedProxy ? (
        <div className="status-card success">
          <strong>Будет возвращено вызывающей системе</strong>
          <CodeBlock code={JSON.stringify(response.body && typeof response.body === 'object' ? response.body : { ok: true }, null, 2)} language="json" showToolbar={false} />
          <span>Если нужен другой JSON, выберите режим “Вернуть свой JSON”.</span>
        </div>
      ) : null}
      {['custom_json', 'custom_xml', 'custom_raw'].includes(response.type) && !lockedProxy ? (
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
