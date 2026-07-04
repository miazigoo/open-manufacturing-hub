import type { UIOption } from '../../api/ui';
import { ConnectorSelect } from './ConnectorSelect';
import { ODataResourceSelect } from './ODataResourceSelect';

export interface ODataLookupDraft {
  id: string;
  name: string;
  connection: string;
  resource: string;
  field: string;
  operator: string;
  value: string;
  saveAs: string;
  required: boolean;
}

interface ODataLookupBlockEditorProps {
  lookup: ODataLookupDraft;
  index: number;
  connectors: UIOption[];
  templates: UIOption[];
  onChange: (lookup: ODataLookupDraft) => void;
  onRemove: () => void;
}

export function ODataLookupBlockEditor({ lookup, index, connectors, templates, onChange, onRemove }: ODataLookupBlockEditorProps) {
  return (
    <div className="integration-block odata-lookup-block">
      <div className="panel-toolbar"><div><span className="eyebrow">OData {index + 1}</span><h3>{lookup.name || 'Lookup block'}</h3></div><button type="button" className="ghost-button danger" onClick={onRemove}>Remove</button></div>
      <div className="form-grid form-grid-3">
        <label className="field-label">Name<input value={lookup.name} onChange={(event) => onChange({ ...lookup, name: event.target.value })} /></label>
        <ConnectorSelect label="1C connector" value={lookup.connection} options={connectors} onChange={(value) => onChange({ ...lookup, connection: value })} />
        <ODataResourceSelect value="" templates={templates} onChange={(_, template) => onChange({ ...lookup, resource: String(template?.meta.resource ?? lookup.resource), name: template?.label ?? lookup.name })} />
        <label className="field-label">Resource<input value={lookup.resource} onChange={(event) => onChange({ ...lookup, resource: event.target.value })} placeholder="Catalog_ContrAgents" /></label>
        <label className="field-label">Field<input value={lookup.field} onChange={(event) => onChange({ ...lookup, field: event.target.value })} placeholder="INN" /></label>
        <label className="field-label">Operator<select value={lookup.operator} onChange={(event) => onChange({ ...lookup, operator: event.target.value })}><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="gt">gt</option><option value="lt">lt</option></select></label>
        <label className="field-label">Value source<input value={lookup.value} onChange={(event) => onChange({ ...lookup, value: event.target.value })} placeholder="{{inn}}" /></label>
        <label className="field-label">Save as<input value={lookup.saveAs} onChange={(event) => onChange({ ...lookup, saveAs: event.target.value })} /></label>
        <label className="check-row"><input type="checkbox" checked={lookup.required} onChange={(event) => onChange({ ...lookup, required: event.target.checked })} /> Required result</label>
      </div>
    </div>
  );
}
