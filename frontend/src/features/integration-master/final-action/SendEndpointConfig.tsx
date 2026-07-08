import { EndpointHeadersEditor } from './EndpointHeadersEditor';
import type { FinalActionBodySource, FinalActionBodyType, FinalActionConfig, FinalActionMethod } from '../types';

interface SendEndpointConfigProps {
  action: FinalActionConfig;
  onChange: (action: FinalActionConfig) => void;
}

export function SendEndpointConfig({ action, onChange }: SendEndpointConfigProps) {
  const patch = (patchValue: Partial<FinalActionConfig>) => onChange({ ...action, ...patchValue });

  return (
    <section className="panel stack-form final-action-config-card">
      <div className="panel-toolbar"><div><span className="eyebrow">Target endpoint</span><h3>Куда отправить результат</h3><p className="microcopy">URL может быть private/localhost для локальной проверки. Backend покажет предупреждение, но не заблокирует.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Method
          <select value={action.method} onChange={(event) => patch({ method: event.target.value as FinalActionMethod })}>
            {['POST', 'PUT', 'PATCH', 'DELETE', 'GET'].map((method) => <option key={method} value={method}>{method}</option>)}
          </select>
        </label>
        <label className="field-label full-span">URL
          <input value={action.url ?? ''} onChange={(event) => patch({ url: event.target.value })} placeholder="https://target.example/api/import" />
        </label>
        <label className="field-label">Body source
          <select value={action.body_source} onChange={(event) => patch({ body_source: event.target.value as FinalActionBodySource })}>
            <option value="target_payload">target_payload</option>
            <option value="custom">Custom body</option>
            <option value="none">No body</option>
          </select>
        </label>
        <label className="field-label">Body type
          <select value={action.body_type} onChange={(event) => patch({ body_type: event.target.value as FinalActionBodyType })}>
            <option value="json">JSON</option>
            <option value="xml">XML</option>
            <option value="raw_text">Raw text</option>
            <option value="form" disabled>Form, позже</option>
          </select>
        </label>
        <label className="field-label">Timeout, sec
          <input type="number" min={1} max={300} value={action.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 30 })} />
        </label>
      </div>
      {action.body_source === 'custom' ? (
        <label className="field-label full-span">Custom request body
          <textarea className="code-textarea" value={String(action.custom_body ?? '')} onChange={(event) => patch({ custom_body: event.target.value })} spellCheck={false} placeholder={action.body_type === 'xml' ? '<Request>{{target_payload}}</Request>' : '{"payload": "{{target_payload}}"}'} />
        </label>
      ) : null}
      <EndpointHeadersEditor value={action.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} />
    </section>
  );
}
