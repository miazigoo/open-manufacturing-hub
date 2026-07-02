import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { eventsApi } from '../api/events';
import { incidentsApi } from '../api/incidents';
import { healthApi } from '../api/health';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { HealthCard } from '../components/HealthCard';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/I18nProvider';
import { formatDateTime } from '../utils';

export function DashboardPage() {
  const t = useT();
  const events = useQuery({ queryKey: ['events'], queryFn: eventsApi.list });
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: incidentsApi.list });
  const health = useQuery({ queryKey: ['health-dashboard'], queryFn: healthApi.dashboard });

  const isLoading = events.isLoading || incidents.isLoading || health.isLoading;
  const error = events.error ?? incidents.error ?? health.error;
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;

  const eventRows = events.data ?? [];
  const incidentRows = incidents.data ?? [];
  const failed = eventRows.filter((event) => event.status === 'failed');
  const retry = eventRows.filter((event) => event.status === 'retry_waiting');
  const openIncidents = incidentRows.filter((incident) => incident.status === 'open');

  return (
    <div className="page-stack">
      <header className="hero-panel dashboard-hero">
        <div>
          <span className="eyebrow">{t('dashboard.eyebrow')}</span>
          <h1>{t('dashboard.title')}</h1>
          <p>{t('dashboard.subtitle')}</p>
        </div>
        <div className="hero-instrument"><span>{failed.length}</span><small>{t('dashboard.activeFailures')}</small></div>
      </header>

      <section className="metric-grid">
        <Metric label={t('dashboard.eventsToday')} value={eventRows.length} />
        <Metric label={t('dashboard.failed')} value={failed.length} tone="bad" />
        <Metric label={t('dashboard.retryWaiting')} value={retry.length} tone="warn" />
        <Metric label={t('dashboard.openIncidents')} value={openIncidents.length} tone="info" />
        <Metric label={t('dashboard.queueSize')} value={0} />
      </section>

      <section className="dashboard-grid">
        <div className="panel wide-panel">
          <div className="panel-toolbar"><h2>{t('dashboard.latestFailures')}</h2><Link className="ghost-link" to="/events">{t('dashboard.openJournal')}</Link></div>
          {failed.length === 0 ? <EmptyState title={t('dashboard.noFailedEvents')} detail={t('dashboard.noFailedEventsDetail')} /> : (
            <div className="failure-list">
              {failed.slice(0, 6).map((event) => (
                <Link key={event.id} to={`/events/${event.id}`} className="failure-row">
                  <StatusBadge status={event.status} />
                  <strong>{event.event_type}</strong>
                  <span>{event.entity_type} #{event.entity_id}</span>
                  <span>{event.source_system} → {event.target_system ?? t('common.unknown')}</span>
                  <span>{formatDateTime(event.created_at)}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="panel">
          <div className="panel-toolbar"><h2>{t('dashboard.healthSummary')}</h2><Link className="ghost-link" to="/health">{t('common.details')}</Link></div>
          {health.data?.sites.length ? health.data.sites.slice(0, 3).map((site) => <HealthCard key={site.name} site={site} />) : <EmptyState title={t('dashboard.noHealthData')} detail={t('dashboard.noHealthDataDetail')} />}
          <div className="component-strip">
            {health.data?.components.slice(0, 5).map((component) => <span key={`${component.type}-${component.name}`}>{component.name}<StatusBadge status={component.status} compact /></span>)}
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone = 'neutral' }: { label: string; value: number; tone?: string }) {
  return <div className={`metric-card ${tone}`}><span>{label}</span><strong>{value.toLocaleString()}</strong></div>;
}
