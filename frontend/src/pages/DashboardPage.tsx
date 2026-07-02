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
import { formatDateTime } from '../utils';

export function DashboardPage() {
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
          <span className="eyebrow">System Overview</span>
          <h1>Integration operations without guesswork.</h1>
          <p>Failures, incidents, health and recovery controls in one operational surface.</p>
        </div>
        <div className="hero-instrument"><span>{failed.length}</span><small>active failures</small></div>
      </header>

      <section className="metric-grid">
        <Metric label="Events today" value={eventRows.length} />
        <Metric label="Failed" value={failed.length} tone="bad" />
        <Metric label="Retry waiting" value={retry.length} tone="warn" />
        <Metric label="Open incidents" value={openIncidents.length} tone="info" />
        <Metric label="Queue size" value={0} />
      </section>

      <section className="dashboard-grid">
        <div className="panel wide-panel">
          <div className="panel-toolbar"><h2>Latest failures</h2><Link className="ghost-link" to="/events">Open journal</Link></div>
          {failed.length === 0 ? <EmptyState title="No failed events" detail="When a pipeline fails, it appears here with timeline access." /> : (
            <div className="failure-list">
              {failed.slice(0, 6).map((event) => (
                <Link key={event.id} to={`/events/${event.id}`} className="failure-row">
                  <StatusBadge status={event.status} />
                  <strong>{event.event_type}</strong>
                  <span>{event.entity_type} #{event.entity_id}</span>
                  <span>{event.source_system} → {event.target_system ?? 'unknown'}</span>
                  <span>{formatDateTime(event.created_at)}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="panel">
          <div className="panel-toolbar"><h2>Health summary</h2><Link className="ghost-link" to="/health">Details</Link></div>
          {health.data?.sites.length ? health.data.sites.slice(0, 3).map((site) => <HealthCard key={site.name} site={site} />) : <EmptyState title="No health data" detail="Agent heartbeat and component checks will populate this area." />}
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
