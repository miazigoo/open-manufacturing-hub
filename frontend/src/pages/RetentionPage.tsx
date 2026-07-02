import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { retentionApi } from '../api/retention';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { useT } from '../i18n/I18nProvider';

export function RetentionPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['retention-preview'], queryFn: retentionApi.preview });
  const cleanup = useMutation({ mutationFn: retentionApi.cleanup, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['retention-preview'] }) });

  if (query.isLoading) return <LoadingState label={t('retention.loading')} />;
  if (query.error) return <ErrorState error={query.error} />;

  const preview = cleanup.data ?? query.data;
  return (
    <div className="page-stack">
      <header className="hero-panel retention-hero"><div><span className="eyebrow">{t('retention.eyebrow')}</span><h1>{t('retention.title')}</h1><p>{t('retention.subtitle')}</p></div></header>
      <section className="metric-grid">
        <div className="metric-card"><span>{t('retention.expiredArtifacts')}</span><strong>{preview?.expired_artifacts ?? 0}</strong></div>
        <div className="metric-card warn"><span>{t('retention.expiredEvents')}</span><strong>{preview?.expired_events ?? 0}</strong></div>
        <div className="metric-card info"><span>{t('retention.pinnedSkipped')}</span><strong>{preview?.pinned_skipped ?? 0}</strong></div>
      </section>
      <section className="panel retention-panel"><h2>{t('retention.cleanupAction')}</h2><p>{t('retention.cleanupDetail')}</p><button className="primary-button" onClick={() => cleanup.mutate()} disabled={cleanup.isPending}>{t('retention.runCleanup')}</button>{cleanup.isSuccess && <div className="success-note">{t('retention.completed')}</div>}</section>
    </div>
  );
}
