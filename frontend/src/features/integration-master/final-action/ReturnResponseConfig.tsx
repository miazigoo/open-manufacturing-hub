import { EndpointHeadersEditor } from './EndpointHeadersEditor';
import type { FinalActionBodySource, FinalActionBodyType, FinalActionConfig } from '../types';

interface ReturnResponseConfigProps {
  action: FinalActionConfig;
  onChange: (action: FinalActionConfig) => void;
}

export function ReturnResponseConfig({ action, onChange }: ReturnResponseConfigProps) {
  const response = action.return_to_caller;
  const patch = (patchValue: Partial<FinalActionConfig>) => onChange({ ...action, ...patchValue });
  const patchResponse = (patchValue: Partial<typeof response>) => onChange({ ...action, return_to_caller: { ...response, ...patchValue } });

  return (
    <section className="panel stack-form final-action-config-card">
      <div className="panel-toolbar"><div><span className="eyebrow">Caller response</span><h3>Ответ вызывающей системе</h3><p className="microcopy">Настройте body, HTTP status и headers. Preview ничего не отправляет во внешние системы.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Body source
          <select value={action.body_source} onChange={(event) => patch({ body_source: event.target.value as FinalActionBodySource })}>
            <option value="target_payload">target_payload</option>
            <option value="custom">Custom body</option>
            <option value="none">No body</option>
          </select>
        </label>
        <label className="field-label">Response type
          <select value={action.body_type} onChange={(event) => patch({ body_type: event.target.value as FinalActionBodyType })}>
            <option value="json">JSON</option>
            <option value="xml">XML</option>
            <option value="raw_text">Raw text</option>
            <option value="form" disabled>Form, позже</option>
          </select>
        </label>
        <label className="field-label">HTTP status
          <input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patchResponse({ status_code: Number(event.target.value) || 200 })} />
        </label>
      </div>
      {action.body_source === 'custom' ? (
        <label className="field-label full-span">Custom body
          <textarea className="code-textarea" value={String(action.custom_body ?? '')} onChange={(event) => patch({ custom_body: event.target.value })} spellCheck={false} placeholder={action.body_type === 'xml' ? '<Response><Ok>true</Ok></Response>' : '{"ok": true}'} />
        </label>
      ) : null}
      <EndpointHeadersEditor value={response.headers ?? {}} onChange={(headers) => patchResponse({ headers })} label="Response headers" hint={'Например: {"Content-Type":"application/json"}.'} />
    </section>
  );
}
