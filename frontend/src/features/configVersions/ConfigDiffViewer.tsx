import { asJson } from '../../api/client';
import { ConfigDiffEntry, ConfigDiffResponse } from '../../api/configVersions';

function DiffList({ title, items }: { title: string; items: ConfigDiffEntry[] }) {
  return (
    <section className="config-diff-column">
      <h3>{title}</h3>
      {items.length === 0 ? <p className="microcopy">No changes</p> : items.map((item, index) => (
        <article key={`${title}-${item.path}-${index}`} className="config-diff-item">
          <strong>{item.path || '/'}</strong>
          <pre>{asJson(item)}</pre>
        </article>
      ))}
    </section>
  );
}

export function ConfigDiffViewer({ diff }: { diff: ConfigDiffResponse | null | undefined }) {
  if (!diff) return <div className="empty-panel compact">Select two versions to see a redacted diff.</div>;
  return (
    <div className="config-diff-viewer">
      <DiffList title="Added" items={diff.added} />
      <DiffList title="Changed" items={diff.changed} />
      <DiffList title="Removed" items={diff.removed} />
    </div>
  );
}
