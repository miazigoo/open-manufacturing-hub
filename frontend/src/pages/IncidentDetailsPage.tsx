import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { eventsApi } from '../api/events';
import { incidentsApi } from '../api/incidents';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';

export function IncidentDetailsPage() {
  const t = useT();
  const { incidentId = '' } = useParams();
  const queryClient = useQueryClient();
  const incident = useQuery({ queryKey: ['incident', incidentId], queryFn: () => incidentsApi.get(incidentId), enabled: Boolean(incidentId) });
  const links = useQuery({ queryKey: ['incident-events', incidentId], queryFn: () => incidentsApi.events(incidentId), enabled: Boolean(incidentId) });
  const events = useQuery({ queryKey: ['events'], queryFn: eventsApi.list });
  const action = useMutation({
    mutationFn: (type: 'acknowledge' | 'resolve' | 'ignore') => incidentsApi[type](incidentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['incident', incidentId] }),
  });

  if (incident.isLoading || links.isLoading || events.isLoading) return <LoadingState label={t('incidents.loadingOne')} />;
  const error = incident.error ?? links.error ?? events.error;
  if (error) return <ErrorState error={error} />;
  if (!incident.data) return null;

  const eventById = new Map((events.data ?? []).map((event) => [event.id, event]));

  return (
    <div className="page-stack">
      <header className="hero-panel incident-hero">
        <div>
          <Link className="ghost-link" to="/incidents">← {t('nav.incidents')}</Link>
          <span className="eyebrow">{t('incidents.details')}</span>
          <h1>{incident.data.title}</h1>
          <div className="hero-meta"><StatusBadge status={incident.data.status} /><StatusBadge status={incident.data.severity} /><span>{incident.data.target_system ?? t('incidents.unknownTarget')}</span></div>
        </div>
        <div className="action-row"><button className="ghost-button" onClick={() => action.mutate('acknowledge')}>{t('incidents.acknowledge')}</button><button className="primary-button" onClick={() => action.mutate('resolve')}>{t('incidents.resolve')}</button><button className="ghost-button" onClick={() => action.mutate('ignore')}>{t('incidents.ignore')}</button></div>
      </header>
      <section className="panel">
        <div className="metadata-grid">
          <span>{t('incidents.affectedEvents')}<strong>{incident.data.affected_events_count}</strong></span>
          <span>{t('incidents.errorCode')}<strong>{incident.data.error_code ?? '—'}</strong></span>
          <span>{t('incidents.failedStep')}<strong>{incident.data.failed_step ?? '—'}</strong></span>
          <span>{t('incidents.firstSeen')}<strong>{new Date(incident.data.first_seen_at).toLocaleString()}</strong></span>
          <span>{t('incidents.lastSeen')}<strong>{new Date(incident.data.last_seen_at).toLocaleString()}</strong></span>
        </div>
        <pre className="fingerprint-block">{incident.data.fingerprint}</pre>
      </section>
      <section className="table-panel">
        <div className="panel-toolbar"><h2>{t('incidents.linkedEvents')}</h2></div>
        <table>
          <thead><tr><th>{t('events.eventType')}</th><th>{t('common.status')}</th><th>{t('common.entity')}</th><th>{t('timeline.runs')}</th><th>{t('common.actions')}</th></tr></thead>
          <tbody>{(links.data ?? []).map((link) => {
            const event = eventById.get(link.event_id);
            return <tr key={link.id}><td>{event?.event_type ?? link.event_id.slice(0, 8)}</td><td>{event ? <StatusBadge status={event.status} /> : '—'}</td><td>{event?.entity_type} #{event?.entity_id}</td><td className="mono">{link.run_id?.slice(0, 8) ?? '—'}</td><td><Link className="primary-link" to={`/events/${link.event_id}`}>{t('timeline.eyebrow')}</Link></td></tr>;
          })}</tbody>
        </table>
      </section>
    </div>
  );
}
