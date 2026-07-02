import { Link } from 'react-router-dom';
import { Incident } from '../api/incidents';
import { StatusBadge } from './StatusBadge';

export function IncidentCard({ incident, onAction }: { incident: Incident; onAction?: (action: 'acknowledge' | 'resolve' | 'ignore') => void }) {
  return (
    <article className="incident-card">
      <div className="incident-stripe" />
      <div className="incident-main">
        <div className="incident-title-row">
          <Link to={`/incidents/${incident.id}`}><h3>{incident.title}</h3></Link>
          <div className="badge-row"><StatusBadge status={incident.status} /><StatusBadge status={incident.severity} /></div>
        </div>
        <p>{incident.target_system ?? 'Unknown target'} · {incident.failed_step ?? 'unknown step'} · {incident.error_code ?? 'UNKNOWN'}</p>
        <div className="metadata-grid compact-grid">
          <span>Affected<strong>{incident.affected_events_count}</strong></span>
          <span>First seen<strong>{new Date(incident.first_seen_at).toLocaleString()}</strong></span>
          <span>Last seen<strong>{new Date(incident.last_seen_at).toLocaleString()}</strong></span>
        </div>
        {onAction && <div className="action-row"><button className="ghost-button" onClick={() => onAction('acknowledge')}>Acknowledge</button><button className="ghost-button" onClick={() => onAction('resolve')}>Resolve</button><button className="ghost-button" onClick={() => onAction('ignore')}>Ignore</button></div>}
      </div>
    </article>
  );
}
