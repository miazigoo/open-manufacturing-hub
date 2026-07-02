import { HealthSite } from '../api/health';
import { StatusBadge } from './StatusBadge';

export function HealthCard({ site }: { site: HealthSite }) {
  return (
    <article className="health-card">
      <div className="health-card-top"><h3>{site.name}</h3><StatusBadge status={site.status} /></div>
      <div className="health-grid">
        <span>Internet<StatusBadge status={site.internet} compact /></span>
        <span>WMS<StatusBadge status={site.wms} compact /></span>
        <span>ERP<StatusBadge status={site.erp} compact /></span>
        <span>Queue<strong>{site.queue_size}</strong></span>
      </div>
      <p className="microcopy">Last event: {site.last_event_minutes_ago == null ? 'unknown' : `${site.last_event_minutes_ago} minutes ago`}</p>
    </article>
  );
}
