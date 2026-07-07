interface SourceArraySelectProps {
  value: string;
  variables: Record<string, unknown>;
  onChange: (value: string) => void;
}

export function SourceArraySelect({ value, variables, onChange }: SourceArraySelectProps) {
  const arrays = Object.entries(variables).filter(([, variable]) => Array.isArray(variable));
  return (
    <label className="field-label">По какому массиву пройти?
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Выберите массив</option>
        {arrays.map(([name, items]) => <option key={name} value={name}>{name} ({(items as unknown[]).length})</option>)}
      </select>
      <small>{value ? `OMH выполнит вложенный OData-запрос для каждой строки массива ${value}.` : 'Например: products после шага чтения табличной части.'}</small>
    </label>
  );
}
