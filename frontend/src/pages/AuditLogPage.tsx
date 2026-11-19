import { ChangeEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { API_BASE_URL } from '../api/client';
import { auditApi, type AuditEvent, type AuditFilters } from '../api/audit';
import { AuditEventDetails } from '../components/audit/AuditEventDetails';
import { ObjectHistoryPanel } from '../components/audit/ObjectHistoryPanel';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const categories = ['auth', 'users', 'connectors', 'integration_flows', 'endpoints', 'routes', 'workflows', 'mappings', 'operation_templates', 'resolvers', 'business_rules', 'transforms', 'packages', 'plugin_store', 'queue', 'dlq', 'production', 'notifications', 'maintenance', 'secrets', 'settings'];
const severities = ['info', 'warning', 'error', 'critical'];

export function AuditLogPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AuditFilters>({ limit: 50, offset: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const audit = useQuery({ queryKey: ['audit-log', filters], queryFn: () => auditApi.list(filters) });
  const stats = useQuery({ queryKey: ['audit-stats'], queryFn: auditApi.stats });
  const cleanup = useMutation({ mutationFn: () => auditApi.cleanup(undefined, true), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['audit-stats'] }) });

  // Load detailed event on demand only when selected
  const eventDetails = useQuery({
    queryKey: ['audit-event-detail', selectedId],
    queryFn: () => auditApi.get(selectedId!),
    enabled: Boolean(selectedId),
  });

  const total = audit.data?.total ?? 0;
  const limit = filters.limit ?? 50;
  const offset = filters.offset ?? 0;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const topCategories = useMemo(() => Object.entries(stats.data?.by_category ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 5), [stats.data]);

  function update(key: keyof AuditFilters, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value || undefined, offset: 0 }));
    setSelectedId(null);
  }

  function goToPage(page: number) {
    const nextOffset = Math.max(0, (page - 1) * limit);
    setFilters((prev) => ({ ...prev, offset: nextOffset }));
    setSelectedId(null);
  }

  if (audit.isLoading && !audit.data) return <LoadingState label="Loading audit log" />;
  if (audit.error) return <ErrorState error={audit.error} />;

  const currentDetailedEvent = eventDetails.data ?? null;

  return (
    <div className="page-stack audit-page">
      <section className="page-header product-page-header audit-hero">
        <div>
          <span className="eyebrow">Audit Log</span>
          <h1>Change history for production integrations.</h1>
          <p>Track who changed connectors, routes, workflows, packages, runtime queue items and production safety controls.</p>
        </div>
        <div className="product-header-actions">
          <a className="ghost-button" href={`${API_BASE_URL}${auditApi.exportUrl()}`}>Export JSON</a>
          <button className="ghost-button" onClick={() => cleanup.mutate()} disabled={cleanup.isPending}>Retention dry-run</button>
        </div>
      </section>

      <section className="metric-grid">
        <article className="metric-card"><span>Total events</span><strong>{stats.data?.total ?? audit.data?.total ?? 0}</strong><small>{audit.data?.total ?? 0} matching filters</small></article>
        <article className="metric-card"><span>Newest</span><strong>{stats.data?.newest_timestamp ? new Date(stats.data.newest_timestamp).toLocaleDateString() : 'none'}</strong><small>{stats.data?.newest_timestamp ? new Date(stats.data.newest_timestamp).toLocaleTimeString() : 'no data'}</small></article>
        <article className="metric-card"><span>Top category</span><strong>{topCategories[0]?.[0] ?? 'none'}</strong><small>{topCategories[0]?.[1] ?? 0} events</small></article>
        <article className="metric-card"><span>Warnings+</span><strong>{(stats.data?.by_severity.warning ?? 0) + (stats.data?.by_severity.error ?? 0) + (stats.data?.by_severity.critical ?? 0)}</strong><small>warning / error / critical</small></article>
      </section>

      {cleanup.data && <section className="panel warning-panel"><strong>Retention dry-run</strong><span>{cleanup.data.deleted} events older than {new Date(cleanup.data.cutoff).toLocaleString()} would be deleted.</span></section>}

      <section className="panel audit-filters">
        <div className="panel-toolbar"><h2>Filters</h2><span>{audit.data?.total ?? 0} events</span></div>
        <div className="form-grid dense-form-grid">
          <label>Search<input value={filters.search ?? ''} onChange={(event) => update('search', event.target.value)} placeholder="summary, action, object, request" /></label>
          <label>Category<select value={filters.category ?? ''} onChange={(event) => update('category', event.target.value)}><option value="">All</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Severity<select value={filters.severity ?? ''} onChange={(event) => update('severity', event.target.value)}><option value="">All</option>{severities.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Action<input value={filters.action ?? ''} onChange={(event) => update('action', event.target.value)} placeholder="connector.updated" /></label>
          <label>Actor<input value={filters.actor_username ?? ''} onChange={(event) => update('actor_username', event.target.value)} placeholder="username" /></label>
          <label>Object type<input value={filters.object_type ?? ''} onChange={(event) => update('object_type', event.target.value)} placeholder="connector" /></label>
          <label>Object ID<input value={filters.object_id ?? ''} onChange={(event) => update('object_id', event.target.value)} placeholder="uuid or slug" /></label>
          <label>From<input type="datetime-local" onChange={(event: ChangeEvent<HTMLInputElement>) => update('date_from', event.target.value ? new Date(event.target.value).toISOString() : '')} /></label>
          <label>To<input type="datetime-local" onChange={(event: ChangeEvent<HTMLInputElement>) => update('date_to', event.target.value ? new Date(event.target.value).toISOString() : '')} /></label>
        </div>
      </section>

      <section className="audit-workbench">
        <article className="panel audit-table-panel">
          <div className="panel-toolbar">
            <h2>Events</h2>
            <div className="toolbar-actions">
              <span className="microcopy">Страница {currentPage} из {totalPages} ({total} всего)</span>
              {audit.isFetching && <span className="microcopy">refreshing</span>}
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table audit-table">
              <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Object</th><th>Summary</th><th>Severity</th></tr></thead>
              <tbody>
                {audit.data?.items.map((event) => (
                  <tr
                    key={event.id}
                    className={selectedId === event.id ? 'selected-row' : ''}
                    tabIndex={0}
                    role="button"
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedId(event.id); } }}
                    onClick={() => setSelectedId(event.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{new Date(event.timestamp).toLocaleString()}</td>
                    <td>{event.actor_username ?? event.actor_type}</td>
                    <td><code>{event.action}</code></td>
                    <td>{event.object_name ?? event.object_id ?? event.object_type ?? 'none'}</td>
                    <td>{event.summary}</td>
                    <td><StatusBadge status={event.severity} label={event.severity} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!audit.data?.items.length && <div className="empty-state compact"><strong>No audit events</strong><span>Run a configuration or runtime action to populate the log.</span></div>}
          
          {totalPages > 1 && (
            <div className="pagination-bar" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '1rem', justifyContent: 'flex-end' }}>
              <button
                className="ghost-button"
                disabled={currentPage <= 1}
                onClick={() => goToPage(1)}
              >
                « Первая
              </button>
              <button
                className="ghost-button"
                disabled={currentPage <= 1}
                onClick={() => goToPage(currentPage - 1)}
              >
                ‹ Назад
              </button>
              <span>{currentPage} / {totalPages}</span>
              <button
                className="ghost-button"
                disabled={currentPage >= totalPages}
                onClick={() => goToPage(currentPage + 1)}
              >
                Далее ›
              </button>
              <button
                className="ghost-button"
                disabled={currentPage >= totalPages}
                onClick={() => goToPage(totalPages)}
              >
                Последняя »
              </button>
            </div>
          )}
        </article>

        <div className="audit-side-panel">
          {selectedId ? (
            eventDetails.isLoading ? (
              <LoadingState label="Loading event details..." />
            ) : eventDetails.error ? (
              <ErrorState error={eventDetails.error} />
            ) : currentDetailedEvent ? (
              <>
                <AuditEventDetails event={currentDetailedEvent} />
                <ObjectHistoryPanel objectType={currentDetailedEvent.object_type ?? null} objectId={currentDetailedEvent.object_id ?? null} />
              </>
            ) : null
          ) : (
            <div className="panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Выберите событие аудита в таблице для просмотра деталей и истории изменений
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
