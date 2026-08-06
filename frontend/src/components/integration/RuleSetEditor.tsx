import { useMemo } from 'react';

interface RuleRow {
  name: string;
  op: string;
  path: string;
  value: string;
  actions: ActionRow[];
}

interface ActionRow {
  action: string;
  path: string;
  value: string;
  message: string;
  error_code: string;
}

interface RuleSetEditorProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

const CONDITION_OPS: Array<{ op: string; label: string; noValue?: boolean; noPath?: boolean; list?: boolean }> = [
  { op: 'always', label: 'всегда', noValue: true, noPath: true },
  { op: 'exists', label: 'поле существует', noValue: true },
  { op: 'not_exists', label: 'поля нет', noValue: true },
  { op: 'is_empty', label: 'поле пустое', noValue: true },
  { op: 'is_not_empty', label: 'поле не пустое', noValue: true },
  { op: 'eq', label: 'равно' },
  { op: 'ne', label: 'не равно' },
  { op: 'contains', label: 'содержит' },
  { op: 'not_contains', label: 'не содержит' },
  { op: 'starts_with', label: 'начинается с' },
  { op: 'ends_with', label: 'заканчивается на' },
  { op: 'in', label: 'в списке', list: true },
  { op: 'not_in', label: 'не в списке', list: true },
  { op: 'gt', label: 'больше' },
  { op: 'lt', label: 'меньше' },
  { op: 'ge', label: 'больше или равно' },
  { op: 'le', label: 'меньше или равно' },
  { op: 'regex', label: 'regex' },
];

const ACTIONS: Array<{ action: string; label: string; fields: Array<'path' | 'value' | 'message' | 'error_code'>; hints?: Record<string, string> }> = [
  { action: 'set_variable', label: 'Записать переменную', fields: ['path', 'value'], hints: { path: 'имя переменной', value: 'значение или {{шаблон}}' } },
  { action: 'set_payload', label: 'Записать поле payload', fields: ['path', 'value'], hints: { path: 'путь поля', value: 'значение' } },
  { action: 'set_target_system', label: 'Направить в систему', fields: ['value'], hints: { value: 'например DnP Service' } },
  { action: 'set_operation', label: 'Установить операцию', fields: ['value'], hints: { value: 'ключ операции' } },
  { action: 'set_route', label: 'Установить маршрут', fields: ['value'], hints: { value: 'имя маршрута' } },
  { action: 'skip_step', label: 'Пропустить шаг', fields: ['value'], hints: { value: 'id шага' } },
  { action: 'continue', label: 'Продолжить', fields: [] },
  { action: 'stop', label: 'Остановить цепочку', fields: [] },
  { action: 'mark_retry', label: 'Отправить на retry', fields: ['message', 'error_code'], hints: { message: 'пояснение', error_code: 'код ошибки' } },
  { action: 'fail', label: 'Завершить с ошибкой', fields: ['message', 'error_code'], hints: { message: 'текст ошибки', error_code: 'код ошибки' } },
];

function opFor(op: string) {
  return CONDITION_OPS.find((item) => item.op === op) ?? CONDITION_OPS[5];
}

function actionFor(action: string) {
  return ACTIONS.find((item) => item.action === action) ?? ACTIONS[0];
}

function toRows(value: Record<string, unknown>): { mode: string; rules: RuleRow[]; supported: boolean } {
  const mode = String(value.mode ?? 'first_match');
  const rawRules = Array.isArray(value.rules) ? value.rules : [];
  const rules: RuleRow[] = [];
  for (const raw of rawRules) {
    if (typeof raw !== 'object' || raw === null) return { mode, rules: [], supported: false };
    const record = raw as Record<string, unknown>;
    const condition = (record.if ?? {}) as Record<string, unknown>;
    const operator = opFor(String(condition.operator ?? 'eq'));
    let value = '';
    if (operator.list) value = Array.isArray(condition.value) ? condition.value.map(String).join(', ') : '';
    else if (condition.value !== undefined && condition.value !== null) value = String(condition.value);
    const actions: ActionRow[] = [];
    for (const rawAction of Array.isArray(record.then) ? record.then : []) {
      if (typeof rawAction !== 'object' || rawAction === null) return { mode, rules: [], supported: false };
      const action = rawAction as Record<string, unknown>;
      actions.push({
        action: String(action.action ?? 'set_variable'),
        path: String(action.path ?? ''),
        value: action.value === undefined || action.value === null ? '' : String(action.value),
        message: String(action.message ?? ''),
        error_code: String(action.error_code ?? ''),
      });
    }
    rules.push({ name: String(record.name ?? ''), op: operator.op, path: String(condition.path ?? ''), value, actions });
  }
  return { mode, rules, supported: true };
}

function toJson(mode: string, rules: RuleRow[]): Record<string, unknown> {
  return {
    mode,
    rules: rules.map((rule) => {
      const operator = opFor(rule.op);
      const condition: Record<string, unknown> = { operator: operator.op };
      if (!operator.noPath) condition.path = rule.path.trim();
      if (!operator.noValue) condition.value = operator.list ? rule.value.split(',').map((item) => item.trim()).filter(Boolean) : numericOrText(rule.value, operator.op);
      return {
        name: rule.name.trim() || 'Правило',
        if: condition,
        then: rule.actions.map((row) => {
          const action: Record<string, unknown> = { action: row.action };
          const meta = actionFor(row.action);
          if (meta.fields.includes('path') && row.path.trim()) action.path = row.path.trim();
          if (meta.fields.includes('value') && row.value !== '') action.value = row.value;
          if (meta.fields.includes('message') && row.message) action.message = row.message;
          if (meta.fields.includes('error_code') && row.error_code) action.error_code = row.error_code;
          return action;
        }),
      };
    }),
  };
}

