import type { ODataObjectKeyType } from '../types';

interface KeyTypeSelectProps { value: ODataObjectKeyType; onChange: (value: ODataObjectKeyType) => void }

export function KeyTypeSelect({ value, onChange }: KeyTypeSelectProps) {
  return (
    <label className="field-label">Тип ключа
      <select value={value} onChange={(event) => onChange(event.target.value as ODataObjectKeyType)}>
        <option value="guid">GUID</option>
        <option value="string">string</option>
        <option value="number">number</option>
        <option value="raw">raw</option>
      </select>
      <small>Для документов 1С почти всегда нужен GUID: `guid'{'{{order.Ref_Key}}'}'`.</small>
    </label>
  );
}
