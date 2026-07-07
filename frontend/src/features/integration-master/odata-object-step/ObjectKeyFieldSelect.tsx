interface ObjectKeyFieldSelectProps {
  variableName: string;
  variableValue: unknown;
  value: string;
  onChange: (value: string) => void;
}

export function ObjectKeyFieldSelect({ variableName, variableValue, value, onChange }: ObjectKeyFieldSelectProps) {
  const fields = typeof variableValue === 'object' && variableValue !== null && !Array.isArray(variableValue) ? Object.keys(variableValue as Record<string, unknown>) : [];
  const preview = fields.includes(value) ? (variableValue as Record<string, unknown>)[value] : undefined;
  return (
    <label className="field-label">Поле ссылки 1С
      <input list="object-key-fields" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Ref_Key" />
      <datalist id="object-key-fields">{fields.map((field) => <option key={field} value={field} />)}</datalist>
      <small>{variableName ? `${variableName}.${value || 'Ref_Key'} = ${formatPreview(preview)}` : 'Ref_Key — внутренняя ссылка/UUID объекта в 1С.'}</small>
    </label>
  );
}

function formatPreview(value: unknown) {
  if (value === null || value === undefined || value === '') return 'нет sample value';
  return typeof value === 'string' ? value : JSON.stringify(value);
}
