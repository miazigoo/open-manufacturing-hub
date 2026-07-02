import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../api/health';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { HealthCard } from '../components/HealthCard';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function HealthPage() {
  const query = useQuery({ queryKey: ['health-dashboard'], queryFn: healthApi.dashboard });
  if (query.isLoading) return <LoadingState label="Loading health dashboard" />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack">
      <header className="page-header"><span className="eyebrow">Health Dashboard</span><h1>Sites, connectors and channels at a glance.</h1></header>
      <section className="card-grid">{query.data?.sites.length ? query.data.sites.map((site) => <HealthCard key={site.name} site={site} />) : <EmptyState title="No site telemetry" detail="POST agent heartbeats to populate warehouse health." />}</section>
      <section className="panel">
        <div className="panel-toolbar"><h2>Components</h2></div>
        {query.data?.components.length ? <div className="component-list">{query.data.components.map((component) => <div key={`${component.type}-${component.name}`}><strong>{component.name}</strong><span>{component.type}</span><StatusBadge status={component.status} /></div>)}</div> : <EmptyState title="No component checks" detail="Connector and notification channel checks will appear here." />}
      </section>
    </div>
  );
}
