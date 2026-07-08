import type { BusinessKeySuggestion, InputBusinessKey, InputContractField } from './types';

interface BusinessKeySelectorProps {
  value: InputBusinessKey;
  suggestions: BusinessKeySuggestion[];
  fields: InputContractField[];
  onChange: (value: InputBusinessKey) => void;
}

export function BusinessKeySelector({ value, suggestions, fields, onChange }: BusinessKeySelectorProps) {
  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin">
        {suggestions.map((suggestion) => (
          <button key={suggestion.path} type="button" className={`builder-help-card ${value.path === suggestion.path ? 'active' : ''}`} onClick={() => onChange({ path: suggestion.path, fallback_paths: suggestion.fallback_paths })}>
            <strong>{suggestion.field_name}</strong>
            <span>{suggestion.label}</span>
            {suggestion.fallback_paths.length ? <small>Запасные поля: {suggestion.fallback_paths.join(', ')}</small> : null}
          </button>
        ))}
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Business key<select value={value.path ?? ''} onChange={(event) => onChange({ ...value, path: event.target.value || null })}><option value="">Не выбран</option>{fields.map((field) => <option key={field.path} value={field.path}>{field.name} · {field.path}</option>)}</select></label>
        <label className="field-label">Если business key пустой, взять из<small>OMH покажет первое найденное значение в журнале событий и Timeline.</small><input value={value.fallback_paths.join(', ')} onChange={(event) => onChange({ ...value, fallback_paths: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="request.body.Number" /></label>
        <span className="success-note">Зачем это нужно<span>Бизнес-ключ будет виден в журнале событий и Timeline. По нему проще найти конкретный запрос.</span></span>
      </div>
    </div>
  );
}
