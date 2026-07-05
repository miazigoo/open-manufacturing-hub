import type { AuditEvent } from '../../api/audit';
import { JsonBlock } from '../JsonBlock';
import { StatusBadge } from '../StatusBadge';
import { AuditDiffViewer } from './AuditDiffViewer';

export function AuditEventDetails({ event }: { event: AuditEvent | null }) {
  if (!event) return <div className="empty-state"><strong>Select an audit event</strong><span>Details, request context and JSON diff will appear here.</span></div>;
  return (
    <section className="panel audit-details-panel">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Audit Event</span><h2>{event.action}</h2></div>
        <StatusBadge status={event.severity} label={event.severity} />
      </div>
      <p>{event.summary}</p>
      <div className="details-grid">
        <Detail label="Time" value={new Date(event.timestamp).toLocaleString()} />
        <Detail label="Actor" value={event.actor_username ?? event.actor_type} />
        <Detail label="Category" value={event.category} />
        <Detail label="Object" value={[event.object_type, event.object_name ?? event.object_id].filter(Boolean).join(' · ') || 'none'} />
        <Detail label="Request ID" value={event.request_id ?? 'none'} />
        <Detail label="Correlation" value={event.correlation_id ?? event.event_id ?? event.queue_item_id ?? 'none'} />
      </div>
      <AuditDiffViewer diff={event.diff_json} />
      <div className="three-column-json">
        <JsonBlock title="Before" value={event.before_json ?? {}} searchable={false} />
        <JsonBlock title="After" value={event.after_json ?? {}} searchable={false} />
        <JsonBlock title="Details" value={event.details_json ?? {}} searchable={false} />
      </div>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="detail-card"><span>{label}</span><strong>{value}</strong></div>;
}