function numericOrText(value: string, op: string) {
  if (['gt', 'lt', 'ge', 'le'].includes(op) && value.trim() !== '' && !Number.isNaN(Number(value))) return Number(value);
  return value;
}

const emptyRule = (): RuleRow => ({ name: '', op: 'eq', path: 'request.body.pool_type', value: '', actions: [{ action: 'set_variable', path: '', value: '', message: '', error_code: '' }] });

export function RuleSetEditor({ value, onChange }: RuleSetEditorProps) {
  const parsed = useMemo(() => toRows(value), [value]);
  const emit = (mode: string, rules: RuleRow[]) => onChange(toJson(mode, rules));
  const updateRule = (index: number, patch: Partial<RuleRow>) => emit(parsed.mode, parsed.rules.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)));

  if (!parsed.supported) {
    return (
      <div className="info-panel">
        <p className="microcopy">Этот набор правил содержит конструкции, которые визуальный редактор не поддерживает. Отредактируйте его как JSON.</p>
        <pre className="code-block small-code">{JSON.stringify(value, null, 2)}</pre>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <label className="field-label">
        Режим набора
        <select value={parsed.mode} onChange={(event) => emit(event.target.value, parsed.rules)}>
          <option value="first_match">Первое совпавшее правило</option>
          <option value="all">Все совпавшие правила по очереди</option>
        </select>
      </label>
      {parsed.rules.map((rule, index) => {
        const operator = opFor(rule.op);
        return (
          <section className="info-panel" key={index}>
            <div className="section-title-row">
              <label className="field-label no-margin">Имя правила<input value={rule.name} onChange={(event) => updateRule(index, { name: event.target.value })} placeholder={`Правило ${index + 1}`} /></label>
              <button type="button" className="ghost-button danger" onClick={() => emit(parsed.mode, parsed.rules.filter((_, i) => i !== index))}>Удалить</button>
            </div>
            <div className="action-row wrap-actions condition-row">
              <select value={rule.op} onChange={(event) => updateRule(index, { op: event.target.value })} title="Оператор условия">
                {CONDITION_OPS.map((item) => <option key={item.op} value={item.op}>{item.label}</option>)}
              </select>
              {!operator.noPath && <input value={rule.path} onChange={(event) => updateRule(index, { path: event.target.value })} placeholder="request.body.pool_type" title="Путь к полю: request.body.*, variables.*, steps.*" />}
              {!operator.noValue && <input value={rule.value} onChange={(event) => updateRule(index, { value: event.target.value })} placeholder={operator.list ? 'A, B, C' : 'значение'} title={operator.list ? 'Значения через запятую' : 'Значение или {{шаблон}}'} />}
            </div>
            {rule.actions.map((row, actionIndex) => {
              const meta = actionFor(row.action);
              return (
                <div className="action-row wrap-actions condition-row" key={actionIndex}>
                  <select value={row.action} onChange={(event) => updateRule(index, { actions: rule.actions.map((item, i) => (i === actionIndex ? { ...item, action: event.target.value } : item)) })} title="Действие">
                    {ACTIONS.map((item) => <option key={item.action} value={item.action}>{item.label}</option>)}
                  </select>
                  {meta.fields.includes('path') && <input value={row.path} onChange={(event) => updateRule(index, { actions: rule.actions.map((item, i) => (i === actionIndex ? { ...item, path: event.target.value } : item)) })} placeholder={meta.hints?.path ?? 'путь'} title={meta.hints?.path} />}
                  {meta.fields.includes('value') && <input value={row.value} onChange={(event) => updateRule(index, { actions: rule.actions.map((item, i) => (i === actionIndex ? { ...item, value: event.target.value } : item)) })} placeholder={meta.hints?.value ?? 'значение'} title={meta.hints?.value} />}
                  {meta.fields.includes('message') && <input value={row.message} onChange={(event) => updateRule(index, { actions: rule.actions.map((item, i) => (i === actionIndex ? { ...item, message: event.target.value } : item)) })} placeholder={meta.hints?.message ?? 'сообщение'} title={meta.hints?.message} />}
                  {meta.fields.includes('error_code') && <input value={row.error_code} onChange={(event) => updateRule(index, { actions: rule.actions.map((item, i) => (i === actionIndex ? { ...item, error_code: event.target.value } : item)) })} placeholder={meta.hints?.error_code ?? 'код'} title={meta.hints?.error_code} style={{ maxWidth: 160 }} />}
                  <button type="button" className="ghost-button danger" onClick={() => updateRule(index, { actions: rule.actions.filter((_, i) => i !== actionIndex) })} disabled={rule.actions.length === 1} title="Удалить действие">✕</button>
                </div>
              );
            })}
            <div className="action-row">
              <button type="button" className="ghost-button" onClick={() => updateRule(index, { actions: [...rule.actions, { action: 'set_variable', path: '', value: '', message: '', error_code: '' }] })}>Добавить действие</button>
            </div>
          </section>
        );
      })}
      <div className="action-row">
        <button type="button" className="ghost-button" onClick={() => emit(parsed.mode, [...parsed.rules, emptyRule()])}>Добавить правило</button>
      </div>
      {parsed.rules.length === 0 && <p className="microcopy">Без правил набор ничего не делает.</p>}
    </div>
  );
}
