import type { UIOption } from '../../api/ui';

interface ConnectorSelectProps {
  label: string;
  value: string;
  options: UIOption[];
  onChange: (value: string) => void;
  placeholder?: string;
}

export function ConnectorSelect({ label, value, options, onChange, placeholder = 'Select connector' }: ConnectorSelectProps) {
  return (
    <label className="field-label">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((option) => <option key={option.id} value={option.label}>{option.label}</option>)}
      </select>
    </label>
  );
}
