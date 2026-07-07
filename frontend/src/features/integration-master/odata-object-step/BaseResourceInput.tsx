interface BaseResourceInputProps {
  value: string;
  resources: string[];
  loading: boolean;
  error?: unknown;
  onChange: (value: string) => void;
}

export function BaseResourceInput({ value, resources, loading, error, onChange }: BaseResourceInputProps) {
  return (
    <label className="field-label">Базовый OData Resource
      <input list="object-base-resources" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Document_ЗаказНаПроизводство2_2" />
      <datalist id="object-base-resources">{resources.map((resource) => <option key={resource} value={resource} />)}</datalist>
      <small>{loading ? 'Читаю resources...' : error ? 'Не удалось загрузить resources, можно ввести вручную.' : 'Например: Document_ЗаказКлиента, Document_ЗаказНаПроизводство2_2, Catalog_Номенклатура.'}</small>
    </label>
  );
}
