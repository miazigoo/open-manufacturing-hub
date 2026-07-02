import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { EventStatus } from '../api/client';
import { eventsApi } from '../api/events';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { EventCreatePanel } from '../components/EventCreatePanel';
import { formatDateTime } from '../utils';

const statuses: Array<EventStatus | 'all'> = ['all', 'new', 'processing', 'success', 'failed', 'retry_waiting', 'cancelled', 'expired'];

export function EventJournalPage() {
  const [status, setStatus] = useState<EventStatus | 'all'>('all');
  const [eventType, setEventType] = useState('');
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const query = useQuery({ queryKey: ['events'], queryFn: eventsApi.list });

  const rows = useMemo(() => (query.data ?? []).filter((event) => {
    if (status !== 'all' && event.status !== status) return false;
    if (eventType && !event.event_type.toLowerCase().includes(eventType.toLowerCase())) return false;
    if (source && !event.source_system.toLowerCase().includes(source.toLowerCase())) return false;
    if (target && !(event.target_system ?? '').toLowerCase().includes(target.toLowerCase())) return false;
    return true;
  }), [query.data, status, eventType, source, target]);

  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack">
      <header className="page-header"><span className="eyebrow">Event Journal</span><h1>Every integration event, searchable and replayable.</h1></header>
      <EventCreatePanel />
      <section className="filter-bar">
        <select value={status} onChange={(event) => setStatus(event.target.value as EventStatus | 'all')}>{statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <input value={eventType} onChange={(event) => setEventType(event.target.value)} placeholder="Event type" />
        <input value={source} onChange={(event) => setSource(event.target.value)} placeholder="Source system" />
        <input value={target} onChange={(event) => setTarget(event.target.value)} placeholder="Target system" />
      </section>
      <section className="table-panel">
        {rows.length === 0 ? <EmptyState title="No events yet" detail="POST /api/events to create the first observable integration event." /> : (
          <table>
            <thead><tr><th>Created</th><th>Status</th><th>Event Type</th><th>Entity</th><th>Source</th><th>Target</th><th>Correlation ID</th><th>Actions</th></tr></thead>
            <tbody>
              {rows.map((event) => (
                <tr key={event.id}>
                  <td className="muted">{formatDateTime(event.created_at)}</td>
                  <td><StatusBadge status={event.status} /></td>
                  <td><strong>{event.event_type}</strong></td>
                  <td>{event.entity_type ?? 'Entity'} #{event.entity_id ?? 'unknown'}</td>
                  <td>{event.source_system}</td>
                  <td>{event.target_system ?? '—'}</td>
                  <td className="mono">{event.correlation_id ?? '—'}</td>
                  <td><Link className="primary-link" to={`/events/${event.id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
