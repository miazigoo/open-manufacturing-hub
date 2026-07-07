interface NestedResourceInputProps { value: string; onChange: (value: string) => void }

const examples = ['Товары', 'Продукция', 'Материалы', 'Услуги'];

export function NestedResourceInput({ value, onChange }: NestedResourceInputProps) {
  return (
    <label className="field-label">Табличная часть / вложенный ресурс
      <input list="nested-resources" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Продукция" />
      <datalist id="nested-resources">{examples.map((item) => <option key={item} value={item} />)}</datalist>
      <small>В 1С документы часто имеют табличные части: Товары, Продукция, Материалы, Услуги.</small>
    </label>
  );
}
