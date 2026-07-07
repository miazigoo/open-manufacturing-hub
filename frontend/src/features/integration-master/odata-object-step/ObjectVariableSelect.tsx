interface ObjectVariableSelectProps {
  value: string;
  variables: Record<string, unknown>;
  onChange: (value: string) => void;
}

export function ObjectVariableSelect({ value, variables, onChange }: ObjectVariableSelectProps) {
  return (
    <label className="field-label">Какой объект 1С читать?
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Выберите объект</option>
        {Object.entries(variables).map(([name, variable]) => <option key={name} value={name}>{name} · {Array.isArray(variable) ? 'array' : typeof variable === 'object' && variable !== null ? 'object' : typeof variable}</option>)}
      </select>
      <small>Это результат предыдущего OData-запроса. Обычно документ или элемент справочника 1С.</small>
    </label>
  );
}
