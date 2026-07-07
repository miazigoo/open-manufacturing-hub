import { CodeEditor } from '../../components/CodeEditor';
import type { InputMode } from './types';

interface SampleInputEditorProps { inputMode: InputMode; value: string; error?: string | null; onChange: (value: string) => void; onParse: () => void; parsing: boolean }

export function SampleInputEditor({ inputMode, value, error, onChange, onParse, parsing }: SampleInputEditorProps) {
  return (
    <div className="stack-form">
      <label className="field-label">Пример входящего запроса
        <CodeEditor value={value} onChange={onChange} language={inputMode === 'json' ? 'json' : inputMode === 'xml' ? 'xml' : 'text'} minRows={9} placeholder="Вставьте пример запроса, который будет приходить в OMH." />
      </label>
      {error ? <div className="error-state compact">{error}</div> : null}
      <div className="action-row wrap-actions">
        <button type="button" className="primary-button" onClick={onParse} disabled={parsing}>{parsing ? 'Разбираю...' : 'Разобрать поля'}</button>
        <span className="microcopy">Лимит sample: 256 KB. Form-data и file будут отдельным шагом позже.</span>
      </div>
    </div>
  );
}
