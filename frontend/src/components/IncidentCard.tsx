import { Link } from 'react-router-dom';
import { Incident } from '../api/incidents';
import { useT } from '../i18n/useI18n';
import { StatusBadge } from './StatusBadge';

export function IncidentCard({ incident, onAction }: { incident: Incident; onAction?: (action: 'acknowledge' | 'resolve' | 'ignore') => void }) {
  const t = useT();
  return (
    <article className="incident-card">
      <div className="incident-stripe" />
      <div className="incident-main">
        <div className="incident-title-row">
          <Link to={`/incidents/${incident.id}`}><h3>{incident.title}</h3></Link>
          <div className="badge-row"><StatusBadge status={incident.status} /><StatusBadge status={incident.severity} /></div>
        </div>
        <p>{incident.target_system ?? t('incidents.unknownTarget')} · {incident.failed_step ?? t('incidents.unknownStep')} · {incident.error_code ?? 'UNKNOWN'}</p>
        <div className="metadata-grid compact-grid">
          <span>{t('incidents.affected')}<strong>{incident.affected_events_count}</strong></span>
          <span>{t('incidents.firstSeen')}<strong>{new Date(incident.first_seen_at).toLocaleString()}</strong></span>
          <span>{t('incidents.lastSeen')}<strong>{new Date(incident.last_seen_at).toLocaleString()}</strong></span>
        </div>
        {onAction && <div className="action-row"><button className="ghost-button" onClick={() => onAction('acknowledge')}>{t('incidents.acknowledge')}</button><button className="ghost-button" onClick={() => onAction('resolve')}>{t('incidents.resolve')}</button><button className="ghost-button" onClick={() => onAction('ignore')}>{t('incidents.ignore')}</button></div>}
      </div>
    </article>
  );
}
