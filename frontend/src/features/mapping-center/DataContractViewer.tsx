import type { DataContract, DataContractField } from '../../api/dataContracts';
import { asJson } from '../../api/client';
import { StatusBadge } from '../../components/StatusBadge';

interface DataContractViewerProps {
  contract: DataContract | null | undefined;
  mappedSources?: Record<string, string>;
  title?: string;
  compact?: boolean;
}

export function DataContractViewer({ contract, mappedSources = {}, title = 'Data Contract', compact = false }: DataContractViewerProps) {
  if (!contract) {
    return (
      <section className="builder-help-card">
        <div className="panel-toolbar compact-toolbar"><div><span className="eyebrow">{title}</span><h3>Контракт не выбран</h3></div><StatusBadge status="missing" compact /></div>
        <p className="microcopy">У этой операции нет описанного контракта. Можно использовать raw template, но Mapping Center не сможет проверить required поля.</p>
      </section>
    );
  }
  const fields = contract.fields?.length ? contract.fields : fieldsFromSchema(contract.schema_json);
  return (
    <section className="builder-help-card data-contract-viewer">
      <div className="panel-toolbar compact-toolbar">
        <div>
          <span className="eyebrow">{title}</span>
          <h3>{contract.name}</h3>
          <p className="microcopy"><code>{contract.code}</code> · {contract.kind}</p>
        </div>
        <StatusBadge status={fields.every((field) => !field.required || mappedSources[field.path]) ? 'ready' : 'partial'} compact />
      </div>
      {contract.description && <p className="microcopy">{contract.description}</p>}
      <div className="table-scroll">
        <table>
          <thead><tr><th>Target field</th><th>Type</th><th>Required</th><th>Description</th><th>Example</th><th>Mapped source</th></tr></thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.path}>
                <td><code>{field.path}</code><small>{field.label ?? ''}</small></td>
                <td><code>{field.type}</code></td>
                <td><StatusBadge status={field.required ? 'warning' : 'not_applicable'} label={field.required ? 'required' : 'optional'} compact /></td>
                <td><small>{field.description || '—'}</small></td>
                <td><small>{formatExample(field.example)}</small></td>
                <td><small>{mappedSources[field.path] ? <code>{mappedSources[field.path]}</code> : '—'}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!compact && contract.example_json != null && <details><summary>Example payload</summary><pre className="microcopy">{asJson(contract.example_json)}</pre></details>}
    </section>
  );
}

function fieldsFromSchema(schema: unknown): DataContractField[] {
  if (!schema || typeof schema !== 'object' || !('fields' in schema) || !Array.isArray((schema as { fields?: unknown }).fields)) return [];
  return (schema as { fields: unknown[] }).fields.filter((field): field is DataContractField => Boolean(field && typeof field === 'object' && 'path' in field));
}

function formatExample(value: unknown) {
  if (typeof value === 'undefined') return '—';
  if (typeof value === 'string') return value;
  return asJson(value).slice(0, 160);
}
