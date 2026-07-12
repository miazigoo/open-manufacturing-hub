import { CodeEditor } from '../../../components/CodeEditor';
import type { ForeachODataStepConfig } from '../../integration-master/types';

interface FindCodesStepProps {
  step: ForeachODataStepConfig;
  onChange: (patch: Partial<ForeachODataStepConfig>) => void;
}

export function FindCodesStep({ step, onChange }: FindCodesStepProps) {
  return (
    <section className="wizard-step integration-master-step dnp-codes-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Foreach OData</span>
          <h2>Как по каждой продукции найти коды ЧЗ</h2>
          <p>Для каждой строки <code>{step.items}[]</code> OMH выполнит OData-запрос в регистр кодов и объединит результат в <code>{step.save_as}</code>.</p>
        </div>
        <span className="status-card warning"><small>Важно</small><strong>$top ≤ 500 + pagination</strong></span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Source array<input value={step.items} onChange={(event) => onChange({ items: event.target.value })} /></label>
        <label className="field-label">Item name<input value={step.item_as} onChange={(event) => onChange({ item_as: event.target.value })} /></label>
        <label className="field-label full-span">Resource<input value={step.resource} onChange={(event) => onChange({ resource: event.target.value })} /></label>
        <label className="field-label">$top<input type="number" min={1} max={500} value={step.top ?? ''} onChange={(event) => onChange({ top: event.target.value ? Number(event.target.value) : null })} /><small>Для пула кодов обычно оставьте 500.</small></label>
        <label className="field-label">Merge mode<select value={step.merge} onChange={(event) => onChange({ merge: event.target.value as ForeachODataStepConfig['merge'] })}><option value="flatten">flatten</option><option value="group_by_item">group_by_item</option><option value="first_per_item">first_per_item</option></select></label>
        <label className="field-label">Save as<input value={step.save_as} onChange={(event) => onChange({ save_as: event.target.value })} /></label>
      </div>
      <label className="field-label">$filter<CodeEditor value={step.filter ?? ''} onChange={(filter) => onChange({ filter })} language="odata" minRows={4} /></label>
      <label className="field-label">Select fields<CodeEditor value={step.select.join(',')} onChange={(value) => onChange({ select: splitSelect(value) })} language="text" minRows={5} /></label>
      <div className="metadata-grid compact-grid no-margin">
        <label className="check-row odata-check"><input type="checkbox" checked={step.paginate} onChange={(event) => onChange({ paginate: event.target.checked })} /> Pagination enabled</label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Ошибка, если коды не найдены</label>
        <span className="builder-help-card"><strong>Friendly note</strong><span>Для пула кодов обычно может быть больше 500 строк. Оставьте $top = 500 и включите пагинацию.</span></span>
      </div>
    </section>
  );
}

function splitSelect(value: string) {
  return value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
}
