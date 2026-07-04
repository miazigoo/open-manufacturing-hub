import type { UIOption } from '../../api/ui';

interface OperationTemplateSelectProps {
  value: string;
  templates: UIOption[];
  onChange: (value: string, template?: UIOption) => void;
}

export function OperationTemplateSelect({ value, templates, onChange }: OperationTemplateSelectProps) {
  return (
    <label className="field-label">
      Operation template
      <select value={value} onChange={(event) => onChange(event.target.value, templates.find((item) => item.id === event.target.value))}>
        <option value="">Manual endpoint</option>
        {templates.map((template) => <option key={template.id} value={template.id}>{template.label}</option>)}
      </select>
    </label>
  );
}
