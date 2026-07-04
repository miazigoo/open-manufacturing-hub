import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../api/health';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { HealthCard } from '../components/HealthCard';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

export function HealthPage() {
  const t = useT();
  const query = useQuery({ queryKey: ['health-dashboard'], queryFn: healthApi.dashboard });
  const history = useQuery({ queryKey: ['agent-heartbeats'], queryFn: () => healthApi.agentHeartbeats(20) });
  if (query.isLoading) return <LoadingState label={t('health.loading')} />;
  if (query.error) return <ErrorState error={query.error} />;

  const agents = query.data?.agents ?? [];

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">{t('health.eyebrow')}</span>
        <h1>{t('health.dashboardTitle')}</h1>
        <p>{t('health.subtitle')}</p>
      </header>
      <section className="card-grid">{query.data?.sites.length ? query.data.sites.map((site) => <HealthCard key={site.name} site={site} />) : <EmptyState title={t('health.noSites')} detail={t('health.noSitesDetail')} />}</section>
      <section className="health-agent-layout">
        <div className="panel">
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">{t('health.agentsEyebrow')}</span>
              <h2>{t('health.agents')}</h2>
            </div>
            <span className="microcopy">{t('connectors.configured', { count: agents.length })}</span>
          </div>
          {agents.length ? (
            <div className="agent-card-grid">
              {agents.map((agent) => (
                <article className="agent-card" key={agent.id}>
                  <div className="panel-toolbar no-margin">
                    <div>
                      <strong>{agent.agent_name}</strong>
                      <span>{agent.site_name} · {agent.site_code}</span>
                    </div>
                    <StatusBadge status={agent.status} />
                  </div>
                  <div className="health-grid compact-health-grid">
                    <span>{t('health.internet')}<StatusBadge status={agent.internet} compact /></span>
                    <span>{t('health.hub')}<StatusBadge status={agent.hub} compact /></span>
                    <span>WMS<StatusBadge status={agent.wms} compact /></span>
                    <span>ERP<StatusBadge status={agent.erp} compact /></span>
                  </div>
                  <div className="metadata-grid compact-grid no-margin">
                    <span>{t('health.age')}<strong>{t('health.secondsAgo', { count: agent.heartbeat_age_seconds })}</strong></span>
                    <span>{t('health.staleAfter')}<strong>{agent.stale_after_seconds}s</strong></span>
                    <span>IP<strong>{agent.local_ip ?? t('common.unknown')}</strong></span>
                  </div>
                </article>
              ))}
            </div>
          ) : <EmptyState title={t('health.noAgents')} detail={t('health.noAgentsDetail')} />}
        </div>
        <div className="panel agent-contract-panel">
          <span className="eyebrow">{t('health.contractEyebrow')}</span>
          <h2>{t('health.contractTitle')}</h2>
          <p>{t('health.contractDetail')}</p>
          <pre className="json-block">{`curl -X POST "$OMH_URL/api/health/agent-heartbeat" \\
  -H "Content-Type: application/json" \\
  -d '{
    "site_name": "Main Warehouse",
    "site_code": "main",
    "agent_name": "warehouse-edge-01",
    "internet_ok": true,
    "can_reach_hub": true,
    "can_reach_wms": true,
    "can_reach_erp": true,
    "local_ip": "10.10.0.15",
    "details_json": { "version": "0.1.0" }
  }'`}</pre>
        </div>
      </section>
      <section className="panel">
        <div className="panel-toolbar"><h2>{t('health.components')}</h2></div>
        {query.data?.components.length ? <div className="component-list">{query.data.components.map((component) => <div key={`${component.type}-${component.name}`}><strong>{component.name}</strong><span>{component.type}</span><StatusBadge status={component.status} /></div>)}</div> : <EmptyState title={t('health.noComponents')} detail={t('health.noComponentsDetail')} />}
      </section>
      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>{t('health.heartbeatHistory')}</h2></div>
        {history.error ? <ErrorState error={history.error} /> : history.isLoading ? <LoadingState label={t('health.loadingHistory')} /> : history.data?.length ? (
          <table>
            <thead><tr><th>{t('health.site')}</th><th>{t('health.agent')}</th><th>{t('health.signals')}</th><th>IP</th><th>{t('common.created')}</th></tr></thead>
            <tbody>
              {history.data.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.site_name}</strong><small>{item.site_code}</small></td>
                  <td>{item.agent_name}</td>
                  <td>
                    <div className="badge-row">
                      <StatusBadge status={signal(item.internet_ok)} label={t('health.internet')} compact />
                      <StatusBadge status={signal(item.can_reach_hub)} label={t('health.hub')} compact />
                      <StatusBadge status={signal(item.can_reach_wms)} label="WMS" compact />
                      <StatusBadge status={signal(item.can_reach_erp)} label="ERP" compact />
                    </div>
                  </td>
                  <td>{item.local_ip ?? t('common.unknown')}</td>
                  <td>{formatDateTime(item.received_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState title={t('health.noHistory')} detail={t('health.noHistoryDetail')} />}
      </section>
    </div>
  );
}

function signal(value: boolean | null) {
  if (value === true) return 'ok';
  if (value === false) return 'down';
  return 'unknown';
}
