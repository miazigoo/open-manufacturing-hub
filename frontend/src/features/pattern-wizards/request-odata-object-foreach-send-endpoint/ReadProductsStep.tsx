import type { ODataObjectStepConfig } from '../../integration-master/types';

interface ReadProductsStepProps {
  step: ODataObjectStepConfig;
  orderPreview: Record<string, unknown>;
  onChange: (patch: Partial<ODataObjectStepConfig>) => void;
}

export function ReadProductsStep({ step, orderPreview, onChange }: ReadProductsStepProps) {
  const template = `${step.base_resource}(guid'{{${step.object_variable}.${step.key_field || 'Ref_Key'}}}')/${step.nested_resource}`;
  const rendered = `${step.base_resource}(guid'${String(orderPreview.Ref_Key ?? '...')}')/${step.nested_resource}`;
  return (
    <section className="wizard-step integration-master-step dnp-products-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Read document rows</span>
          <h2>Как прочитать продукцию заказа</h2>
          <p>Шаг читает табличную часть <code>Продукция</code> найденного заказа. Результат сохраняется как массив <code>{step.save_as}</code>.</p>
        </div>
        <span className="status-card neutral"><small>Resource template</small><strong>{template}</strong></span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Object variable<input value={step.object_variable} onChange={(event) => onChange({ object_variable: event.target.value })} /></label>
        <label className="field-label">Key field<input value={step.key_field} onChange={(event) => onChange({ key_field: event.target.value })} /></label>
        <label className="field-label">Key type<select value={step.key_type} onChange={(event) => onChange({ key_type: event.target.value as ODataObjectStepConfig['key_type'] })}><option value="guid">GUID</option><option value="string">String</option><option value="number">Number</option><option value="raw">Raw</option></select></label>
        <label className="field-label full-span">Base resource<input value={step.base_resource} onChange={(event) => onChange({ base_resource: event.target.value })} /></label>
        <label className="field-label">Nested resource<input value={step.nested_resource} onChange={(event) => onChange({ nested_resource: event.target.value })} /></label>
        <label className="field-label">Save as<input value={step.save_as} onChange={(event) => onChange({ save_as: event.target.value })} /></label>
        <label className="field-label">$top<input type="number" min={1} max={500} value={step.top ?? ''} onChange={(event) => onChange({ top: event.target.value ? Number(event.target.value) : null })} /></label>
      </div>
      <label className="field-label">Select fields<input value={step.select.join(', ')} onChange={(event) => onChange({ select: splitSelect(event.target.value) })} /></label>
      <div className="metadata-grid compact-grid no-margin">
        <span className="success-note">Rendered resource<span><code>{rendered}</code></span></span>
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Ошибка, если строк нет</label>
      </div>
    </section>
  );
}

function splitSelect(value: string) {
  return value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
}
