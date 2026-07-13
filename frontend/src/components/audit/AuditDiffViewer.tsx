import { JsonBlock } from '../JsonBlock';
import type { AuditDiff } from '../../api/audit';
import { useT } from '../../i18n/useI18n';

export function AuditDiffViewer({ diff }: { diff: AuditDiff | null }) {
  const t = useT();
  const added = diff?.added ?? [];
  const removed = diff?.removed ?? [];
  const changed = diff?.changed ?? [];
  const empty = added.length + removed.length + changed.length === 0;
  if (empty) return <div className="empty-state compact"><strong>{t('audit.noFieldChanges')}</strong><span>{t('audit.noJsonDiff')}</span></div>;
  return (
    <div className="audit-diff-grid">
      <DiffGroup title={t('audit.changed')} tone="warning" items={changed} />
      <DiffGroup title={t('audit.added')} tone="ok" items={added} />
      <DiffGroup title={t('audit.removed')} tone="error" items={removed} />
    </div>
  );
}

function DiffGroup({ title, tone, items }: { title: string; tone: string; items: Array<{ path: string; before?: unknown; after?: unknown }> }) {
  const t = useT();
  return (
    <article className="panel compact-panel">
      <div className="panel-toolbar"><h3>{title}</h3><span className={`status-pill ${tone}`}>{items.length}</span></div>
      {items.length === 0 ? <p className="microcopy">{t('audit.noEntries')}</p> : items.map((item) => (
        <div className="audit-diff-row" key={`${title}:${item.path}`}>
          <strong>{item.path}</strong>
          {'before' in item && <JsonBlock value={item.before} searchable={false} />}
          {'after' in item && <JsonBlock value={item.after} searchable={false} />}
        </div>
      ))}
    </article>
  );
}
