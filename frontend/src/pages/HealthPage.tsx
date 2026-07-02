import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../api/health';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { HealthCard } from '../components/HealthCard';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/I18nProvider';

export function HealthPage() {
  const t = useT();
  const query = useQuery({ queryKey: ['health-dashboard'], queryFn: healthApi.dashboard });
  if (query.isLoading) return <LoadingState label={t('health.loading')} />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack">
      <header className="page-header"><span className="eyebrow">{t('health.eyebrow')}</span><h1>{t('health.dashboardTitle')}</h1></header>
      <section className="card-grid">{query.data?.sites.length ? query.data.sites.map((site) => <HealthCard key={site.name} site={site} />) : <EmptyState title={t('health.noSites')} detail={t('health.noSitesDetail')} />}</section>
      <section className="panel">
        <div className="panel-toolbar"><h2>{t('health.components')}</h2></div>
        {query.data?.components.length ? <div className="component-list">{query.data.components.map((component) => <div key={`${component.type}-${component.name}`}><strong>{component.name}</strong><span>{component.type}</span><StatusBadge status={component.status} /></div>)}</div> : <EmptyState title={t('health.noComponents')} detail={t('health.noComponentsDetail')} />}
      </section>
    </div>
  );
}
