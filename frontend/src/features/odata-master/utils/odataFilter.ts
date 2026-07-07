import { placeholder } from './placeholders';

export type ODataFilterValueMode = 'simple' | 'variable' | 'guid' | 'raw';

export interface ODataFilterCondition {
  field: string;
  operator: string;
  value: string;
  mode: ODataFilterValueMode;
}

export function compileFilterCondition(condition: ODataFilterCondition) {
  const field = condition.field.trim();
  const operator = condition.operator || 'eq';
  const value = condition.value.trim();
  if (!field || !value) return '';
  if (condition.mode === 'raw') return `${field} ${operator} ${value}`;
  if (condition.mode === 'guid') return `${field} ${operator} guid'${placeholder(value)}'`;
  if (condition.mode === 'variable') return `${field} ${operator} '${placeholder(value)}'`;
  if (value === 'true' || value === 'false' || /^-?\d+(\.\d+)?$/.test(value)) return `${field} ${operator} ${value}`;
  return `${field} ${operator} '${value.replaceAll("'", "''")}'`;
}

export function compileODataFilter(conditions: ODataFilterCondition[]) {
  return conditions.map(compileFilterCondition).filter(Boolean).join(' and ');
}
