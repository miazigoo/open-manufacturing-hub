import type { PayloadBodyType } from '../types';

interface PayloadTypeSelectorProps {
  value: PayloadBodyType;
  onChange: (value: PayloadBodyType) => void;
}

const OPTIONS: Array<{ value: PayloadBodyType; title: string; description: string }> = [
  { value: 'json', title: 'JSON', description: 'Объект или массив для внешнего сервиса.' },
  { value: 'xml', title: 'XML', description: 'XML-ответ или XML body с escaping.' },
  { value: 'raw_text', title: 'Raw text', description: 'Строка ответа или произвольный текст.' },
];

export function PayloadTypeSelector({ value, onChange }: PayloadTypeSelectorProps) {
  return (
    <div className="metadata-grid compact-grid no-margin request-action-cards">
      {OPTIONS.map((option) => (
        <button key={option.value} type="button" className={`builder-help-card action-card ${value === option.value ? 'active' : ''}`} onClick={() => onChange(option.value)}>
          <strong>{option.title}</strong>
          <span>{option.description}</span>
        </button>
      ))}
    </div>
  );
}
