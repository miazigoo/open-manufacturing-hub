import { useQuery } from '@tanstack/react-query';
import { auditApi } from '../../api/audit';
import { ErrorState } from '../ErrorState';
import { LoadingState } from '../LoadingState';
import { StatusBadge } from '../StatusBadge';
import { useT } from '../../i18n/useI18n';

export function ObjectHistoryPanel({ objectType, objectId }: { objectType: string | null; objectId: string | null }) {
  const t = useT();
  const enabled = Boolean(objectType && objectId);
  const history = useQuery({ queryKey: ['audit-object-history', objectType, objectId], queryFn: () => auditApi.objectHistory(objectType!, objectId!), enabled });
  if (!enabled) return null;
  if (history.isLoading) return <LoadingState label={t('audit.loadingObjectHistory')} />;
  if (history.error) return <ErrorState error={history.error} />;
  return (
    <section className="panel">
      <div className="panel-toolbar"><h2>{t('audit.objectHistory')}</h2><span>{history.data?.total ?? 0}</span></div>
      <div className="compact-run-list">
        {history.data?.items.map((item) => <div className="success-note" key={item.id}><strong>{item.action}</strong><span>{new Date(item.timestamp).toLocaleString()} · {item.actor_username ?? item.actor_type}</span><StatusBadge status={item.severity} label={item.severity} /></div>)}
      </div>
    </section>
  );
}
