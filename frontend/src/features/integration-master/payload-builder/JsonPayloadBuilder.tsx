import { DynamicObjectEntryEditor } from './DynamicObjectEntryEditor';
import { JsonFieldTableBuilder } from './JsonFieldTableBuilder';
import { JsonRawTemplateEditor } from './JsonRawTemplateEditor';
import type { JsonPayloadDynamicEntryConfig, JsonPayloadFieldConfig, JsonPayloadMode } from '../types';

interface JsonPayloadBuilderProps {
  mode: JsonPayloadMode;
  fields: JsonPayloadFieldConfig[];
  dynamicEntries: JsonPayloadDynamicEntryConfig[];
  rawTemplate: string;
  onModeChange: (mode: JsonPayloadMode) => void;
  onFieldsChange: (fields: JsonPayloadFieldConfig[]) => void;
  onDynamicEntriesChange: (entries: JsonPayloadDynamicEntryConfig[]) => void;
  onRawTemplateChange: (value: string) => void;
}

export function JsonPayloadBuilder({ mode, fields, dynamicEntries, rawTemplate, onModeChange, onFieldsChange, onDynamicEntriesChange, onRawTemplateChange }: JsonPayloadBuilderProps) {
  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin request-action-cards">
        <button type="button" className={`builder-help-card action-card ${mode === 'table' ? 'active' : ''}`} onClick={() => onModeChange('table')}><strong>Таблица полей</strong><span>Быстрее и безопаснее для типовых JSON.</span></button>
        <button type="button" className={`builder-help-card action-card ${mode === 'raw_template' ? 'active' : ''}`} onClick={() => onModeChange('raw_template')}><strong>Raw JSON template</strong><span>Нужен для сложных объектов и ручной структуры.</span></button>
      </div>
      {mode === 'table' ? <JsonFieldTableBuilder fields={fields} onChange={onFieldsChange} /> : <JsonRawTemplateEditor value={rawTemplate} onChange={onRawTemplateChange} />}
      {mode === 'table' ? <DynamicObjectEntryEditor entries={dynamicEntries} onChange={onDynamicEntriesChange} /> : null}
    </div>
  );
}
