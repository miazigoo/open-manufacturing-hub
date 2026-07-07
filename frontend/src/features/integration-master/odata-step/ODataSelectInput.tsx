import type { ODataStepConfig } from '../types';

interface ODataSelectInputProps {
  step: ODataStepConfig;
  onChange: (patch: Partial<ODataStepConfig>) => void;
}

export function ODataSelectInput({ step, onChange }: ODataSelectInputProps) {
  return (
    <div className="metadata-grid compact-grid no-margin">
      <label className="field-label">$select<input value={step.select.join(', ')} onChange={(event) => onChange({ select: splitSelect(event.target.value) })} placeholder="Ref_Key, Number, Date, Posted" /><small>Минимально добавьте `Ref_Key`, если следующий шаг должен отправлять ссылку 1C.</small></label>
      <label className="field-label">$top<input type="number" min="1" max="500" value={step.top ?? ''} onChange={(event) => onChange({ top: event.target.value ? Number(event.target.value) : null })} /></label>
      <label className="field-label">$orderby<input value={step.orderby ?? ''} onChange={(event) => onChange({ orderby: event.target.value || null })} placeholder="Date desc" /></label>
      <label className="check-row odata-check"><input type="checkbox" checked={step.paginate} onChange={(event) => onChange({ paginate: event.target.checked })} /> Читать страницы OData</label>
    </div>
  );
}

function splitSelect(value: string) {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}
