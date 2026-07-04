import { asJson } from '../../api/client';

interface JsonPayloadBuilderProps {
  value: string;
  onChange: (value: string) => void;
}

export function JsonPayloadBuilder({ value, onChange }: JsonPayloadBuilderProps) {
  return (
    <div className="integration-block json-payload-builder">
      <div className="panel-toolbar"><div><span className="eyebrow">Build JSON</span><h3>Target payload template</h3><p>Use placeholders like {'{{request.body.id}}'} or {'{{contractor.Ref_Key}}'}.</p></div><button type="button" className="ghost-button" onClick={() => onChange(asJson({ id: '{{request.body.id}}', contractor_uuid: '{{contractor.Ref_Key}}', lines: '{{request.body.lines}}' }))}>Use starter</button></div>
      <label className="field-label">JSON template<textarea value={value} onChange={(event) => onChange(event.target.value)} /></label>
    </div>
  );
}
