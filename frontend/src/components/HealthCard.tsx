import { HealthSite } from '../api/health';
import { useT } from '../i18n/I18nProvider';
import { StatusBadge } from './StatusBadge';

export function HealthCard({ site }: { site: HealthSite }) {
  const t = useT();
  const lastEvent = site.last_event_minutes_ago == null ? t('common.unknown') : t('health.minutesAgo', { count: site.last_event_minutes_ago });
  return (
    <article className="health-card">
      <div className="health-card-top"><h3>{site.name}</h3><StatusBadge status={site.status} /></div>
      <div className="health-grid">
        <span>{t('health.internet')}<StatusBadge status={site.internet} compact /></span>
        <span>WMS<StatusBadge status={site.wms} compact /></span>
        <span>ERP<StatusBadge status={site.erp} compact /></span>
        <span>{t('health.queue')}<strong>{site.queue_size}</strong></span>
      </div>
      <p className="microcopy">{t('health.lastEvent', { value: lastEvent })}</p>
    </article>
  );
}
