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
  select?: string;
  orderby?: string;
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
  const resultPath = `{{${lookup.saveAs || 'lookup_result'}.Ref_Key}}`;
  const stepPath = `{{steps.${lookup.id || 'odata_step'}.first.Ref_Key}}`;
  return (
    <div className="integration-block odata-lookup-block">
      <div className="panel-toolbar"><div><span className="eyebrow">OData {index + 1}</span><h3>{lookup.name || 'Выборка OData'}</h3></div><button type="button" className="ghost-button danger" onClick={onRemove}>Remove</button></div>
      <div className="builder-help-card">
        <strong>Как работает эта выборка OData</strong>
        <span>1. OMH отправляет `$filter` в выбранный 1C Resource. 2. `$select` оставляет в JSON только нужные поля. 3. Первая найденная строка сохраняется как <code>{lookup.saveAs || 'lookup_result'}</code>, поэтому следующие шаги могут использовать <code>{resultPath}</code> или <code>{stepPath}</code>.</span>
      </div>
      <div className="form-grid form-grid-3">
        <label className="field-label">Step name<input value={lookup.name} onChange={(event) => onChange({ ...lookup, name: event.target.value })} title="Понятное имя шага, которое будет видно в Timeline." /></label>
        <ConnectorSelect label="OData Connection" value={lookup.connection} options={connectors} onChange={(value) => onChange({ ...lookup, connection: value })} placeholder="Select OData Connection" />
        <ODataResourceSelect value="" templates={templates} onChange={(_, template) => onChange({ ...lookup, resource: String(template?.meta.resource ?? lookup.resource), name: template?.label ?? lookup.name })} />
        <label className="field-label">Resource<input value={lookup.resource} onChange={(event) => onChange({ ...lookup, resource: event.target.value })} placeholder="Catalog_ContrAgents" title="Use the exact technical resource name from OData Master, not a guessed Russian UI name." /></label>
        <label className="field-label">Filter field<input value={lookup.field} onChange={(event) => onChange({ ...lookup, field: event.target.value })} placeholder="INN" title="OData field used in $filter. Check spelling in OData Master first." /></label>
        <label className="field-label">Operator<select value={lookup.operator} onChange={(event) => onChange({ ...lookup, operator: event.target.value })} title="eq is safest for exact keys. contains/startswith are useful for search-like scenarios."><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="endswith">endswith</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label>
        <label className="field-label">Value source<input value={lookup.value} onChange={(event) => onChange({ ...lookup, value: event.target.value })} placeholder="{{inn}}" title="Can read from request, previous variables or previous OData: {{request.body.inn}}, {{inn}}, {{contractor.Ref_Key}}." /></label>
        <label className="field-label">$select<input value={lookup.select ?? ''} onChange={(event) => onChange({ ...lookup, select: event.target.value })} placeholder="Ref_Key,Description,INN" title="Return only fields that the next steps need. This keeps artifacts smaller and OData faster." /></label>
        <label className="field-label">$orderby<input value={lookup.orderby ?? ''} onChange={(event) => onChange({ ...lookup, orderby: event.target.value })} placeholder="Date desc" title="Optional. Use when top=1 must pick the newest or oldest row deterministically." /></label>
        <label className="field-label">Save as<input value={lookup.saveAs} onChange={(event) => onChange({ ...lookup, saveAs: event.target.value })} title="Variable name for this lookup result. Example: contractor, product, price_row." /></label>
        <label className="check-row"><input type="checkbox" checked={lookup.required} onChange={(event) => onChange({ ...lookup, required: event.target.checked })} /> Required result / обязательно найти</label>
      </div>
      <div className="hint-chip-row">
        {['{{request.body.inn}}', '{{inn}}', resultPath, stepPath].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)} title="Click to copy placeholder">{hint}</button>)}
      </div>
    </div>
  );
}
