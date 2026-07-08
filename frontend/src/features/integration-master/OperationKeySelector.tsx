import { JsonBlock } from '../../components/JsonBlock';
import type { InputContractField, InputOperationKey, OperationKeySuggestion } from './types';

interface OperationKeySelectorProps {
  value: InputOperationKey;
  suggestions: OperationKeySuggestion[];
  fields: InputContractField[];
  onChange: (value: InputOperationKey) => void;
}

export function OperationKeySelector({ value, suggestions, fields, onChange }: OperationKeySelectorProps) {
  function selectSuggestion(suggestion: OperationKeySuggestion) {
    onChange({ type: suggestion.type, field_path: suggestion.field_path ?? null, value: suggestion.value ?? null, fallback_paths: suggestion.fallback_paths, matcher_preview: suggestion.matcher_json });
  }

  const selectedField = fields.find((field) => field.path === value.field_path);

  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin">
        {suggestions.map((suggestion) => (
          <button key={`${suggestion.type}-${suggestion.field_path ?? suggestion.label}`} type="button" className={`builder-help-card ${value.type === suggestion.type && value.field_path === (suggestion.field_path ?? null) ? 'active' : ''}`} onClick={() => selectSuggestion(suggestion)}>
            <strong>{suggestion.label}</strong>
            <span>{suggestion.human_text}</span>
          </button>
        ))}
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Поле ключа маршрута<select value={value.field_path ?? ''} disabled={value.type !== 'field'} onChange={(event) => {
          const field = fields.find((item) => item.path === event.target.value);
          onChange({ type: 'field', field_path: event.target.value, value: field?.example ?? '', fallback_paths: [], matcher_preview: {} });
        }}><option value="">Выберите поле</option>{fields.map((field) => <option key={field.path} value={field.path}>{field.name} · {field.path}</option>)}</select></label>
        <label className="field-label">Значение<input value={value.value == null ? '' : String(value.value)} disabled={value.type !== 'field'} onChange={(event) => onChange({ ...value, value: event.target.value })} placeholder={selectedField ? String(selectedField.example ?? '') : 'operation value'} /></label>
        <label className="field-label">Если поле не пришло, проверить ещё<small>Запасные поля для route key. Например: сначала sinc, а если его нет — operation.</small><input value={value.fallback_paths.join(', ')} disabled={value.type !== 'field'} onChange={(event) => onChange({ ...value, fallback_paths: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="request.body.operation" /></label>
      </div>
      <details className="variable-card"><summary><span>Advanced matcher JSON</span><strong>JSON</strong></summary><JsonBlock value={value.matcher_preview} title="Matcher preview" searchable={false} /></details>
    </div>
  );
}
