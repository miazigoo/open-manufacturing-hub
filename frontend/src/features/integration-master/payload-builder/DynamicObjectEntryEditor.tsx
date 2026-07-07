import type { JsonPayloadDynamicEntryConfig } from '../types';

interface DynamicObjectEntryEditorProps {
  entries: JsonPayloadDynamicEntryConfig[];
  onChange: (entries: JsonPayloadDynamicEntryConfig[]) => void;
}

export function DynamicObjectEntryEditor({ entries, onChange }: DynamicObjectEntryEditorProps) {
  function patch(index: number, patchValue: Partial<JsonPayloadDynamicEntryConfig>) {
    onChange(entries.map((entry, entryIndex) => (entryIndex === index ? { ...entry, ...patchValue } : entry)));
  }

  function remove(index: number) {
    onChange(entries.filter((_, entryIndex) => entryIndex !== index));
  }

  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Dynamic keys</span><h3>Динамические JSON-ключи</h3><p className="microcopy">Для DnP: `payload.order_numbers_by_basis` + key `order.Ref_Key` + value `order.Number`.</p></div><button type="button" className="secondary-button" onClick={() => onChange([...entries, { object_path: '', key_source: '', value_source: '', value_type: 'variable' }])}>Добавить ключ</button></div>
      <div className="metadata-grid compact-grid no-margin">
        {entries.map((entry, index) => (
          <div key={`${index}-${entry.object_path}`} className="status-card neutral">
            <label className="field-label">Object path<input value={entry.object_path} onChange={(event) => patch(index, { object_path: event.target.value })} placeholder="payload.order_numbers_by_basis" /></label>
            <label className="field-label">Key source<input value={entry.key_source} onChange={(event) => patch(index, { key_source: event.target.value })} placeholder="order.Ref_Key" /></label>
            <label className="field-label">Value source<input value={String(entry.value_source ?? '')} onChange={(event) => patch(index, { value_source: event.target.value })} placeholder="order.Number" /></label>
            <button type="button" className="link-button danger" onClick={() => remove(index)}>remove</button>
          </div>
        ))}
      </div>
    </section>
  );
}
