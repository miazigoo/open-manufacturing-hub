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
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const statuses: Array<EventStatus | 'all'> = ['all', 'new', 'processing', 'success', 'failed', 'retry_waiting', 'cancelled', 'expired'];

export function EventJournalPage() {
  const t = useT();
  const [status, setStatus] = useState<EventStatus | 'all'>('all');
  const [eventType, setEventType] = useState('');
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const query = useQuery({ queryKey: ['events-journal'], queryFn: eventsApi.journal });

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
      <header className="page-header"><span className="eyebrow">{t('events.eyebrow')}</span><h1>{t('events.title')}</h1></header>
      <EventCreatePanel />
      <section className="filter-bar">
        <select value={status} onChange={(event) => setStatus(event.target.value as EventStatus | 'all')}>{statuses.map((item) => <option key={item} value={item}>{item === 'all' ? t('common.all') : t(`status.${item}`)}</option>)}</select>
        <input value={eventType} onChange={(event) => setEventType(event.target.value)} placeholder={t('events.eventType')} />
        <input value={source} onChange={(event) => setSource(event.target.value)} placeholder={t('events.sourceSystem')} />
        <input value={target} onChange={(event) => setTarget(event.target.value)} placeholder={t('events.targetSystem')} />
      </section>
      <section className="table-panel">
        {rows.length === 0 ? <EmptyState title={t('events.noEvents')} detail={t('events.noEventsDetail')} /> : (
          <table>
            <thead><tr><th>{t('common.created')}</th><th>{t('common.status')}</th><th>{t('events.journalTitle')}</th><th>{t('common.source')} → {t('common.target')}</th><th>{t('events.operation')}</th><th>{t('events.businessKey')}</th><th>{t('events.lastError')}</th><th>{t('common.actions')}</th></tr></thead>
            <tbody>
              {rows.map((event) => (
                <tr key={event.id} className={event.requires_attention ? 'attention-row' : ''}>
                  <td className="muted">{formatDateTime(event.created_at)}</td>
                  <td><StatusBadge status={event.status} /></td>
                  <td><strong>{event.human_title}</strong><small>{event.human_summary}</small></td>
                  <td>{event.source_display ?? event.source_system} → {event.target_display ?? event.target_system ?? '—'}</td>
                  <td>{event.operation ?? event.event_type}</td>
                  <td>{event.business_key ?? event.correlation_id ?? '—'}</td>
                  <td><strong>{event.last_error_code ?? '—'}</strong><small>{event.last_external_error_message ?? event.last_error_summary ?? event.hint ?? ''}</small></td>
                  <td><Link className="primary-link" to={`/events/${event.id}`}>{t('common.open')}</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
