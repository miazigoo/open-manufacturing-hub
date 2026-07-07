interface PreviousVariablesPanelProps {
  variables: Record<string, unknown>;
  onUseVariable: (name: string) => void;
  onUseField: (name: string, field: string) => void;
}

export function PreviousVariablesPanel({ variables, onUseVariable, onUseField }: PreviousVariablesPanelProps) {
  const entries = Object.entries(variables);
  if (!entries.length) {
    return <div className="empty-state compact"><h3>Нет результатов предыдущих шагов</h3><p>Сначала выполните и сохраните OData Query Step 2A. Для rendered preview желательно нажать Test query, чтобы OMH получил sample значения.</p></div>;
  }

  return (
    <section className="panel stack-form previous-variable-panel">
      <div><span className="eyebrow">Previous variables</span><h3>Доступные результаты предыдущих шагов</h3><p className="microcopy">Выберите объект и поле ссылки 1С. Для табличной части обычно нужен `Ref_Key`.</p></div>
      <div className="previous-variable-tree">
        {entries.map(([name, value]) => (
          <div className="previous-variable-card" key={name}>
            <div className="previous-variable-head"><strong>{name}</strong><span>{valueType(value)}</span><div className="action-row"><button type="button" className="ghost-button" onClick={() => onUseVariable(name)}>Использовать</button><button type="button" className="ghost-button" onClick={() => copy(name)}>Копировать</button></div></div>
            {isRecord(value) ? Object.entries(value).map(([field, fieldValue]) => (
              <div className="previous-variable-row" key={field}>
                <code>{name}.{field}</code><span>{formatValue(fieldValue)}</span><div className="action-row"><button type="button" className="ghost-button" onClick={() => onUseField(name, field)}>Использовать</button><button type="button" className="ghost-button" onClick={() => copy(`${name}.${field}`)}>Копировать</button></div>
              </div>
            )) : Array.isArray(value) ? <p className="microcopy">Это массив. Для массива нужен будущий foreach OData step.</p> : <p className="microcopy">Значение не является объектом 1С.</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function valueType(value: unknown) {
  if (Array.isArray(value)) return 'array';
  if (isRecord(value)) return 'object';
  return typeof value;
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'нет sample value';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function copy(value: string) {
  void navigator.clipboard?.writeText(value);
}
