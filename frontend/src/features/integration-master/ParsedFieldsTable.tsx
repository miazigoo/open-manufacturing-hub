import type { InputContractField } from './types';

interface ParsedFieldsTableProps {
  fields: InputContractField[];
  operationPath?: string | null;
  businessPath?: string | null;
  onChange: (fields: InputContractField[]) => void;
  onUseOperation: (field: InputContractField) => void;
  onUseBusiness: (field: InputContractField) => void;
}

export function ParsedFieldsTable({ fields, operationPath, businessPath, onChange, onUseOperation, onUseBusiness }: ParsedFieldsTableProps) {
  function patch(index: number, patchValue: Partial<InputContractField>) {
    onChange(fields.map((field, itemIndex) => itemIndex === index ? { ...field, ...patchValue } : field));
  }

  if (!fields.length) {
    return <div className="empty-state compact"><h3>Поля ещё не распознаны</h3><p>Вставьте sample и нажмите «Разобрать поля».</p></div>;
  }

  return (
    <section className="table-panel integration-fields-table">
      <div className="field-key-help">
        <span><strong>Route</strong> — поле, по которому OMH выбирает нужный сценарий.</span>
        <span><strong>Business</strong> — поле, по которому оператор потом найдёт запрос в журнале и Timeline.</span>
      </div>
      <table>
        <thead><tr><th>Поле</th><th>Путь</th><th>Тип</th><th>Пример</th><th>Обязательное</th><th>Описание</th><th>Ключи</th></tr></thead>
        <tbody>
          {fields.map((field, index) => (
            <tr key={`${field.path}-${index}`}>
              <td><strong>{field.name}</strong></td>
              <td><code>{field.display_path || field.path}</code></td>
              <td>{field.type}</td>
              <td><small>{formatExample(field.example)}</small></td>
              <td><label className="check-row compact-check"><input type="checkbox" checked={field.required} onChange={(event) => patch(index, { required: event.target.checked })} /> {field.required ? 'Required' : 'Optional'}</label></td>
              <td><input value={field.description ?? ''} onChange={(event) => patch(index, { description: event.target.value })} placeholder="Например: номер заказа в 1С" /></td>
              <td>
                <div className="action-row wrap-actions">
                  <button
                    type="button"
                    className={`${operationPath === field.path ? 'primary-link' : 'ghost-button'} tooltip-button`}
                    data-tooltip="Route key: OMH выберет этот сценарий, если входящий запрос содержит это поле с нужным значением. Обычно это operation или sinc."
                    aria-label={`Сделать ${field.name} route key`}
                    onClick={() => onUseOperation(field)}
                  >
                    Route
                  </button>
                  <button
                    type="button"
                    className={`${businessPath === field.path ? 'primary-link' : 'ghost-button'} tooltip-button`}
                    data-tooltip="Business key: значение попадёт в журнал событий и Timeline. Выбирайте номер заказа, ID заявки или другой понятный оператору идентификатор."
                    aria-label={`Сделать ${field.name} business key`}
                    onClick={() => onUseBusiness(field)}
                  >
                    Business
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function formatExample(value: unknown) {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return '—';
  return JSON.stringify(value);
}
