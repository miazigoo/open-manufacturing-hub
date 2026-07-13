import type { AuditEvent } from '../../api/audit';
import { JsonBlock } from '../JsonBlock';
import { StatusBadge } from '../StatusBadge';
import { AuditDiffViewer } from './AuditDiffViewer';
import { useT } from '../../i18n/useI18n';

export function AuditEventDetails({ event }: { event: AuditEvent | null }) {
  const t = useT();
  if (!event) return <div className="empty-state"><strong>{t('audit.selectEvent')}</strong><span>{t('audit.selectEventHint')}</span></div>;
  return (
    <section className="panel audit-details-panel">
      <div className="panel-toolbar">
        <div><span className="eyebrow">{t('audit.event')}</span><h2>{event.action}</h2></div>
        <StatusBadge status={event.severity} label={event.severity} />
      </div>
      <p>{event.summary}</p>
      <div className="details-grid">
        <Detail label={t('audit.time')} value={new Date(event.timestamp).toLocaleString()} />
        <Detail label={t('audit.actor')} value={event.actor_username ?? event.actor_type} />
        <Detail label={t('audit.category')} value={event.category} />
        <Detail label={t('audit.object')} value={[event.object_type, event.object_name ?? event.object_id].filter(Boolean).join(' · ') || t('common.none')} />
        <Detail label={t('audit.requestId')} value={event.request_id ?? t('common.none')} />
        <Detail label={t('audit.correlation')} value={event.correlation_id ?? event.event_id ?? event.queue_item_id ?? t('common.none')} />
      </div>
      <AuditDiffViewer diff={event.diff_json} />
      <div className="three-column-json">
        <JsonBlock title={t('audit.before')} value={event.before_json ?? {}} searchable={false} />
        <JsonBlock title={t('audit.after')} value={event.after_json ?? {}} searchable={false} />
        <JsonBlock title={t('audit.details')} value={event.details_json ?? {}} searchable={false} />
      </div>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="detail-card"><span>{label}</span><strong>{value}</strong></div>;
}
