import { JsonBlock } from '../JsonBlock';
import type { AuditDiff } from '../../api/audit';

export function AuditDiffViewer({ diff }: { diff: AuditDiff | null }) {
  const added = diff?.added ?? [];
  const removed = diff?.removed ?? [];
  const changed = diff?.changed ?? [];
  const empty = added.length + removed.length + changed.length === 0;
  if (empty) return <div className="empty-state compact"><strong>No field-level changes</strong><span>This event has no JSON diff payload.</span></div>;
  return (
    <div className="audit-diff-grid">
      <DiffGroup title="Changed" tone="warning" items={changed} />
      <DiffGroup title="Added" tone="ok" items={added} />
      <DiffGroup title="Removed" tone="error" items={removed} />
    </div>
  );
}

function DiffGroup({ title, tone, items }: { title: string; tone: string; items: Array<{ path: string; before?: unknown; after?: unknown }> }) {
  return (
    <article className="panel compact-panel">
      <div className="panel-toolbar"><h3>{title}</h3><span className={`status-pill ${tone}`}>{items.length}</span></div>
      {items.length === 0 ? <p className="microcopy">No entries</p> : items.map((item) => (
        <div className="audit-diff-row" key={`${title}:${item.path}`}>
          <strong>{item.path}</strong>
          {'before' in item && <JsonBlock value={item.before} searchable={false} />}
          {'after' in item && <JsonBlock value={item.after} searchable={false} />}
        </div>
      ))}
    </article>
  );
}
