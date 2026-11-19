import { useEffect, useMemo, useRef, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { EventStatus } from '../api/client';
import { eventsApi } from '../api/events';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { EventCreatePanel } from '../components/EventCreatePanel';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const statuses: Array<EventStatus | 'all'> = [
  'all',
  'new',
  'processing',
  'success',
  'failed',
  'retry_waiting',
  'cancelled',
  'expired',
];

export function EventJournalPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL-driven query parameters
  const statusParam = (searchParams.get('status') as EventStatus | null) ?? 'all';
  const typeParam = searchParams.get('event_type') ?? '';
  const sourceParam = searchParams.get('source') ?? '';
  const targetParam = searchParams.get('target') ?? '';
  const qParam = searchParams.get('q') ?? '';
  const dateFromParam = searchParams.get('date_from') ?? '';
  const dateToParam = searchParams.get('date_to') ?? '';
  const cursorParam = searchParams.get('cursor') ?? null;

  // Local draft inputs for 300ms debounce
  const [typeInput, setTypeInput] = useState(typeParam);
  const [sourceInput, setSourceInput] = useState(sourceParam);
  const [targetInput, setTargetInput] = useState(targetParam);
  const [qInput, setQInput] = useState(qParam);
  const [dateFromInput, setDateFromInput] = useState(dateFromParam);
  const [dateToInput, setDateToInput] = useState(dateToParam);

  // Stack of cursors for "Back" navigation within current filter session
  const [cursorStack, setCursorStack] = useState<string[]>([]);

  // Synchronize local input state if URL changes externally
  useEffect(() => {
    setTypeInput(typeParam);
    setSourceInput(sourceParam);
    setTargetInput(targetParam);
    setQInput(qParam);
    setDateFromInput(dateFromParam);
    setDateToInput(dateToParam);
  }, [typeParam, sourceParam, targetParam, qParam, dateFromParam, dateToParam]);

  // Debounced sync from local inputs to URL searchParams
  const debounceTimerRef = useRef<number | null>(null);
  const updateFilters = (next: {
    status?: string;
    event_type?: string;
    source?: string;
    target?: string;
    q?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const params = new URLSearchParams(searchParams);
    if (next.status !== undefined) {
      if (next.status && next.status !== 'all') params.set('status', next.status);
      else params.delete('status');
    }
    if (next.event_type !== undefined) {
      if (next.event_type.trim()) params.set('event_type', next.event_type.trim());
      else params.delete('event_type');
    }
    if (next.source !== undefined) {
      if (next.source.trim()) params.set('source', next.source.trim());
      else params.delete('source');
    }
    if (next.target !== undefined) {
      if (next.target.trim()) params.set('target', next.target.trim());
      else params.delete('target');
    }
    if (next.q !== undefined) {
      if (next.q.trim()) params.set('q', next.q.trim());
      else params.delete('q');
    }
    if (next.date_from !== undefined) {
      if (next.date_from.trim()) params.set('date_from', next.date_from.trim());
      else params.delete('date_from');
    }
    if (next.date_to !== undefined) {
      if (next.date_to.trim()) params.set('date_to', next.date_to.trim());
      else params.delete('date_to');
    }
    // Filter change always resets pagination cursor
    params.delete('cursor');
    setCursorStack([]);
    setSearchParams(params, { replace: true });
  };

  const onTextChange = (key: 'event_type' | 'source' | 'target' | 'q' | 'date_from' | 'date_to', val: string) => {
    if (key === 'q') setQInput(val);
    else if (key === 'event_type') setTypeInput(val);
    else if (key === 'source') setSourceInput(val);
    else if (key === 'target') setTargetInput(val);
    else if (key === 'date_from') setDateFromInput(val);
    else if (key === 'date_to') setDateToInput(val);

    if (debounceTimerRef.current) window.clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = window.setTimeout(() => {
      updateFilters({ [key]: val });
    }, 300);
  };

  const hasActiveFilters = Boolean(
    (statusParam && statusParam !== 'all') ||
    typeParam.trim() ||
    sourceParam.trim() ||
    targetParam.trim() ||
    qParam.trim() ||
    dateFromParam.trim() ||
    dateToParam.trim()
  );

  const queryKey = useMemo(
    () => [
      'events-journal',
      {
        status: statusParam,
        event_type: typeParam,
        source: sourceParam,
        target: targetParam,
        q: qParam,
        date_from: dateFromParam,
        date_to: dateToParam,
        cursor: cursorParam,
      },
    ],
    [statusParam, typeParam, sourceParam, targetParam, qParam, dateFromParam, dateToParam, cursorParam]
  );

  const query = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      eventsApi.journalPage(
        {
          status: statusParam === 'all' ? undefined : statusParam,
          event_type: typeParam || undefined,
          source: sourceParam || undefined,
          target: targetParam || undefined,
          q: qParam || undefined,
          date_from: dateFromParam || undefined,
          date_to: dateToParam || undefined,
          limit: 50,
          cursor: cursorParam,
        },
        { signal }
      ),
    placeholderData: keepPreviousData,
  });

  const pageData = query.data;
  const rows = pageData?.items ?? [];

  const handleNextPage = () => {
    if (!pageData?.next_cursor) return;
    setCursorStack((prev) => [...prev, cursorParam ?? '']);
    const params = new URLSearchParams(searchParams);
    params.set('cursor', pageData.next_cursor);
    setSearchParams(params);
  };

  const handlePrevPage = () => {
    if (cursorStack.length === 0 && !cursorParam) return;
    const nextStack = [...cursorStack];
    const prevCursor = nextStack.pop() ?? '';
    setCursorStack(nextStack);
    const params = new URLSearchParams(searchParams);
    if (prevCursor) params.set('cursor', prevCursor);
    else params.delete('cursor');
    setSearchParams(params);
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['events-journal'] });
  };

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">{t('events.eyebrow')}</span>
        <h1>{t('events.title')}</h1>
      </header>

      <EventCreatePanel />

      <section className="filter-bar" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
        <select
          value={statusParam}
          aria-label={t('common.status')}
          onChange={(e) => updateFilters({ status: e.target.value })}
        >
          {statuses.map((item) => (
            <option key={item} value={item}>
              {item === 'all' ? t('common.all') : t(`status.${item}`)}
            </option>
          ))}
        </select>

        <input
          value={qInput}
          onChange={(e) => onTextChange('q', e.target.value)}
          placeholder={t('events.searchPlaceholder')}
          style={{ minWidth: '260px', flex: '1 1 200px' }}
        />

        <input
          value={typeInput}
          onChange={(e) => onTextChange('event_type', e.target.value)}
          placeholder={t('events.eventType')}
          style={{ width: '140px' }}
        />

        <input
          value={sourceInput}
          onChange={(e) => onTextChange('source', e.target.value)}
          placeholder={t('events.sourceSystem')}
          style={{ width: '130px' }}
        />

        <input
          value={targetInput}
          onChange={(e) => onTextChange('target', e.target.value)}
          placeholder={t('events.targetSystem')}
          style={{ width: '130px' }}
        />

        <input
          type="datetime-local"
          value={dateFromInput}
          onChange={(e) => onTextChange('date_from', e.target.value)}
          aria-label={t('events.dateFrom')}
          title={t('events.dateFrom')}
          style={{ width: '180px' }}
        />

        <input
          type="datetime-local"
          value={dateToInput}
          onChange={(e) => onTextChange('date_to', e.target.value)}
          aria-label={t('events.dateTo')}
          title={t('events.dateTo')}
          style={{ width: '180px' }}
        />

        <button type="button" className="ghost-button" onClick={handleRefresh} title={t('common.refresh')}>
          {t('common.refresh')}
        </button>

        {query.isFetching && <small style={{ opacity: 0.7 }}>{t('common.loading')}...</small>}
      </section>

      <section className="table-panel">
        {query.isLoading && rows.length === 0 ? (
          <LoadingState />
        ) : query.error && rows.length === 0 ? (
          <div>
            <ErrorState error={query.error} />
            <div style={{ marginTop: '12px', textAlign: 'center' }}>
              <button type="button" className="ghost-button" onClick={() => query.refetch()}>
                {t('common.retry')}
              </button>
            </div>
          </div>
        ) : rows.length === 0 ? (
          hasActiveFilters ? (
            <EmptyState title={t('events.noFilteredEvents')} detail={t('events.noFilteredEventsDetail')} />
          ) : (
            <EmptyState title={t('events.noEvents')} detail={t('events.noEventsDetail')} />
          )
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>{t('common.created')}</th>
                  <th>{t('common.status')}</th>
                  <th>{t('events.journalTitle')}</th>
                  <th>{t('common.source')} → {t('common.target')}</th>
                  <th>{t('events.operation')}</th>
                  <th>{t('events.businessKey')}</th>
                  <th>Queue</th>
                  <th>{t('events.lastError')}</th>
                  <th>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((event) => (
                  <tr
                    key={event.id}
                    id={`event-${event.id}`}
                    className={event.requires_attention ? 'attention-row' : ''}
                  >
                    <td className="muted">{formatDateTime(event.created_at)}</td>
                    <td><StatusBadge status={event.status} /></td>
                    <td>
                      <strong>{event.human_title}</strong>
                      <small>{event.human_summary}</small>
                    </td>
                    <td>
                      {event.source_display ?? event.source_system} → {event.target_display ?? event.target_system ?? '—'}
                    </td>
                    <td>{event.operation ?? event.event_type}</td>
                    <td>{event.business_key ?? event.correlation_id ?? '—'}</td>
                    <td>
                      {event.queue_status ? (
                        <>
                          <StatusBadge status={event.queue_status} label={event.queue_status} compact />
                          <small>
                            {event.queue_attempts}/{event.queue_max_attempts} · {event.queue_next_retry_at ?? 'no retry'}
                          </small>
                        </>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      <strong>{event.last_error_code ?? '—'}</strong>
                      <small>{event.last_external_error_message ?? event.last_error_summary ?? event.hint ?? ''}</small>
                    </td>
                    <td>
                      <Link className="primary-link" to={`/events/${event.id}`}>
                        {t('common.open')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div
              className="pagination-controls"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 16px',
                borderTop: '1px solid var(--border-color, #e2e8f0)',
              }}
            >
              <div>
                <small className="muted">
                  {rows.length} {t('common.entity')}
                </small>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={handlePrevPage}
                  disabled={cursorStack.length === 0 && !cursorParam}
                >
                  ← {t('common.previous')}
                </button>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={handleNextPage}
                  disabled={!pageData?.has_more}
                >
                  {t('common.next')} →
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
