import type { UIOption } from '../../api/ui';

interface ODataResourceSelectProps {
  value: string;
  templates: UIOption[];
  onChange: (value: string, template?: UIOption) => void;
}

export function ODataResourceSelect({ value, templates, onChange }: ODataResourceSelectProps) {
  return (
    <label className="field-label">
      OData resource / lookup
      <select value={value} onChange={(event) => onChange(event.target.value, templates.find((item) => item.label === event.target.value || item.id === event.target.value))}>
        <option value="">Manual resource</option>
        {templates.map((template) => <option key={template.id} value={template.label}>{template.label}</option>)}
      </select>
    </label>
  );
}
