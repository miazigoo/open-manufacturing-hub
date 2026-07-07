interface ODataResourceInputProps {
  value: string;
  resources: string[];
  loading: boolean;
  error?: unknown;
  onChange: (value: string) => void;
}

export function ODataResourceInput({ value, resources, loading, error, onChange }: ODataResourceInputProps) {
  const datalistId = 'integration-master-odata-resources';
  return (
    <label className="field-label">Resource
      <input list={datalistId} value={value} onChange={(event) => onChange(event.target.value)} placeholder="Document_ЗаказНаПроизводство2_2" />
      <datalist id={datalistId}>{resources.map((resource) => <option key={resource} value={resource} />)}</datalist>
      <small>{loading ? 'Читаю $metadata/resources...' : error ? 'Не удалось загрузить список ресурсов, можно ввести имя вручную.' : resources.length ? 'Выберите resource из metadata или введите вручную.' : 'Например: Catalog_Контрагенты или Document_ЗаказНаПроизводство2_2.'}</small>
    </label>
  );
}
