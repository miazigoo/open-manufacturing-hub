import type { InputContractField, ODataFilterOperator, ODataFilterRule, ODataStepConfig, ODataValueType } from '../types';

interface ODataFilterBuilderProps {
  step: ODataStepConfig;
  fields: InputContractField[];
  onChange: (patch: Partial<ODataStepConfig>) => void;
}

const operators: ODataFilterOperator[] = ['eq', 'ne', 'contains', 'gt', 'lt', 'ge', 'le'];
const valueTypes: ODataValueType[] = ['variable', 'string', 'number', 'boolean', 'guid', 'raw'];

export function ODataFilterBuilder({ step, fields, onChange }: ODataFilterBuilderProps) {
  const rule = step.filter_rule ?? defaultRule(fields);

  function updateRule(patch: Partial<ODataFilterRule>) {
    onChange({ filter_rule: { ...rule, ...patch }, filter_mode: 'builder' });
  }

  function insertVariable(path: string) {
    if (step.filter_mode === 'raw') {
      const raw = step.filter ?? '';
      onChange({ filter: raw ? `${raw} {{${path}}}` : `{{${path}}}` });
      return;
    }
    updateRule({ value_type: 'variable', value: path });
  }

  return (
    <div className="odata-filter-builder stack-form">
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Filter mode<select value={step.filter_mode} onChange={(event) => onChange({ filter_mode: event.target.value as ODataStepConfig['filter_mode'] })}><option value="builder">Builder</option><option value="raw">Raw OData</option></select></label>
        <span className="success-note">Целевой фильтр<span><code>{step.filter_mode === 'raw' ? step.filter || 'нет фильтра' : compileFilter(rule)}</code></span></span>
      </div>

      {step.filter_mode === 'raw' ? (
        <label className="field-label">$filter<textarea value={step.filter ?? ''} onChange={(event) => onChange({ filter: event.target.value })} rows={3} placeholder="Number eq '{{request.body.Number}}'" /></label>
      ) : (
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">OData field<input value={rule.field} onChange={(event) => updateRule({ field: event.target.value })} placeholder="Number" /></label>
          <label className="field-label">Operator<select value={rule.operator} onChange={(event) => updateRule({ operator: event.target.value as ODataFilterOperator })}>{operators.map((operator) => <option key={operator} value={operator}>{operator}</option>)}</select></label>
          <label className="field-label">Value type<select value={rule.value_type} onChange={(event) => updateRule({ value_type: event.target.value as ODataValueType })}>{valueTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          <label className="field-label">Value<input value={rule.value == null ? '' : String(rule.value)} onChange={(event) => updateRule({ value: event.target.value })} placeholder="request.body.Number" /></label>
        </div>
      )}

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные из Input Contract</span><strong>{fields.length}</strong></summary>
        <div className="odata-variable-grid">
          {fields.map((field) => (
            <button type="button" key={field.path} className="builder-help-card" onClick={() => insertVariable(field.path)}>
              <strong>{field.name}</strong><span>{field.path}</span><small>{formatExample(field.example)}</small>
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}

function defaultRule(fields: InputContractField[]): ODataFilterRule {
  const numberField = fields.find((field) => field.name.toLowerCase() === 'number') ?? fields.find((field) => field.name.toLowerCase().includes('number')) ?? fields[0];
  return { field: 'Number', operator: 'eq', value_type: 'variable', value: numberField?.path ?? 'request.body.Number' };
}

function compileFilter(rule: ODataFilterRule) {
  const value = rule.value_type === 'variable' ? `'{{${String(rule.value || '').replace(/^{{|}}$/g, '')}}}'` : rule.value_type === 'string' ? `'${String(rule.value ?? '')}'` : String(rule.value ?? '');
  return rule.operator === 'contains' ? `contains(${rule.field || 'Field'}, ${value})` : `${rule.field || 'Field'} ${rule.operator} ${value}`;
}

function formatExample(value: unknown) {
  if (value === null || value === undefined) return 'нет примера';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}
