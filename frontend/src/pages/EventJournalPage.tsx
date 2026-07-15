import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { EventStatus } from '../api/client';
import { eventsApi } from '../api/events';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { EventCreatePanel } from '../components/EventCreatePanel';
import { SearchToolbar, SortableTh } from '../components/table/TableControls';
import { usePersistentState } from '../hooks/usePersistentState';
import { useTableControls } from '../hooks/useTableControls';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const statuses: Array<EventStatus | 'all'> = ['all', 'new', 'processing', 'success', 'failed', 'retry_waiting', 'cancelled', 'expired'];

interface EventFilters {
  status: EventStatus | 'all';
  eventType: string;
  source: string;
  target: string;
}

const defaultFilters: EventFilters = { status: 'all', eventType: '', source: '', target: '' };

export function EventJournalPage() {
  const t = useT();
  const [filters, setFilters, resetFilters] = usePersistentState<EventFilters>('omh.events.filters.v1', defaultFilters);
  const query = useQuery({ queryKey: ['events-journal'], queryFn: eventsApi.journal });

  const filtered = useMemo(() => (query.data ?? []).filter((event) => {
    if (filters.status !== 'all' && event.status !== filters.status) return false;
    if (filters.eventType && !event.event_type.toLowerCase().includes(filters.eventType.toLowerCase())) return false;
    if (filters.source && !event.source_system.toLowerCase().includes(filters.source.toLowerCase())) return false;
    if (filters.target && !(event.target_system ?? '').toLowerCase().includes(filters.target.toLowerCase())) return false;
    return true;
  }), [query.data, filters]);

  const table = useTableControls(filtered, {
    storageKey: 'omh.events.table.v1',
    searchText: (event) => [event.human_title, event.human_summary, event.event_type, event.source_system, event.target_system, event.business_key, event.correlation_id, event.last_error_code].filter(Boolean).join(' '),
    columns: {
      created: (event) => event.created_at,
      status: (event) => event.status,
      title: (event) => event.human_title,
      operation: (event) => event.operation ?? event.event_type,
    },
    defaultSort: { key: 'created', direction: 'desc' },
  });

  const filtersActive = filters.status !== 'all' || Boolean(filters.eventType || filters.source || filters.target);

  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack">
      <header className="page-header"><span className="eyebrow">{t('events.eyebrow')}</span><h1>{t('events.title')}</h1></header>
      <EventCreatePanel />
      <section className="filter-bar">
        <select value={filters.status} onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value as EventStatus | 'all' }))}>{statuses.map((item) => <option key={item} value={item}>{item === 'all' ? t('common.all') : t(`status.${item}`)}</option>)}</select>
        <input value={filters.eventType} onChange={(event) => setFilters((prev) => ({ ...prev, eventType: event.target.value }))} placeholder={t('events.eventType')} />
        <input value={filters.source} onChange={(event) => setFilters((prev) => ({ ...prev, source: event.target.value }))} placeholder={t('events.sourceSystem')} />
        <input value={filters.target} onChange={(event) => setFilters((prev) => ({ ...prev, target: event.target.value }))} placeholder={t('events.targetSystem')} />
        {filtersActive && <button type="button" className="ghost-button" onClick={resetFilters}>{t('common.table.reset')}</button>}
      </section>
      <section className="table-panel">
        <SearchToolbar value={table.search} onChange={table.setSearch} shown={table.shown} total={table.total} isFiltered={table.isFiltered} onReset={table.reset} />
        {table.rows.length === 0 ? <EmptyState title={t('events.noEvents')} detail={t('events.noEventsDetail')} /> : (
          <table>
            <thead><tr>
              <SortableTh columnKey="created" sort={table.sort} onSort={table.toggleSort}>{t('common.created')}</SortableTh>
              <SortableTh columnKey="status" sort={table.sort} onSort={table.toggleSort}>{t('common.status')}</SortableTh>
              <SortableTh columnKey="title" sort={table.sort} onSort={table.toggleSort}>{t('events.journalTitle')}</SortableTh>
              <th>{t('common.source')} → {t('common.target')}</th>
              <SortableTh columnKey="operation" sort={table.sort} onSort={table.toggleSort}>{t('events.operation')}</SortableTh>
              <th>{t('events.businessKey')}</th><th>Queue</th><th>{t('events.lastError')}</th><th>{t('common.actions')}</th>
            </tr></thead>
            <tbody>
              {table.rows.map((event) => (
                <tr key={event.id} className={event.requires_attention ? 'attention-row' : ''}>
                  <td className="muted">{formatDateTime(event.created_at)}</td>
                  <td><StatusBadge status={event.status} /></td>
                  <td><strong>{event.human_title}</strong><small>{event.human_summary}</small></td>
                  <td>{event.source_display ?? event.source_system} → {event.target_display ?? event.target_system ?? '—'}</td>
                  <td>{event.operation ?? event.event_type}</td>
                  <td>{event.business_key ?? event.correlation_id ?? '—'}</td>
                  <td>{event.queue_status ? <><StatusBadge status={event.queue_status} label={event.queue_status} compact /><small>{event.queue_attempts}/{event.queue_max_attempts} · {event.queue_next_retry_at ?? 'no retry'}</small></> : '—'}</td>
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
