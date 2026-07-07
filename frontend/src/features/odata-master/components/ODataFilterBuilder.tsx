import { useMemo, useState } from 'react';
import { compileODataFilter, type ODataFilterCondition, type ODataFilterValueMode } from '../utils/odataFilter';

interface ODataFilterBuilderProps { onUse: (filter: string) => void }

const modes: Array<{ value: ODataFilterValueMode; label: string }> = [
  { value: 'simple', label: 'Simple value' },
  { value: 'variable', label: 'Variable' },
  { value: 'guid', label: 'GUID' },
  { value: 'raw', label: 'Raw OData expression' },
];

export function ODataFilterBuilder({ onUse }: ODataFilterBuilderProps) {
  const [conditions, setConditions] = useState<ODataFilterCondition[]>([{ field: 'Number', operator: 'eq', value: 'request.body.Number', mode: 'variable' }]);
  const compiled = useMemo(() => compileODataFilter(conditions), [conditions]);

  function patch(index: number, value: Partial<ODataFilterCondition>) {
    setConditions((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...value } : item));
  }

  return (
    <div className="odata-filter-builder">
      <div className="panel-toolbar compact-toolbar">
        <h3>OData Filter Builder v2</h3>
        <button type="button" className="ghost-button" onClick={() => setConditions([...conditions, { field: '', operator: 'eq', value: '', mode: 'simple' }])}>Добавить условие</button>
      </div>
      {conditions.map((condition, index) => (
        <div className="metadata-grid compact-grid no-margin" key={index}>
          <label className="field-label">Поле<input value={condition.field} onChange={(event) => patch(index, { field: event.target.value })} placeholder="Номенклатура_Key" /></label>
          <label className="field-label">Оператор<select value={condition.operator} onChange={(event) => patch(index, { operator: event.target.value })}><option value="eq">eq</option><option value="ne">ne</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label>
          <label className="field-label">Тип значения<select value={condition.mode} onChange={(event) => patch(index, { mode: event.target.value as ODataFilterValueMode })}>{modes.map((mode) => <option key={mode.value} value={mode.value}>{mode.label}</option>)}</select></label>
          <label className="field-label">Значение<input value={condition.value} onChange={(event) => patch(index, { value: event.target.value })} placeholder="order.Ref_Key" /></label>
          <button type="button" className="ghost-button danger" onClick={() => setConditions(conditions.filter((_, itemIndex) => itemIndex !== index))} disabled={conditions.length === 1}>Удалить</button>
        </div>
      ))}
      <div className="success-note">Compiled $filter<span>{compiled || 'Заполните поле и значение'}</span></div>
      <button type="button" className="ghost-button" onClick={() => onUse(compiled)} disabled={!compiled}>Use this filter</button>
    </div>
  );
}
