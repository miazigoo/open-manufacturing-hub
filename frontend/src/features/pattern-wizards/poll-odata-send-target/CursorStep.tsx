import type { PollODataCursorConfig, PollODataCursorType, PollODataCursorUpdateWhen } from './types';

interface CursorStepProps {
  cursor: PollODataCursorConfig;
  saveAs: string;
  onChange: (value: PollODataCursorConfig) => void;
}

export function CursorStep({ cursor, saveAs, onChange }: CursorStepProps) {
  const patch = (value: Partial<PollODataCursorConfig>) => onChange({ ...cursor, ...value });
  return (
    <section className="wizard-step integration-master-step poll-cursor-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Cursor / watermark</span>
          <h2>Как OMH поймёт, что уже отправлял</h2>
          <p>Cursor нужен, чтобы OMH не отправлял одни и те же данные каждый запуск. Cursor обновляется только после успешного run.</p>
        </div>
        <span className="status-card neutral"><small>Current source</small><strong>{cursor.source_field || `${saveAs}[].Date`}</strong></span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Cursor type
          <select value={cursor.cursor_type} onChange={(event) => patch({ cursor_type: event.target.value as PollODataCursorType })}>
            <option value="last_success_at">last_success_at</option>
            <option value="field_max_value">field_max_value</option>
            <option value="manual">manual</option>
          </select>
          <small><code>last_success_at</code> использует timestamp успешного run. <code>field_max_value</code> берёт максимум по полю.</small>
        </label>
        <label className="field-label">Cursor source
          <input value={cursor.source_field} disabled={cursor.cursor_type !== 'field_max_value'} onChange={(event) => patch({ source_field: event.target.value })} placeholder={`${saveAs}[].Date`} />
        </label>
        <label className="field-label">Update cursor when
          <select value={cursor.update_when} onChange={(event) => patch({ update_when: event.target.value as PollODataCursorUpdateWhen })}>
            <option value="target_success">target_success</option>
            <option value="odata_success">odata_success</option>
            <option value="manual">manual</option>
          </select>
        </label>
      </div>
      <div className="pattern-flow compact">
        <span>cursor_before</span>
        <span>OData filter</span>
        <span>target success</span>
        <span>cursor_after</span>
      </div>
    </section>
  );
}
