import { HealthSite } from '../api/health';
import { useT } from '../i18n/useI18n';
import { StatusBadge } from './StatusBadge';

export function HealthCard({ site }: { site: HealthSite }) {
  const t = useT();
  const lastEvent = site.last_event_minutes_ago == null ? t('common.unknown') : t('health.minutesAgo', { count: site.last_event_minutes_ago });
  const heartbeat = site.heartbeat_age_seconds == null ? t('common.unknown') : t('health.secondsAgo', { count: site.heartbeat_age_seconds });
  return (
    <article className="health-card">
      <div className="health-card-top"><h3>{site.name}</h3><StatusBadge status={site.status} /></div>
      <div className="health-grid">
        <span>{t('health.internet')}<StatusBadge status={site.internet} compact /></span>
        <span>{t('health.hub')}<StatusBadge status={site.hub} compact /></span>
        <span>WMS<StatusBadge status={site.wms} compact /></span>
        <span>ERP<StatusBadge status={site.erp} compact /></span>
        <span>{t('health.agent')}<StatusBadge status={site.agent_status} compact /></span>
        <span>{t('health.heartbeat')}<strong>{heartbeat}</strong></span>
        <span>{t('health.queue')}<strong>{site.queue_size}</strong></span>
      </div>
      {site.agent_name && <p className="microcopy">{t('health.agentName', { value: site.agent_name })}</p>}
      <p className="microcopy">{t('health.lastEvent', { value: lastEvent })}</p>
    </article>
  );
}
