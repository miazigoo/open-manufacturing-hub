import type { JsonPayloadFieldConfig, JsonPayloadValueType } from '../types';

interface JsonFieldTableBuilderProps {
  fields: JsonPayloadFieldConfig[];
  onChange: (fields: JsonPayloadFieldConfig[]) => void;
}

const VALUE_TYPES: JsonPayloadValueType[] = ['variable', 'template_string', 'constant_string', 'constant_number', 'constant_boolean', 'constant_null', 'object', 'array'];

export function JsonFieldTableBuilder({ fields, onChange }: JsonFieldTableBuilderProps) {
  function patch(index: number, patchValue: Partial<JsonPayloadFieldConfig>) {
    onChange(fields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, ...patchValue } : field)));
  }

  function remove(index: number) {
    onChange(fields.filter((_, fieldIndex) => fieldIndex !== index));
  }

  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">JSON table</span><h3>Поля JSON</h3><p className="microcopy">Target path создаёт вложенные объекты через точку, например `omh.run_id`.</p></div><button type="button" className="secondary-button" onClick={() => onChange([...fields, { target_path: '', value_source: '', value_type: 'variable' }])}>Добавить поле</button></div>
      <div className="table-card">
        <table className="data-table compact-table">
          <thead><tr><th>Target path</th><th>Value source</th><th>Type</th><th>Preview</th><th /></tr></thead>
          <tbody>
            {fields.map((field, index) => (
              <tr key={`${index}-${field.target_path}`}>
                <td><input value={field.target_path} onChange={(event) => patch(index, { target_path: event.target.value })} placeholder="payload.rows" /></td>
                <td><input value={String(field.value_source ?? '')} onChange={(event) => patch(index, { value_source: event.target.value })} placeholder="codes" /></td>
                <td><select value={field.value_type} onChange={(event) => patch(index, { value_type: event.target.value as JsonPayloadValueType })}>{VALUE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select></td>
                <td><code>{preview(field)}</code></td>
                <td><button type="button" className="link-button danger" onClick={() => remove(index)}>remove</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function preview(field: JsonPayloadFieldConfig) {
  if (field.value_type === 'variable' || field.value_type === 'array' || field.value_type === 'object') return `{{${field.value_source ?? ''}}}`;
  return String(field.value_source ?? '');
}
