import { asJson } from '../../api/client';
import { CodeEditor } from '../CodeEditor';

interface JsonPayloadBuilderProps {
  value: string;
  onChange: (value: string) => void;
}

export function JsonPayloadBuilder({ value, onChange }: JsonPayloadBuilderProps) {
  const starter = { id: '{{request.body.id}}', contractor_uuid: '{{contractor.Ref_Key}}', product_uuid: '{{product.Ref_Key}}', lines: '{{request.body.lines}}' };
  return (
    <div className="integration-block json-payload-builder">
      <div className="panel-toolbar"><div><span className="eyebrow">Build JSON</span><h3>Target payload template</h3><p>Use only the fields you need from request and OData lookups. A full placeholder like {'{{request.body.lines}}'} preserves arrays/objects.</p></div><button type="button" className="ghost-button" onClick={() => onChange(asJson(starter))}>Use starter</button></div>
      <div className="builder-help-card">
        <strong>Common OData values</strong>
        <span>After an OData lookup saved as <code>contractor</code>, use <code>{'{{contractor.Ref_Key}}'}</code>, <code>{'{{contractor.Description}}'}</code>, or <code>{'{{steps.get_contractor.first.Ref_Key}}'}</code>. If top returns a list, use <code>{'{{steps.get_prices.items}}'}</code> or <code>{'{{prices[0].Price}}'}</code>.</span>
      </div>
      <label className="field-label">JSON template<CodeEditor value={value} onChange={onChange} language="json" minRows={9} title="This JSON is rendered after OData steps. Put only fields the target API or second OData query needs." /></label>
      <div className="hint-chip-row">
        {['{{request.body.inn}}', '{{contractor.Ref_Key}}', '{{product.Ref_Key}}', '{{steps.get_contractor.first.Description}}'].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)} title="Click to copy placeholder">{hint}</button>)}
      </div>
    </div>
  );
}
