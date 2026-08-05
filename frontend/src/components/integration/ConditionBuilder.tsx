import { useMemo } from 'react';

export interface MatcherGroupValue {
  mode: 'all' | 'any' | 'none';
  rules: Array<Record<string, unknown>>;
}

interface ConditionRow {
  field: string;
  op: string;
  value: string;
}

interface ConditionBuilderProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  fieldPresets?: Array<{ label: string; path: string }>;
}

const OPERATORS: Array<{ op: string; type: string; label: string; list?: boolean; noValue?: boolean; pattern?: boolean }> = [
  { op: 'eq', type: 'body_path_equals', label: 'равно' },
  { op: 'ne', type: 'body_path_not_equals', label: 'не равно' },
  { op: 'contains', type: 'body_path_contains', label: 'содержит' },
  { op: 'not_contains', type: 'body_path_not_contains', label: 'не содержит' },
  { op: 'starts_with', type: 'body_path_starts_with', label: 'начинается с' },
  { op: 'ends_with', type: 'body_path_ends_with', label: 'заканчивается на' },
  { op: 'in', type: 'body_path_in', label: 'в списке', list: true },
  { op: 'not_in', type: 'body_path_not_in', label: 'не в списке', list: true },
  { op: 'gt', type: 'body_path_gt', label: 'больше' },
  { op: 'lt', type: 'body_path_lt', label: 'меньше' },
  { op: 'ge', type: 'body_path_ge', label: 'больше или равно' },
  { op: 'le', type: 'body_path_le', label: 'меньше или равно' },
  { op: 'regex', type: 'body_path_regex', label: 'regex', pattern: true },
  { op: 'exists', type: 'body_path_exists', label: 'поле существует', noValue: true },
];

const MODES: Array<{ mode: 'all' | 'any' | 'none'; label: string }> = [
  { mode: 'all', label: 'Все условия (И)' },
  { mode: 'any', label: 'Любое условие (ИЛИ)' },
  { mode: 'none', label: 'Ни одно условие (НЕ)' },
];

function opFor(type: string) {
  return OPERATORS.find((item) => item.type === type);
}

function toRows(group: Record<string, unknown>): { mode: 'all' | 'any' | 'none'; rows: ConditionRow[]; supported: boolean } {
  const mode = (group.mode as 'all' | 'any' | 'none') || 'all';
  const rules = Array.isArray(group.rules) ? group.rules : [];
  const rows: ConditionRow[] = [];
  for (const rule of rules) {
    if (typeof rule !== 'object' || rule === null) return { mode, rows: [], supported: false };
    const record = rule as Record<string, unknown>;
    const op = opFor(String(record.type || ''));
    if (!op) return { mode, rows: [], supported: false };
    let value = '';
    if (op.list) value = Array.isArray(record.values) ? record.values.map(String).join(', ') : '';
    else if (op.pattern) value = String(record.pattern ?? record.value ?? '');
    else value = record.value === undefined || record.value === null ? '' : String(record.value);
    rows.push({ field: String(record.path || ''), op: op.op, value });
  }
  return { mode, rows, supported: true };
}

function toGroup(mode: string, rows: ConditionRow[]): Record<string, unknown> {
  const rules = rows
    .filter((row) => row.field.trim())
    .map((row) => {
      const operator = OPERATORS.find((item) => item.op === row.op);
      if (!operator) return { type: 'always' };
      const rule: Record<string, unknown> = { type: operator.type, path: row.field.trim() };
      if (operator.noValue) return rule;
      if (operator.list) {
        rule.values = row.value.split(',').map((item) => item.trim()).filter(Boolean);
        return rule;
      }
      if (operator.pattern) {
        rule.pattern = row.value;
        return rule;
      }
      if (['gt', 'lt', 'ge', 'le'].includes(operator.op) && row.value.trim() !== '' && !Number.isNaN(Number(row.value))) {
        rule.value = Number(row.value);
        return rule;
      }
      rule.value = row.value;
      return rule;
    });
  return { mode, rules };
}

export function ConditionBuilder({ value, onChange, fieldPresets = [] }: ConditionBuilderProps) {
  const parsed = useMemo(() => toRows(value), [value]);

  const emit = (mode: string, rows: ConditionRow[]) => onChange(toGroup(mode, rows));
  const updateRow = (index: number, patch: Partial<ConditionRow>) => {
    const rows = parsed.rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row));
    emit(parsed.mode, rows);
  };

  if (!parsed.supported) {
    return (
      <div className="info-panel">
        <p className="microcopy">Это условие содержит конструкции, которые визуальный редактор не поддерживает (например вложенные группы). Отредактируйте его как JSON.</p>
        <pre className="code-block small-code">{JSON.stringify(value, null, 2)}</pre>
      </div>
    );
  }

  return (
    <div className="condition-builder">
      <label className="field-label">
        Логика группы
        <select value={parsed.mode} onChange={(event) => emit(event.target.value, parsed.rows)}>
          {MODES.map((item) => <option key={item.mode} value={item.mode}>{item.label}</option>)}
        </select>
      </label>
      {parsed.rows.map((row, index) => {
        const operator = OPERATORS.find((item) => item.op === row.op) ?? OPERATORS[0];
        const customField = row.field && !fieldPresets.some((preset) => preset.path === row.field);
        return (
          <div className="action-row wrap-actions condition-row" key={index}>
            {fieldPresets.length > 0 ? (
              <select
                value={customField ? '__custom' : row.field}
                onChange={(event) => updateRow(index, { field: event.target.value === '__custom' ? row.field : event.target.value })}
                title="Поле кода или документа"
              >
                {fieldPresets.map((preset) => <option key={preset.path} value={preset.path}>{preset.label}</option>)}
                <option value="__custom">Свой путь…</option>
              </select>
            ) : null}
            {(fieldPresets.length === 0 || customField) && (
              <input value={row.field} onChange={(event) => updateRow(index, { field: event.target.value })} placeholder="gtin" title="Путь к полю, например gtin или order_number" />
            )}
            <select value={row.op} onChange={(event) => updateRow(index, { op: event.target.value })} title="Оператор">
              {OPERATORS.map((item) => <option key={item.op} value={item.op}>{item.label}</option>)}
            </select>
            {!operator.noValue && (
              <input
                value={row.value}
                onChange={(event) => updateRow(index, { value: event.target.value })}
                placeholder={operator.list ? 'значение 1, значение 2' : operator.pattern ? 'регулярное выражение' : 'значение'}
                title={operator.list ? 'Список значений через запятую' : 'Значение для сравнения'}
              />
            )}
            <button type="button" className="ghost-button danger" onClick={() => emit(parsed.mode, parsed.rows.filter((_, rowIndex) => rowIndex !== index))} title="Удалить условие">✕</button>
          </div>
        );
      })}
      <div className="action-row">
        <button type="button" className="ghost-button" onClick={() => emit(parsed.mode, [...parsed.rows, { field: fieldPresets[0]?.path ?? '', op: 'eq', value: '' }])}>
          Добавить условие
        </button>
      </div>
      {parsed.rows.length === 0 && <p className="microcopy">Без условий правило срабатывает на каждый код.</p>}
    </div>
  );
}
