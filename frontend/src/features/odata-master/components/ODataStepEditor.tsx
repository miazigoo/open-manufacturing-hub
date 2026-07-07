import { useState } from 'react';
import type { ODataQueryStep, ODataWizardStep } from '../types';
import { variableName } from '../utils/placeholders';
import { ODataFilterBuilder } from './ODataFilterBuilder';
import { ODataResourceBuilder } from './ODataResourceBuilder';
import { ODataSelectBuilder } from './ODataSelectBuilder';
import { PaginationControl } from './PaginationControl';

interface ODataStepEditorProps { connectionName: string; onAdd: (step: ODataWizardStep) => void }

export function ODataStepEditor({ connectionName, onAdd }: ODataStepEditorProps) {
  const [mode, setMode] = useState<'single' | 'object'>('single');
  const [step, setStep] = useState<ODataQueryStep>({ type: 'odata_query', connection: connectionName, resource: 'Document_ЗаказНаПроизводство2_2', filter: "Number eq '{{request.body.Number}}'", select: ['Ref_Key', 'Number', 'Date', 'Posted'], top: 1, orderby: '', paginate: false, required: true, save_as: 'order', name: 'Найти заказ производства' });
  const [objectFields, setObjectFields] = useState({ base_resource: 'Document_ЗаказНаПроизводство2_2', object_key: 'order.Ref_Key', tabular_part: 'Продукция' });

  function add() {
    const saveAs = variableName(step.save_as || step.resource, 'odata_result');
    if (mode === 'object') {
      onAdd({ type: 'odata_object_query', connection: connectionName || step.connection, base_resource: objectFields.base_resource, object_key: objectFields.object_key, tabular_part: objectFields.tabular_part, filter: step.filter || '', select: step.select, top: step.top, orderby: step.orderby || '', paginate: step.paginate, required: step.required, save_as: saveAs, name: step.name || 'Прочитать табличную часть' });
    } else {
      onAdd({ ...step, connection: connectionName || step.connection, save_as: saveAs });
    }
    setStep({ ...step, resource: '', filter: '', select: [], top: 100, save_as: 'result', name: '' });
  }

  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">OData-запрос</span>
          <h2>Что ищем в OData?</h2>
        </div>
        <div className="segmented-control">
          <button type="button" className={mode === 'single' ? 'active' : ''} onClick={() => setMode('single')}>Single query</button>
          <button type="button" className={mode === 'object' ? 'active' : ''} onClick={() => setMode('object')}>1C object/tabular</button>
          <button type="button" disabled>Foreach ниже</button>
        </div>
      </div>
      <div className="stack-form">
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">Название шага<input value={step.name || ''} onChange={(event) => setStep({ ...step, name: event.target.value })} /></label>
          <label className="field-label">Save as<input value={step.save_as} onChange={(event) => setStep({ ...step, save_as: variableName(event.target.value, 'result') })} /></label>
          <label className="field-label">Required<select value={String(step.required)} onChange={(event) => setStep({ ...step, required: event.target.value === 'true' })}><option value="true">Да, остановить flow если пусто</option><option value="false">Нет, можно продолжить</option></select></label>
        </div>
        {mode === 'single' ? (
          <label className="field-label">Resource<input value={step.resource} onChange={(event) => setStep({ ...step, resource: event.target.value })} placeholder="Document_ЗаказНаПроизводство2_2" /></label>
        ) : (
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Base resource<input value={objectFields.base_resource} onChange={(event) => setObjectFields({ ...objectFields, base_resource: event.target.value })} /></label>
            <label className="field-label">Object key<input value={objectFields.object_key} onChange={(event) => setObjectFields({ ...objectFields, object_key: event.target.value })} /></label>
            <label className="field-label">Tabular part<input value={objectFields.tabular_part} onChange={(event) => setObjectFields({ ...objectFields, tabular_part: event.target.value })} /></label>
          </div>
        )}
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">$top<input type="number" min={1} max={500} value={step.top || 100} onChange={(event) => setStep({ ...step, top: Number(event.target.value) })} /></label>
          <label className="field-label">$orderby<input value={step.orderby || ''} onChange={(event) => setStep({ ...step, orderby: event.target.value })} /></label>
        </div>
        <ODataSelectBuilder value={step.select} onChange={(select) => setStep({ ...step, select })} />
        <label className="field-label">$filter<input value={step.filter || ''} onChange={(event) => setStep({ ...step, filter: event.target.value })} placeholder="Number eq '{{request.body.Number}}'" /></label>
        <ODataFilterBuilder onUse={(filter) => setStep({ ...step, filter })} />
        <ODataResourceBuilder onUse={(resource) => { setStep({ ...step, resource }); setMode('single'); }} />
        <PaginationControl checked={step.paginate} top={step.top} onChange={(paginate) => setStep({ ...step, paginate })} />
        <button type="button" className="primary-button" onClick={add} disabled={!connectionName || (mode === 'single' && !step.resource.trim())}>Добавить OData-шаг</button>
      </div>
    </section>
  );
}
