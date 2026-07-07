import { useState } from 'react';
import type { ODataForeachStep, ODataWizardStep } from '../types';
import { variableName } from '../utils/placeholders';
import { ODataFilterBuilder } from './ODataFilterBuilder';
import { ODataSelectBuilder } from './ODataSelectBuilder';
import { PaginationControl } from './PaginationControl';

interface ODataForeachStepEditorProps { connectionName: string; steps: ODataWizardStep[]; onAdd: (step: ODataForeachStep) => void }

export function ODataForeachStepEditor({ connectionName, steps, onAdd }: ODataForeachStepEditorProps) {
  const defaultSource = steps.at(-1)?.save_as || 'products';
  const [step, setStep] = useState<ODataForeachStep>({ type: 'foreach_odata', items: defaultSource, item_as: 'product', connection: connectionName, resource: 'InformationRegister_ПулКодовМаркировкиСУЗ', filter: "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')", select: ['КодМаркировки', 'ПолныйКодМаркировки', 'GTIN', 'Номенклатура_Key', 'ДокументОснование'], top: 500, orderby: '', paginate: true, required: false, merge: 'flatten', save_as: 'codes', name: 'Найти коды по продукции' });

  function add() {
    onAdd({ ...step, connection: connectionName || step.connection, save_as: variableName(step.save_as, 'codes'), item_as: variableName(step.item_as, 'item') });
  }

  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Foreach OData</span>
          <h2>Повторить OData по массиву</h2>
          <p className="microcopy">Например: взять `products`, для каждой строки сделать запрос в регистр кодов и объединить все строки в `codes`.</p>
        </div>
      </div>
      <div className="stack-form">
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">Source array<select value={step.items} onChange={(event) => setStep({ ...step, items: event.target.value })}>{steps.map((item) => <option key={item.save_as} value={item.save_as}>{item.save_as}</option>)}<option value="products">products</option></select></label>
          <label className="field-label">Item name<input value={step.item_as} onChange={(event) => setStep({ ...step, item_as: variableName(event.target.value, 'item') })} /></label>
          <label className="field-label">Save merged result as<input value={step.save_as} onChange={(event) => setStep({ ...step, save_as: variableName(event.target.value, 'codes') })} /></label>
        </div>
        <label className="field-label">Nested resource<input value={step.resource} onChange={(event) => setStep({ ...step, resource: event.target.value })} /></label>
        <label className="field-label">Nested filter<input value={step.filter || ''} onChange={(event) => setStep({ ...step, filter: event.target.value })} /></label>
        <ODataFilterBuilder onUse={(filter) => setStep({ ...step, filter })} />
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">$top<input type="number" min={1} max={500} value={step.top || 500} onChange={(event) => setStep({ ...step, top: Number(event.target.value) })} /></label>
          <label className="field-label">Merge mode<select value={step.merge} onChange={(event) => setStep({ ...step, merge: event.target.value as ODataForeachStep['merge'] })}><option value="flatten">flatten all rows into one array</option><option value="grouped">keep grouped by item</option><option value="first">keep first per item</option></select></label>
        </div>
        <ODataSelectBuilder value={step.select} onChange={(select) => setStep({ ...step, select })} placeholder="КодМаркировки,ПолныйКодМаркировки,GTIN" />
        <PaginationControl checked={step.paginate} top={step.top} onChange={(paginate) => setStep({ ...step, paginate })} />
        <button type="button" className="primary-button" onClick={add} disabled={!connectionName || !step.items || !step.resource}>Добавить foreach OData</button>
      </div>
    </section>
  );
}
