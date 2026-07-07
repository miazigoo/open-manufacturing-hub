interface ItemNameInputProps {
  value: string;
  sourceArray: string;
  onChange: (value: string) => void;
}

export function ItemNameInput({ value, sourceArray, onChange }: ItemNameInputProps) {
  return (
    <label className="field-label">Как назвать одну строку массива?
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder="product" />
      <small>В filter используйте <code>{`{{${value || 'product'}.Номенклатура_Key}}`}</code>. Это локальная переменная одной строки {sourceArray || 'массива'}.</small>
    </label>
  );
}
