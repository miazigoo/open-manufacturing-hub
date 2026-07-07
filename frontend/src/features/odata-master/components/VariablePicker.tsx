import { placeholder } from '../utils/placeholders';
import type { VariableGroup } from '../hooks/useODataVariables';

interface VariablePickerProps {
  groups: VariableGroup[];
  onInsert?: (value: string) => void;
}

export function VariablePicker({ groups, onInsert }: VariablePickerProps) {
  return (
    <div className="builder-help-card">
      <strong>Переменные</strong>
      <span>Используйте переменные во `$filter`, resource, JSON/XML/raw payload. Для GUID вставляйте переменную через кнопку GUID.</span>
      <div className="variable-card-list">
        {groups.map((group) => (
          <details className="variable-card" key={group.title} open={group.title.includes('Входящий') || group.title.includes('Контекст')}>
            <summary><span>{group.title}</span><strong>{group.variables.length}</strong></summary>
            <div className="hint-chip-row">
              {group.variables.map((item) => (
                <span key={`${group.title}:${item}`} className="action-row wrap-actions">
                  <button type="button" className="hint-chip" onClick={() => onInsert?.(placeholder(item))}>String: {item}</button>
                  <button type="button" className="hint-chip" onClick={() => onInsert?.(`guid'${placeholder(item)}'`)}>GUID</button>
                  <button type="button" className="hint-chip" onClick={() => onInsert?.(placeholder(item).replace(/^'|'$/g, ''))}>Raw</button>
                  <button type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(placeholder(item))}>Copy</button>
                </span>
              ))}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
