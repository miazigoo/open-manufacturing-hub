import type { ODataResponseSpec } from '../types';
import { PayloadBuilder } from './PayloadBuilder';

interface ResponseBuilderProps { value: ODataResponseSpec; onChange: (value: ODataResponseSpec) => void }

export function ResponseBuilder({ value, onChange }: ResponseBuilderProps) {
  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Как вернуть ответ вызывающему<select value={value.mode} onChange={(event) => onChange({ ...value, mode: event.target.value as ODataResponseSpec['mode'] })}><option value="sync_response">Вернуть настроенный ответ</option><option value="proxy_response">Вернуть ответ endpoint</option><option value="accepted_event">Асинхронно: вернуть accepted</option></select></label>
        <label className="check-row success-note"><input type="checkbox" checked={Boolean(value.return_target_response)} onChange={(event) => onChange({ ...value, return_target_response: event.target.checked })} /><strong>Вернуть target response</strong><span>Используйте после отправки на endpoint.</span></label>
      </div>
      {value.mode !== 'proxy_response' && !value.return_target_response && (
        <PayloadBuilder title="Response body" bodyType={value.body_type} value={value.body} onBodyTypeChange={(bodyType) => onChange({ ...value, body_type: bodyType, body: bodyType === 'json' ? { ok: true } : '' })} onChange={(body) => onChange({ ...value, body })} />
      )}
    </div>
  );
}
