import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { incidentsApi } from '../api/incidents';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { IncidentCard } from '../components/IncidentCard';
import { LoadingState } from '../components/LoadingState';
import { useT } from '../i18n/I18nProvider';

export function IncidentsPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['incidents'], queryFn: incidentsApi.list });
  const action = useMutation({
    mutationFn: ({ id, type }: { id: string; type: 'acknowledge' | 'resolve' | 'ignore' }) => incidentsApi[type](id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['incidents'] }),
  });

  if (query.isLoading) return <LoadingState label={t('incidents.loading')} />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack">
      <header className="page-header"><span className="eyebrow">{t('incidents.eyebrow')}</span><h1>{t('incidents.title')}</h1></header>
      {query.data?.length ? (
        <div className="incident-list">
          {query.data.map((incident) => <IncidentCard key={incident.id} incident={incident} onAction={(type) => action.mutate({ id: incident.id, type })} />)}
        </div>
      ) : <EmptyState title={t('incidents.noIncidents')} detail={t('incidents.noIncidentsDetail')} />}
    </div>
  );
}
