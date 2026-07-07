import type { ForeachODataMergeMode } from '../types';

interface MergeModeSelectProps {
  value: ForeachODataMergeMode;
  onChange: (value: ForeachODataMergeMode) => void;
}

const modes: Array<{ value: ForeachODataMergeMode; label: string; hint: string }> = [
  { value: 'flatten', label: 'Flatten: один общий массив', hint: 'Для codes[] в DnP. Все строки из всех запросов складываются в один массив.' },
  { value: 'group_by_item', label: 'Group by item', hint: 'Сохраняет привязку к исходной строке products[]. Удобно для диагностики.' },
  { value: 'first_per_item', label: 'First per item', hint: 'Берёт первую найденную строку для каждой строки массива.' },
];

export function MergeModeSelect({ value, onChange }: MergeModeSelectProps) {
  const selected = modes.find((mode) => mode.value === value);
  return (
    <label className="field-label">Как объединить результаты?
      <select value={value} onChange={(event) => onChange(event.target.value as ForeachODataMergeMode)}>
        {modes.map((mode) => <option key={mode.value} value={mode.value}>{mode.label}</option>)}
      </select>
      <small>{selected?.hint}</small>
    </label>
  );
}
