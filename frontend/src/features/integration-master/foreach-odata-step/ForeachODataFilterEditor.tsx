import { CodeEditor } from '../../../components/CodeEditor';
import type { ForeachODataStepConfig } from '../types';

interface ForeachODataFilterEditorProps {
  step: ForeachODataStepConfig;
  variables: Record<string, unknown>;
  onChange: (patch: Partial<ForeachODataStepConfig>) => void;
}

export function ForeachODataFilterEditor({ step, variables, onChange }: ForeachODataFilterEditorProps) {
  const item = firstArrayItem(variables[step.items]);
  const itemFields = item ? Object.keys(item) : [];
  const objectFields = Object.entries(variables).filter(([, value]) => isRecord(value));

  function insert(text: string) {
    const prefix = step.filter?.trim() ? `${step.filter} ` : '';
    onChange({ filter: `${prefix}${text}` });
  }

  return (
    <section className="panel stack-form foreach-filter-editor">
      <div><span className="eyebrow">Foreach OData filter</span><h3>OData-запрос для каждой строки</h3><p className="microcopy">Внутри цикла доступна локальная переменная <code>{step.item_as || 'product'}</code> и все предыдущие переменные, например <code>order.Ref_Key</code>.</p></div>
      <label className="field-label">$filter<CodeEditor value={step.filter ?? ''} onChange={(filter) => onChange({ filter })} language="odata" minRows={4} placeholder="Номенклатура_Key eq guid'{{product.Номенклатура_Key}}'" /></label>
      <div className="action-row wrap-actions">
        <button type="button" className="ghost-button" onClick={() => insert(`Номенклатура_Key eq guid'{{${step.item_as || 'product'}.Номенклатура_Key}}'`)}>+ Номенклатура_Key</button>
        <button type="button" className="ghost-button" onClick={() => insert("and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')")}>+ ДокументОснование</button>
      </div>
      {itemFields.length ? <div className="variable-chip-row"><strong>Поля строки {step.items}[]</strong>{itemFields.map((field) => <button type="button" className="ghost-button compact" key={field} onClick={() => insert(`{{${step.item_as || 'product'}.${field}}}`)}>{step.item_as || 'product'}.{field}</button>)}</div> : null}
      {objectFields.length ? <div className="variable-chip-row"><strong>Объекты предыдущих шагов</strong>{objectFields.flatMap(([name, value]) => Object.keys(value as Record<string, unknown>).map((field) => <button type="button" className="ghost-button compact" key={`${name}.${field}`} onClick={() => insert(`{{${name}.${field}}}`)}>{name}.{field}</button>))}</div> : null}
    </section>
  );
}

function firstArrayItem(value: unknown): Record<string, unknown> | null {
  if (!Array.isArray(value)) return null;
  const first = value.find(isRecord);
  return first ?? null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
